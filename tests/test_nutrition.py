"""Unit tests for the nutrition engine, including regressions for the bugs
found in the original single-file program.
"""

from __future__ import annotations

import pytest
from app.domain.constants import MIN_CALORIES_FEMALE, MIN_CALORIES_MALE
from app.domain.enums import ActivityLevel, Goal, Sex
from app.domain.models import UserProfile
from app.domain.nutrition import (
    build_nutrition_plan,
    calculate_bmr,
    calculate_calorie_target,
    calculate_tdee,
)
from pydantic import ValidationError


def make_profile(**overrides: object) -> UserProfile:
    base: dict[str, object] = {
        "name": "Test",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 80,
        "target_weight_kg": 75,
        "sex": Sex.MALE,
        "activity_level": ActivityLevel.MODERATE,
        "weeks_to_target": 10,
    }
    base.update(overrides)
    return UserProfile(**base)  # type: ignore[arg-type]


def test_bmr_uses_current_weight_not_target() -> None:
    """Regression for B1: BMR must depend on current weight, not target."""
    lighter_target = make_profile(weight_kg=80, target_weight_kg=60)
    heavier_target = make_profile(weight_kg=80, target_weight_kg=90)
    # Same current weight => identical BMR regardless of target.
    assert calculate_bmr(lighter_target) == calculate_bmr(heavier_target)
    # Mifflin-St Jeor for a 80kg/175cm/30yo male: 10*80+6.25*175-5*30+5 = 1748.75
    assert calculate_bmr(lighter_target) == pytest.approx(1748.75)


def test_tdee_scales_with_activity() -> None:
    sedentary = make_profile(activity_level=ActivityLevel.SEDENTARY)
    very_active = make_profile(activity_level=ActivityLevel.VERY_ACTIVE)
    assert calculate_tdee(very_active) > calculate_tdee(sedentary)


def test_engine_is_deterministic() -> None:
    """Regression for B4/B5: no randomness — identical input, identical output."""
    p = make_profile()
    assert build_nutrition_plan(p) == build_nutrition_plan(p)


def test_calorie_target_floored_for_safety() -> None:
    """An extreme, fast cut must not drop below the sex-specific floor."""
    aggressive = make_profile(sex=Sex.FEMALE, weight_kg=60, target_weight_kg=45, weeks_to_target=4)
    assert calculate_calorie_target(aggressive) >= MIN_CALORIES_FEMALE
    male = make_profile(weight_kg=70, target_weight_kg=55, weeks_to_target=4)
    assert calculate_calorie_target(male) >= MIN_CALORIES_MALE


def test_macros_are_consistent_with_calorie_target() -> None:
    plan = build_nutrition_plan(make_profile())
    kcal_from_macros = plan.macros.protein_g * 4 + plan.macros.carbs_g * 4 + plan.macros.fat_g * 9
    # Macros should account for the calorie target within rounding noise.
    assert kcal_from_macros == pytest.approx(plan.calorie_target_kcal, abs=15)


def test_goal_derivation() -> None:
    assert make_profile(weight_kg=80, target_weight_kg=70).goal is Goal.LOSE
    assert make_profile(weight_kg=70, target_weight_kg=80).goal is Goal.GAIN
    assert make_profile(weight_kg=70, target_weight_kg=70).goal is Goal.MAINTAIN


def test_bmi_category() -> None:
    plan = build_nutrition_plan(make_profile(height_cm=180, weight_kg=95))
    assert plan.body_metrics.bmi == pytest.approx(29.3, abs=0.1)
    assert plan.body_metrics.bmi_category == "overweight"


@pytest.mark.parametrize(
    "bad",
    [
        {"weeks_to_target": 0},  # regression for B3 (ZeroDivisionError)
        {"age": 0},
        {"age": -5},
        {"height_cm": 0},
        {"weight_kg": -1},
    ],
)
def test_invalid_profiles_are_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make_profile(**bad)
