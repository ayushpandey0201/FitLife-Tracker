"""Command-line adapter over the pure domain engine.

This is a *thin* presentation layer: it collects and validates input, calls the
domain (``build_nutrition_plan`` / ``generate_meal_plan``), and formats output.
It contains no business logic — the same domain will back the FastAPI app in a
later phase. This replaces the original module-level script that ran on import
and crashed on any unexpected input.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import ValidationError

from app.catalog import load_foods
from app.domain.enums import ActivityLevel, DietPreference, Sex
from app.domain.meals import MealPlan, generate_meal_plan
from app.domain.models import NutritionPlan, UserProfile
from app.domain.nutrition import build_nutrition_plan
from app.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input helpers — validated, re-prompting instead of crashing (fixes A5).
# ---------------------------------------------------------------------------
def _prompt[T](message: str, parse: Callable[[str], T]) -> T:
    """Prompt until ``parse`` accepts the input, re-asking on error."""
    while True:
        raw = input(message).strip()
        try:
            return parse(raw)
        except (ValueError, KeyError) as exc:
            print(f"  ! Invalid input: {exc}. Please try again.")


def _choice[T](message: str, options: dict[str, T]) -> T:
    """Prompt for one of a set of keyed options (case-insensitive)."""
    keys = "/".join(options)

    def parse(raw: str) -> T:
        key = raw.lower()
        if key not in options:
            raise ValueError(f"expected one of {keys}")
        return options[key]

    return _prompt(f"{message} ({keys}): ", parse)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _render_plan(profile: UserProfile, plan: NutritionPlan, meal_plan: MealPlan) -> str:
    lines = [
        "",
        f"===== FitLife plan for {profile.name} =====",
        f"BMI: {plan.body_metrics.bmi} ({plan.body_metrics.bmi_category})",
        f"Goal: {plan.goal.value}",
        f"BMR: {plan.bmr_kcal} kcal   TDEE: {plan.tdee_kcal} kcal",
        f"Daily calorie target: {plan.calorie_target_kcal} kcal",
        "",
        "Daily macro targets:",
        f"  Protein: {plan.macros.protein_g} g",
        f"  Carbs:   {plan.macros.carbs_g} g",
        f"  Fat:     {plan.macros.fat_g} g",
        f"  Water:   {plan.macros.water_ml} ml",
        "",
        "Suggested meals (deterministic, calorie-matched):",
    ]
    for meal in meal_plan.meals:
        lines.append(
            f"  {meal.meal_type.value.title():10s} {meal.food_name} — "
            f"{meal.quantity_g:.0f} g  (~{meal.calories_kcal:.0f} kcal)"
        )
    lines.append(
        f"  {'Total':10s} ~{meal_plan.total_calories_kcal:.0f} kcal, "
        f"{meal_plan.total_protein_g:.0f}g P / "
        f"{meal_plan.total_carbs_g:.0f}g C / {meal_plan.total_fat_g:.0f}g F"
    )
    lines.append("")
    return "\n".join(lines)


def _collect_profile() -> UserProfile:
    """Gather a validated :class:`UserProfile` from stdin."""
    while True:
        try:
            return UserProfile(
                name=_prompt("Enter your name: ", str),
                age=_prompt("Enter your age (years): ", int),
                height_cm=_prompt("Enter your height (cm): ", float),
                weight_kg=_prompt("Enter your current weight (kg): ", float),
                target_weight_kg=_prompt("Enter your target weight (kg): ", float),
                sex=_choice(
                    "Sex", {"male": Sex.MALE, "female": Sex.FEMALE, "m": Sex.MALE, "f": Sex.FEMALE}
                ),
                activity_level=_choice(
                    "Activity level",
                    {
                        "sedentary": ActivityLevel.SEDENTARY,
                        "light": ActivityLevel.LIGHT,
                        "moderate": ActivityLevel.MODERATE,
                        "active": ActivityLevel.ACTIVE,
                        "very_active": ActivityLevel.VERY_ACTIVE,
                    },
                ),
                diet_preference=_choice(
                    "Diet",
                    {
                        "veg": DietPreference.VEGETARIAN,
                        "nonveg": DietPreference.NON_VEGETARIAN,
                    },
                ),
                weeks_to_target=_prompt("Weeks to reach target: ", int),
            )
        except ValidationError as exc:
            # A cross-field rule failed; show why and restart the questionnaire.
            print(f"\n  ! Profile invalid:\n{exc}\n  Let's try again.\n")


def main() -> None:
    """CLI entrypoint.

    User-facing output uses ``print`` (it is the program's product, not
    diagnostics); operational events go to the logger so the same domain calls
    are observable when driven by the API in a later phase.
    """
    configure_logging()
    logger.info("cli_start")

    print("FitLife Tracker — deterministic diet & fitness planner\n")
    profile = _collect_profile()

    plan = build_nutrition_plan(profile)
    meal_plan = generate_meal_plan(
        plan.macros, plan.calorie_target_kcal, list(load_foods()), profile.diet_preference
    )
    logger.info(
        "plan_generated goal=%s calorie_target=%.0f bmi=%.1f",
        plan.goal.value,
        plan.calorie_target_kcal,
        plan.body_metrics.bmi,
    )

    print(_render_plan(profile, plan, meal_plan))
    print("Healthy food for a wealthy mood :)")


if __name__ == "__main__":
    main()
