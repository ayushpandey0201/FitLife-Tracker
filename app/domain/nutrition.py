"""The deterministic, evidence-based nutrition engine.

Given a :class:`~app.domain.models.UserProfile`, it computes BMR, TDEE, a safe
calorie target, and macronutrient/hydration targets. Everything is a pure
function of the input — no randomness (unlike the original, whose macro targets
were ``random.randint`` and therefore changed every run).

Pipeline:  BMR → TDEE → calorie target (bounded) → macro split.
"""

from __future__ import annotations

from app.domain.constants import (
    FAT_CALORIE_FRACTION,
    KCAL_PER_G_CARB,
    KCAL_PER_G_FAT,
    KCAL_PER_G_PROTEIN,
    KCAL_PER_KG_BODY_MASS,
    MAX_WEEKLY_WEIGHT_CHANGE_KG,
    MIN_CALORIES_FEMALE,
    MIN_CALORIES_MALE,
    PROTEIN_G_PER_KG,
    WATER_ML_PER_KG,
)
from app.domain.enums import Sex
from app.domain.models import BodyMetrics, MacroTargets, NutritionPlan, UserProfile


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Body Mass Index = weight(kg) / height(m)^2."""
    height_m = height_cm / 100.0
    return weight_kg / (height_m**2)


def calculate_bmr(profile: UserProfile) -> float:
    """Basal Metabolic Rate via the Mifflin-St Jeor equation.

    Bug fix (B1): the original computed BMR from ``target_weight``. BMR must be
    based on the person's *current* weight — it is what the body burns today.
    """
    base = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age
    sex_offset = 5 if profile.sex is Sex.MALE else -161
    return base + sex_offset


def calculate_tdee(profile: UserProfile) -> float:
    """Total Daily Energy Expenditure = BMR x activity multiplier.

    Bug fix (B1): activity is now an explicit, per-user factor instead of a
    hard-coded ``1.5`` applied to everyone.
    """
    return calculate_bmr(profile) * profile.activity_level.multiplier


def _daily_energy_delta(profile: UserProfile) -> float:
    """Signed daily calorie adjustment needed to reach the target on schedule.

    Positive => surplus (gain), negative => deficit (lose). The magnitude is
    clamped to a safe maximum rate of weight change so we never prescribe an
    unsafe deficit — a subtle correctness problem in the original, which could
    drive the goal far below BMR.
    """
    weight_change_kg = profile.target_weight_kg - profile.weight_kg
    weeks = profile.weeks_to_target

    # Cap the effective weekly rate so we never prescribe an unsafe pace.
    max_total_change = MAX_WEEKLY_WEIGHT_CHANGE_KG * weeks
    if abs(weight_change_kg) > max_total_change:
        weight_change_kg = max_total_change if weight_change_kg > 0 else -max_total_change

    total_energy_delta = weight_change_kg * KCAL_PER_KG_BODY_MASS
    return total_energy_delta / (weeks * 7)


def calculate_calorie_target(profile: UserProfile) -> float:
    """Recommended daily intake = TDEE + safe energy delta, floored for safety.

    Bug fix (B1): the original subtracted a deficit *on top of* a target-weight
    BMR, double-counting the goal. Here the delta is applied once to TDEE, and
    the result is floored at a sex-specific minimum so we never recommend a
    dangerous intake.
    """
    raw = calculate_tdee(profile) + _daily_energy_delta(profile)
    floor = MIN_CALORIES_MALE if profile.sex is Sex.MALE else MIN_CALORIES_FEMALE
    return round(max(raw, floor), 1)


def calculate_macro_targets(profile: UserProfile, calorie_target: float) -> MacroTargets:
    """Split the calorie target into protein/fat/carbohydrate grams + water.

    Bug fix (B4): targets are now derived deterministically from the calorie
    goal and body weight, not ``random.randint``. Protein is set per kg of body
    weight (goal-dependent), fat as a fixed fraction of calories, and carbs fill
    the remainder. Carbs are floored at 0 so an aggressive cut can't go negative.
    """
    protein_g = PROTEIN_G_PER_KG[profile.goal.value] * profile.weight_kg
    fat_g = (calorie_target * FAT_CALORIE_FRACTION) / KCAL_PER_G_FAT

    remaining_kcal = calorie_target - (protein_g * KCAL_PER_G_PROTEIN) - (fat_g * KCAL_PER_G_FAT)
    carbs_g = max(remaining_kcal, 0.0) / KCAL_PER_G_CARB

    water_ml = WATER_ML_PER_KG * profile.weight_kg

    return MacroTargets(
        protein_g=round(protein_g, 1),
        carbs_g=round(carbs_g, 1),
        fat_g=round(fat_g, 1),
        water_ml=round(water_ml, 0),
    )


def build_nutrition_plan(profile: UserProfile) -> NutritionPlan:
    """Compose the full nutrition plan for a profile (the engine entrypoint)."""
    bmi = calculate_bmi(profile.weight_kg, profile.height_cm)
    calorie_target = calculate_calorie_target(profile)

    return NutritionPlan(
        body_metrics=BodyMetrics(bmi=round(bmi, 1)),
        goal=profile.goal,
        bmr_kcal=round(calculate_bmr(profile), 1),
        tdee_kcal=round(calculate_tdee(profile), 1),
        calorie_target_kcal=calorie_target,
        macros=calculate_macro_targets(profile, calorie_target),
    )
