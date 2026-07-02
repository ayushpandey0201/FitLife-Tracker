"""Domain models — typed, validated value objects.

These are ``pydantic`` models so that (a) invalid data is rejected at the
boundary with clear errors, and (b) the same objects can be reused verbatim as
API request/response schemas in later phases. They are ``frozen`` where they
represent immutable computed results.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.constants import (
    BMI_NORMAL_MAX,
    BMI_OVERWEIGHT_MAX,
    BMI_UNDERWEIGHT_MAX,
)
from app.domain.enums import ActivityLevel, DietPreference, Goal, Sex


class UserProfile(BaseModel):
    """Validated user input. All physical quantities are in metric units.

    Validation here replaces the original code's complete lack of it — negative
    ages, zero ``weeks_to_target`` (which crashed with ``ZeroDivisionError``),
    and unknown genders are now impossible to construct.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=13, le=120, description="Age in years")
    height_cm: float = Field(gt=50, le=300, description="Height in centimetres")
    weight_kg: float = Field(gt=2, le=500, description="Current weight in kg")
    target_weight_kg: float = Field(gt=2, le=500, description="Goal weight in kg")
    sex: Sex
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    diet_preference: DietPreference = DietPreference.NON_VEGETARIAN
    weeks_to_target: int = Field(
        ge=1, le=520, description="Weeks allotted to reach the target weight"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def goal(self) -> Goal:
        """Weight goal derived from current vs target weight.

        A 0.5 kg dead-band avoids classifying trivial differences as a goal.
        """
        delta = self.weight_kg - self.target_weight_kg
        if delta > 0.5:
            return Goal.LOSE
        if delta < -0.5:
            return Goal.GAIN
        return Goal.MAINTAIN


class BodyMetrics(BaseModel):
    """Body composition metrics derived from a profile."""

    model_config = ConfigDict(frozen=True)

    bmi: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bmi_category(self) -> str:
        """WHO BMI classification."""
        if self.bmi < BMI_UNDERWEIGHT_MAX:
            return "underweight"
        if self.bmi < BMI_NORMAL_MAX:
            return "normal"
        if self.bmi < BMI_OVERWEIGHT_MAX:
            return "overweight"
        return "obese"


class MacroTargets(BaseModel):
    """Daily macronutrient and hydration targets, in grams / millilitres."""

    model_config = ConfigDict(frozen=True)

    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: float


class NutritionPlan(BaseModel):
    """The full deterministic result of the nutrition engine for a profile."""

    model_config = ConfigDict(frozen=True)

    body_metrics: BodyMetrics
    goal: Goal
    bmr_kcal: float = Field(description="Basal metabolic rate")
    tdee_kcal: float = Field(description="Total daily energy expenditure")
    calorie_target_kcal: float = Field(description="Recommended daily intake")
    macros: MacroTargets
