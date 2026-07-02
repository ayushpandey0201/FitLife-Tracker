"""Domain enumerations.

Using explicit enums (instead of the original magic ``'m'``/``'f'`` strings and
``1``/``2`` integers) removes an entire class of bugs — e.g. the original
``calculate_calories_goal`` raised ``UnboundLocalError`` for any gender other
than the two hard-coded letters.
"""

from __future__ import annotations

from enum import StrEnum


class Sex(StrEnum):
    """Biological sex, used by the Mifflin-St Jeor BMR equation."""

    MALE = "male"
    FEMALE = "female"


class ActivityLevel(StrEnum):
    """Physical activity level, mapped to a standard TDEE multiplier.

    The original code hard-coded a single ``* 1.5`` factor for everyone;
    exposing the level makes the calorie target honest and personalised.
    """

    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"

    @property
    def multiplier(self) -> float:
        """Standard Harris-Benedict / Mifflin activity multipliers."""
        return _ACTIVITY_MULTIPLIERS[self]


_ACTIVITY_MULTIPLIERS: dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}


class DietPreference(StrEnum):
    """Dietary preference controlling which foods are eligible."""

    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non_vegetarian"


class Goal(StrEnum):
    """Weight goal, derived from current vs target weight (never user-typed)."""

    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class MealType(StrEnum):
    """Meals of the day. Replaces the original 'morning/afternoon/night'."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
