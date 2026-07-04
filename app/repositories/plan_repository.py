"""SQLAlchemy repository for persisted nutrition plans.

Reads are user-scoped so one account cannot fetch another's history. The full
plan/meal payloads are stored and returned as JSON dicts; the service layer
reconstructs the domain :class:`NutritionPlan` / :class:`MealPlan` from them.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JsonDict, PlanRecord
from app.logging_config import get_logger

logger = get_logger(__name__)


class SqlAlchemyPlanRepository:
    """Persistence operations for generated plans."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        user_id: int,
        profile_id: int | None,
        goal: str,
        diet_preference: str,
        calorie_target_kcal: float,
        bmi: float,
        nutrition_plan: JsonDict,
        meal_plan: JsonDict,
    ) -> PlanRecord:
        record = PlanRecord(
            user_id=user_id,
            profile_id=profile_id,
            goal=goal,
            diet_preference=diet_preference,
            calorie_target_kcal=calorie_target_kcal,
            bmi=bmi,
            nutrition_plan=nutrition_plan,
            meal_plan=meal_plan,
        )
        self._session.add(record)
        self._session.flush()
        logger.info("plan_persisted id=%d user_id=%d", record.id, user_id)
        return record

    def get_for_user(self, user_id: int, plan_id: int) -> PlanRecord | None:
        stmt = select(PlanRecord).where(
            PlanRecord.id == plan_id, PlanRecord.user_id == user_id
        )
        return self._session.scalars(stmt).one_or_none()

    def list_for_user(self, user_id: int) -> list[PlanRecord]:
        stmt = (
            select(PlanRecord)
            .where(PlanRecord.user_id == user_id)
            .order_by(PlanRecord.id.desc())
        )
        return list(self._session.scalars(stmt))
