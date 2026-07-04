"""Plan service: generate a nutrition plan and persist it as history.

Reuses the pure domain engine (:func:`app.domain.nutrition.build_nutrition_plan`,
:func:`app.domain.meals.generate_meal_plan`) and the bundled food catalogue, then
stores the full result so it becomes a durable, user-scoped historical record.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog import load_foods
from app.db.models import PlanRecord
from app.domain.enums import Goal
from app.domain.meals import MealPlan, generate_meal_plan
from app.domain.models import NutritionPlan, StoredProfile
from app.domain.nutrition import build_nutrition_plan
from app.logging_config import get_logger
from app.repositories.plan_repository import SqlAlchemyPlanRepository
from app.schemas.plan import PlanOut, PlanSummary
from app.services.exceptions import PlanNotFoundError

logger = get_logger(__name__)


def _record_to_out(record: PlanRecord) -> PlanOut:
    """Reconstruct the full response (incl. domain plans) from a stored row."""
    return PlanOut(
        id=record.id,
        created_at=record.created_at,
        goal=Goal(record.goal),
        calorie_target_kcal=record.calorie_target_kcal,
        bmi=record.bmi,
        nutrition_plan=NutritionPlan.model_validate(record.nutrition_plan),
        meal_plan=MealPlan.model_validate(record.meal_plan),
    )


def _record_to_summary(record: PlanRecord) -> PlanSummary:
    return PlanSummary(
        id=record.id,
        created_at=record.created_at,
        goal=Goal(record.goal),
        calorie_target_kcal=record.calorie_target_kcal,
        bmi=record.bmi,
    )


class PlanService:
    """Use cases for generating and retrieving nutrition plans."""

    def __init__(self, session: Session) -> None:
        self._plans = SqlAlchemyPlanRepository(session)

    def generate(self, user_id: int, stored_profile: StoredProfile) -> PlanOut:
        """Generate a plan from the user's profile and persist it."""
        profile = stored_profile.profile
        nutrition: NutritionPlan = build_nutrition_plan(profile)
        meal_plan: MealPlan = generate_meal_plan(
            nutrition.macros,
            nutrition.calorie_target_kcal,
            list(load_foods()),
            profile.diet_preference,
        )

        record = self._plans.add(
            user_id=user_id,
            profile_id=stored_profile.id,
            goal=nutrition.goal.value,
            diet_preference=profile.diet_preference.value,
            calorie_target_kcal=nutrition.calorie_target_kcal,
            bmi=nutrition.body_metrics.bmi,
            nutrition_plan=nutrition.model_dump(mode="json"),
            meal_plan=meal_plan.model_dump(mode="json"),
        )
        logger.info("plan_generated id=%d user_id=%d", record.id, user_id)
        return _record_to_out(record)

    def get(self, user_id: int, plan_id: int) -> PlanOut:
        """Return one of the user's plans, or raise if it is not theirs/absent."""
        record = self._plans.get_for_user(user_id, plan_id)
        if record is None:
            raise PlanNotFoundError(f"plan {plan_id} not found")
        return _record_to_out(record)

    def list_history(self, user_id: int) -> list[PlanSummary]:
        """Return summaries of the user's plans, newest first."""
        return [_record_to_summary(r) for r in self._plans.list_for_user(user_id)]
