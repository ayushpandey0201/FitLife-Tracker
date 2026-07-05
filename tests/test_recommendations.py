"""Tests for the recommendation seam (Phase 6).

Covers the pure :class:`RuleBasedRecommender` rules and the
:class:`RecommendationService` wiring — including that a custom recommender
injected through the seam is used unchanged (the AI-swap path).
"""

from __future__ import annotations

from datetime import date

import pytest
from app.domain.nutrition import build_nutrition_plan
from app.domain.recommendations import (
    Recommendation,
    RecommendationCategory,
    RecommendationContext,
    RecommendationLevel,
    RuleBasedRecommender,
)
from app.domain.tracking import DailySummary, LoggedWeight, WaterEntry, build_weight_trend
from app.services.auth_service import AuthService
from app.services.exceptions import ProfileNotFoundError
from app.services.profile_service import ProfileService
from app.services.recommendation_service import RecommendationService
from app.services.tracking_service import TrackingService
from sqlalchemy.orm import Session

from tests.test_nutrition import make_profile
from tests.test_services import _settings
from tests.test_tracking import _dt

_RECOMMENDER = RuleBasedRecommender()


def _summary(
    day: date,
    *,
    consumed: float = 0.0,
    burned: float = 0.0,
    protein: float = 0.0,
    water: float = 0.0,
    food_count: int = 0,
    exercise_count: int = 0,
) -> DailySummary:
    return DailySummary(
        date=day,
        calories_consumed_kcal=consumed,
        calories_burned_kcal=burned,
        net_calories_kcal=consumed - burned,
        protein_g=protein,
        carbs_g=0.0,
        fat_g=0.0,
        water_ml=water,
        food_count=food_count,
        exercise_count=exercise_count,
    )


def _context(
    today: DailySummary, weights: list[LoggedWeight] | None = None
) -> RecommendationContext:
    profile = make_profile()  # 80 kg male, goal = lose
    return RecommendationContext(
        profile=profile,
        plan=build_nutrition_plan(profile),
        today=today,
        weight_trend=build_weight_trend(weights or []),
    )


def _categories(recs: list[Recommendation]) -> set[RecommendationCategory]:
    return {r.category for r in recs}


# --- rule-based recommender ------------------------------------------------
def test_empty_day_prompts_logging() -> None:
    recs = _RECOMMENDER.recommend(_context(_summary(_dt(4).date())))
    assert RecommendationCategory.LOGGING in _categories(recs)


def test_hydration_shortfall_warns() -> None:
    ctx = _context(_summary(_dt(4).date(), water=200, food_count=0))
    recs = _RECOMMENDER.recommend(ctx)
    hydration = [r for r in recs if r.category is RecommendationCategory.HYDRATION]
    assert hydration and hydration[0].level is RecommendationLevel.WARNING


def test_protein_shortfall_only_when_food_logged() -> None:
    day = _dt(4).date()
    # Low protein but no food logged yet -> no protein rec.
    assert RecommendationCategory.PROTEIN not in _categories(
        _RECOMMENDER.recommend(_context(_summary(day, food_count=0, protein=0)))
    )
    # Food logged with low protein -> protein warning.
    ctx = _context(_summary(day, consumed=1200, food_count=3, protein=10, water=3000))
    assert RecommendationCategory.PROTEIN in _categories(_RECOMMENDER.recommend(ctx))


def test_calories_over_target_warns() -> None:
    profile = make_profile()
    target = build_nutrition_plan(profile).calorie_target_kcal
    ctx = _context(
        _summary(_dt(4).date(), consumed=target * 1.5, food_count=4, protein=200, water=3000)
    )
    calories = [
        r for r in _RECOMMENDER.recommend(ctx) if r.category is RecommendationCategory.CALORIES
    ]
    assert calories and calories[0].level is RecommendationLevel.WARNING


def test_weight_trend_off_goal_warns() -> None:
    # Goal is to lose, but weight is trending up.
    weights = [
        LoggedWeight(id=1, logged_at=_dt(1), weight_kg=80.0),
        LoggedWeight(id=2, logged_at=_dt(5), weight_kg=82.0),
    ]
    ctx = _context(
        _summary(_dt(5).date(), consumed=1500, food_count=3, protein=200, water=3000), weights
    )
    weight_recs = [
        r for r in _RECOMMENDER.recommend(ctx) if r.category is RecommendationCategory.WEIGHT
    ]
    assert weight_recs and weight_recs[0].level is RecommendationLevel.WARNING


def test_weight_trend_on_goal_praises() -> None:
    weights = [
        LoggedWeight(id=1, logged_at=_dt(1), weight_kg=82.0),
        LoggedWeight(id=2, logged_at=_dt(5), weight_kg=80.0),
    ]
    ctx = _context(
        _summary(_dt(5).date(), consumed=1500, food_count=3, protein=200, water=3000), weights
    )
    weight_recs = [
        r for r in _RECOMMENDER.recommend(ctx) if r.category is RecommendationCategory.WEIGHT
    ]
    assert weight_recs and weight_recs[0].level is RecommendationLevel.SUCCESS


def test_is_deterministic() -> None:
    ctx = _context(_summary(_dt(4).date(), consumed=500, food_count=2, protein=20, water=1000))
    assert _RECOMMENDER.recommend(ctx) == _RECOMMENDER.recommend(ctx)


# --- service ---------------------------------------------------------------
def _user_with_profile(session: Session, email: str = "r@example.com") -> int:
    user = AuthService(session, _settings()).register(email=email, password="password123")
    ProfileService(session).create(user.id, make_profile())
    return user.id


def test_service_requires_profile(db_session: Session) -> None:
    user = AuthService(db_session, _settings()).register(
        email="np@example.com", password="password123"
    )
    with pytest.raises(ProfileNotFoundError):
        RecommendationService(db_session).for_user(user.id)


def test_service_returns_recommendations(db_session: Session) -> None:
    user_id = _user_with_profile(db_session)
    recs = RecommendationService(db_session).for_user(user_id)
    # A brand-new user with no logs today should at least be nudged to log.
    assert any(r.category is RecommendationCategory.LOGGING for r in recs)


def test_service_uses_injected_recommender(db_session: Session) -> None:
    """The seam: a custom Recommender is used verbatim (the AI-swap path)."""
    sentinel = Recommendation(
        category=RecommendationCategory.LOGGING,
        level=RecommendationLevel.INFO,
        message="from a fake recommender",
    )

    class FakeRecommender:
        def recommend(self, context: RecommendationContext) -> list[Recommendation]:
            return [sentinel]

    user_id = _user_with_profile(db_session, email="fake@example.com")
    recs = RecommendationService(db_session, recommender=FakeRecommender()).for_user(user_id)
    assert recs == [sentinel]


def test_service_reflects_logged_data(db_session: Session) -> None:
    user_id = _user_with_profile(db_session, email="logged@example.com")
    # Log a big hydration shortfall for *now* (no explicit timestamp), so it
    # lands on today's summary regardless of the calendar date.
    TrackingService(db_session).log_water(user_id, WaterEntry(volume_ml=100))
    recs = RecommendationService(db_session).for_user(user_id)
    # With some water logged (but far below target) hydration should be flagged,
    # and the "log nothing yet" nudge should be gone.
    cats = {r.category for r in recs}
    assert RecommendationCategory.HYDRATION in cats
    assert RecommendationCategory.LOGGING not in cats
