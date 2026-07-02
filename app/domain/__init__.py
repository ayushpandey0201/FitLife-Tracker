"""Pure domain layer: enums, models, and deterministic fitness calculations.

Nothing in this package may import a web framework, database driver, or perform
I/O. Everything here is deterministic and unit-testable in isolation.
"""

from app.domain.enums import ActivityLevel, DietPreference, Goal, MealType, Sex
from app.domain.exceptions import DomainError
from app.domain.meals import Food, Meal, MealPlan, generate_meal_plan
from app.domain.models import BodyMetrics, MacroTargets, NutritionPlan, UserProfile
from app.domain.nutrition import build_nutrition_plan

__all__ = [
    "ActivityLevel",
    "BodyMetrics",
    "DietPreference",
    "DomainError",
    "Food",
    "Goal",
    "MacroTargets",
    "Meal",
    "MealPlan",
    "MealType",
    "NutritionPlan",
    "Sex",
    "UserProfile",
    "build_nutrition_plan",
    "generate_meal_plan",
]
