"""Deterministic meal-plan generation.

The original selected both the food *and* the portion size with
``random.choice`` / ``random.randint``, so the same user got different advice on
every run and the portions bore no relation to their calorie goal.

This module instead:
  1. splits the daily calorie target across meals by a fixed distribution,
  2. picks, per meal, the eligible food whose macro profile best matches the
     user's target macro ratio (deterministic, tie-broken by name), and
  3. scales the portion so the meal hits its calorie share.

The result is fully reproducible and actually satisfies the calorie target.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.constants import (
    KCAL_PER_G_CARB,
    KCAL_PER_G_FAT,
    KCAL_PER_G_PROTEIN,
    MEAL_CALORIE_SPLIT,
)
from app.domain.enums import DietPreference, MealType
from app.domain.exceptions import NoEligibleFoodError
from app.domain.models import MacroTargets

# Portions are rounded to a sensible, human-friendly granularity (grams).
_PORTION_ROUNDING_G = 5


class Food(BaseModel):
    """A catalogue food item. Nutrients are per 100 g."""

    model_config = ConfigDict(frozen=True)

    name: str
    meal: MealType
    vegetarian: bool
    carbs_g: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    water_ml: float = Field(ge=0)

    @property
    def kcal_per_100g(self) -> float:
        return (
            self.carbs_g * KCAL_PER_G_CARB
            + self.protein_g * KCAL_PER_G_PROTEIN
            + self.fat_g * KCAL_PER_G_FAT
        )


class Meal(BaseModel):
    """A single planned meal: a food scaled to a portion size."""

    model_config = ConfigDict(frozen=True)

    meal_type: MealType
    food_name: str
    quantity_g: float
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: float


class MealPlan(BaseModel):
    """A full day's plan plus the achieved totals across all meals."""

    model_config = ConfigDict(frozen=True)

    meals: list[Meal]
    total_calories_kcal: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_water_ml: float


def _macro_calorie_fractions(
    protein_g: float, carbs_g: float, fat_g: float
) -> tuple[float, float, float]:
    """Return the (protein, carb, fat) share of total calories, summing to 1."""
    p = protein_g * KCAL_PER_G_PROTEIN
    c = carbs_g * KCAL_PER_G_CARB
    f = fat_g * KCAL_PER_G_FAT
    total = p + c + f
    if total == 0:
        return (0.0, 0.0, 0.0)
    return (p / total, c / total, f / total)


def _eligible_foods(
    foods: list[Food], meal_type: MealType, preference: DietPreference
) -> list[Food]:
    """Foods for a meal, filtered by dietary preference (veg excludes non-veg)."""
    return [
        food
        for food in foods
        if food.meal is meal_type
        and (preference is DietPreference.NON_VEGETARIAN or food.vegetarian)
    ]


def _select_food(candidates: list[Food], target: MacroTargets) -> Food:
    """Pick the food whose macro distribution best matches the target ratio.

    Deterministic: minimise the L1 distance between the food's and the target's
    macro-calorie fractions, tie-broken alphabetically by name.
    """
    target_fracs = _macro_calorie_fractions(target.protein_g, target.carbs_g, target.fat_g)

    def score(food: Food) -> tuple[float, str]:
        f = _macro_calorie_fractions(food.protein_g, food.carbs_g, food.fat_g)
        distance = sum(abs(a - b) for a, b in zip(target_fracs, f, strict=True))
        return (distance, food.name)

    return min(candidates, key=score)


def generate_meal_plan(
    targets: MacroTargets,
    calorie_target_kcal: float,
    foods: list[Food],
    preference: DietPreference,
) -> MealPlan:
    """Build a deterministic meal plan satisfying the daily calorie target.

    Raises :class:`NoEligibleFoodError` if any meal has no eligible food for the
    given dietary preference.
    """
    meals: list[Meal] = []

    for meal_type in MealType:
        candidates = _eligible_foods(foods, meal_type, preference)
        if not candidates:
            raise NoEligibleFoodError(f"No {preference.value} food available for {meal_type.value}")

        food = _select_food(candidates, targets)
        meal_calories = calorie_target_kcal * MEAL_CALORIE_SPLIT[meal_type.value]

        # Scale portion so the meal delivers its calorie share.
        scale = meal_calories / food.kcal_per_100g  # in units of 100 g
        quantity_g = round(scale * 100 / _PORTION_ROUNDING_G) * _PORTION_ROUNDING_G
        factor = quantity_g / 100.0

        meals.append(
            Meal(
                meal_type=meal_type,
                food_name=food.name,
                quantity_g=quantity_g,
                calories_kcal=round(food.kcal_per_100g * factor, 1),
                protein_g=round(food.protein_g * factor, 1),
                carbs_g=round(food.carbs_g * factor, 1),
                fat_g=round(food.fat_g * factor, 1),
                water_ml=round(food.water_ml * factor, 1),
            )
        )

    return MealPlan(
        meals=meals,
        total_calories_kcal=round(sum(m.calories_kcal for m in meals), 1),
        total_protein_g=round(sum(m.protein_g for m in meals), 1),
        total_carbs_g=round(sum(m.carbs_g for m in meals), 1),
        total_fat_g=round(sum(m.fat_g for m in meals), 1),
        total_water_ml=round(sum(m.water_ml for m in meals), 1),
    )
