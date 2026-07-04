"""Plan request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import Goal
from app.domain.meals import MealPlan
from app.domain.models import NutritionPlan


class PlanSummary(BaseModel):
    """Lightweight plan view for history listings (no full payloads)."""

    id: int
    created_at: datetime
    goal: Goal
    calorie_target_kcal: float
    bmi: float


class PlanOut(BaseModel):
    """A full persisted plan: summary metadata plus the complete computed plans."""

    id: int
    created_at: datetime
    goal: Goal
    calorie_target_kcal: float
    bmi: float
    nutrition_plan: NutritionPlan
    meal_plan: MealPlan
