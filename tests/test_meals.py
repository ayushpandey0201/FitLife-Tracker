"""Unit tests for deterministic meal-plan generation and the catalogue."""

from __future__ import annotations

import pytest
from app.catalog import load_exercises, load_foods
from app.domain.enums import DietPreference, MealType, Sex
from app.domain.exceptions import NoEligibleFoodError
from app.domain.meals import Food, generate_meal_plan
from app.domain.models import MacroTargets
from app.domain.nutrition import build_nutrition_plan

from tests.test_nutrition import make_profile

TARGETS = MacroTargets(protein_g=150, carbs_g=200, fat_g=60, water_ml=2800)


def _foods() -> list[Food]:
    return list(load_foods())


def test_plan_is_deterministic() -> None:
    """Regression for B5: same inputs always produce the same plan."""
    a = generate_meal_plan(TARGETS, 2200, _foods(), DietPreference.NON_VEGETARIAN)
    b = generate_meal_plan(TARGETS, 2200, _foods(), DietPreference.NON_VEGETARIAN)
    assert a == b


def test_plan_covers_all_meals() -> None:
    plan = generate_meal_plan(TARGETS, 2200, _foods(), DietPreference.NON_VEGETARIAN)
    assert {m.meal_type for m in plan.meals} == set(MealType)


def test_plan_hits_calorie_target_closely() -> None:
    """The whole point of the rewrite: portions satisfy the calorie goal."""
    plan = generate_meal_plan(TARGETS, 2200, _foods(), DietPreference.NON_VEGETARIAN)
    # Within portion-rounding tolerance.
    assert plan.total_calories_kcal == pytest.approx(2200, rel=0.05)


def test_vegetarian_preference_excludes_non_veg_foods() -> None:
    veg_names = {
        m.food_name
        for m in generate_meal_plan(TARGETS, 2200, _foods(), DietPreference.VEGETARIAN).meals
    }
    non_veg = {f.name for f in _foods() if not f.vegetarian}
    assert veg_names.isdisjoint(non_veg)


def test_no_eligible_food_raises() -> None:
    only_non_veg = [
        Food(
            name="Steak",
            meal=MealType.BREAKFAST,
            vegetarian=False,
            carbs_g=0,
            protein_g=25,
            fat_g=15,
            water_ml=50,
        )
    ]
    with pytest.raises(NoEligibleFoodError):
        generate_meal_plan(TARGETS, 2000, only_non_veg, DietPreference.VEGETARIAN)


def test_catalogue_loads_and_validates() -> None:
    foods = load_foods()
    exercises = load_exercises()
    assert len(foods) >= 15
    assert all(e.met > 0 for e in exercises)


def test_full_pipeline_profile_to_plan() -> None:
    """End-to-end: a profile yields a plan whose macros drive the meal plan."""
    profile = make_profile(sex=Sex.FEMALE, weight_kg=65, target_weight_kg=60)
    nutrition = build_nutrition_plan(profile)
    plan = generate_meal_plan(
        nutrition.macros,
        nutrition.calorie_target_kcal,
        _foods(),
        profile.diet_preference,
    )
    assert plan.total_calories_kcal == pytest.approx(nutrition.calorie_target_kcal, rel=0.05)
