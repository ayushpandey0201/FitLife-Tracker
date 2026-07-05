"""Recommendation seam — the extension point for future AI features.

Phase 6 introduces *recommendations*: actionable, personalised guidance derived
from a user's profile, their plan targets, and what they actually logged. The
important design move is the **seam**, not the rules: :class:`Recommender` is a
port (Protocol), and today's :class:`RuleBasedRecommender` is one deterministic
adapter behind it. A future AI recommender (e.g. an LLM given the same context)
implements the identical interface and drops in with no change to the service,
API, or callers.

Everything here is pure: the rule-based recommender is a deterministic function
of its :class:`RecommendationContext`, so it is trivially testable and its advice
never changes between runs. The application layer assembles the context (current
profile, recomputed plan, today's tracking, weight trend) and picks a recommender.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from app.domain.enums import Goal
from app.domain.models import NutritionPlan, UserProfile
from app.domain.tracking import DailySummary, WeightTrend

# A logged day is only judged "complete enough" to critique above these floors,
# so we don't nag a user who simply hasn't finished logging yet.
_HYDRATION_SHORTFALL = 0.8  # today's water below 80% of target → suggest more
_PROTEIN_SHORTFALL = 0.8  # today's protein below 80% of target → suggest more
_CALORIE_OVER = 1.10  # intake above 110% of target → flag overshoot
_CALORIE_UNDER = 0.60  # intake below 60% of target → flag under-eating


class RecommendationCategory(StrEnum):
    """The aspect of fitness a recommendation speaks to."""

    HYDRATION = "hydration"
    PROTEIN = "protein"
    CALORIES = "calories"
    WEIGHT = "weight"
    ACTIVITY = "activity"
    LOGGING = "logging"


class RecommendationLevel(StrEnum):
    """How a recommendation should be read: praise, neutral nudge, or warning."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"


class Recommendation(BaseModel):
    """A single piece of actionable guidance."""

    model_config = ConfigDict(frozen=True)

    category: RecommendationCategory
    level: RecommendationLevel
    message: str


class RecommendationContext(BaseModel):
    """Everything a recommender needs to reason about one user, right now.

    Assembled by the application layer so recommenders (rule-based or AI) stay
    pure functions of their input and need no repository or I/O access.
    """

    model_config = ConfigDict(frozen=True)

    profile: UserProfile
    plan: NutritionPlan
    today: DailySummary
    weight_trend: WeightTrend


@runtime_checkable
class Recommender(Protocol):
    """Port: turn a :class:`RecommendationContext` into ordered guidance.

    Implementations must be deterministic w.r.t. their input where possible and
    must not perform I/O; the application layer supplies all data via the context.
    An AI-backed implementation is expected to satisfy exactly this signature.
    """

    def recommend(self, context: RecommendationContext) -> list[Recommendation]: ...


class RuleBasedRecommender:
    """Default :class:`Recommender`: transparent, deterministic heuristics.

    Each rule inspects the context and may append one recommendation. Rules are
    evidence-aligned and intentionally conservative — they only critique a day
    that has some data, and reinforce good adherence rather than only warning.
    """

    def recommend(self, context: RecommendationContext) -> list[Recommendation]:
        recs: list[Recommendation] = []
        for rule in (
            self._logging,
            self._hydration,
            self._protein,
            self._calories,
            self._weight,
            self._activity,
        ):
            rec = rule(context)
            if rec is not None:
                recs.append(rec)
        return recs

    # -- individual rules ----------------------------------------------------
    @staticmethod
    def _logging(ctx: RecommendationContext) -> Recommendation | None:
        """Nudge a user who has logged nothing today to start tracking."""
        today = ctx.today
        if today.food_count == 0 and today.exercise_count == 0 and today.water_ml == 0:
            return Recommendation(
                category=RecommendationCategory.LOGGING,
                level=RecommendationLevel.INFO,
                message="No entries yet today — log a meal, water, or a workout to track progress.",
            )
        return None

    @staticmethod
    def _hydration(ctx: RecommendationContext) -> Recommendation | None:
        target = ctx.plan.macros.water_ml
        if target <= 0 or ctx.today.water_ml == 0:
            return None
        if ctx.today.water_ml < target * _HYDRATION_SHORTFALL:
            deficit = round(target - ctx.today.water_ml)
            return Recommendation(
                category=RecommendationCategory.HYDRATION,
                level=RecommendationLevel.WARNING,
                message=(
                    f"You're about {deficit} ml short of your hydration target — drink some water."
                ),
            )
        return None

    @staticmethod
    def _protein(ctx: RecommendationContext) -> Recommendation | None:
        # Only judge protein once some food is logged for the day.
        if ctx.today.food_count == 0:
            return None
        target = ctx.plan.macros.protein_g
        if target > 0 and ctx.today.protein_g < target * _PROTEIN_SHORTFALL:
            deficit = round(target - ctx.today.protein_g)
            return Recommendation(
                category=RecommendationCategory.PROTEIN,
                level=RecommendationLevel.WARNING,
                message=f"Protein is ~{deficit} g below target — add a protein-rich food.",
            )
        return None

    @staticmethod
    def _calories(ctx: RecommendationContext) -> Recommendation | None:
        if ctx.today.food_count == 0:
            return None
        target = ctx.plan.calorie_target_kcal
        consumed = ctx.today.calories_consumed_kcal
        if target <= 0:
            return None
        if consumed > target * _CALORIE_OVER:
            over = round(consumed - target)
            return Recommendation(
                category=RecommendationCategory.CALORIES,
                level=RecommendationLevel.WARNING,
                message=(
                    f"You're ~{over} kcal over today's target — ease off for the rest of the day."
                ),
            )
        if consumed < target * _CALORIE_UNDER:
            return Recommendation(
                category=RecommendationCategory.CALORIES,
                level=RecommendationLevel.INFO,
                message="Intake is well under target so far — remember to fuel adequately.",
            )
        return None

    @staticmethod
    def _weight(ctx: RecommendationContext) -> Recommendation | None:
        """Compare the weight trend against the user's goal direction."""
        change = ctx.weight_trend.change_kg
        if change is None or len(ctx.weight_trend.entries) < 2:
            return None
        goal = ctx.profile.goal
        moving_down = change < -0.1
        moving_up = change > 0.1

        if goal is Goal.LOSE:
            if moving_down:
                return _on_track("Weight is trending down in line with your goal — keep it up.")
            if moving_up:
                return _off_track(
                    "Your goal is to lose weight, but the trend is up — review intake and activity."
                )
        elif goal is Goal.GAIN:
            if moving_up:
                return _on_track("Weight is trending up in line with your goal — nice work.")
            if moving_down:
                return _off_track(
                    "Your goal is to gain weight, but the trend is down — you may need to eat more."
                )
        return None

    @staticmethod
    def _activity(ctx: RecommendationContext) -> Recommendation | None:
        """Encourage exercise on an active-goal day with none logged."""
        if ctx.profile.goal is Goal.MAINTAIN:
            return None
        if ctx.today.exercise_count == 0 and ctx.today.food_count > 0:
            return Recommendation(
                category=RecommendationCategory.ACTIVITY,
                level=RecommendationLevel.INFO,
                message="No exercise logged today — even a short session supports your goal.",
            )
        return None


def _on_track(message: str) -> Recommendation:
    return Recommendation(
        category=RecommendationCategory.WEIGHT,
        level=RecommendationLevel.SUCCESS,
        message=message,
    )


def _off_track(message: str) -> Recommendation:
    return Recommendation(
        category=RecommendationCategory.WEIGHT,
        level=RecommendationLevel.WARNING,
        message=message,
    )
