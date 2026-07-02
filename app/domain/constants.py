"""Named domain constants (evidence-based), replacing scattered magic numbers.

Every value here carries a comment and, where relevant, a source. The original
code inlined 7700, 1.5, ``* 100`` and BMI cut-offs with no names.
"""

from __future__ import annotations

# Energy density of body fat/tissue. ~7700 kcal per kg of body weight.
# Source: widely used clinical approximation (Wishnofsky, 1958).
KCAL_PER_KG_BODY_MASS: float = 7700.0

# Atwater factors: energy yield per gram of each macronutrient (kcal/g).
KCAL_PER_G_PROTEIN: float = 4.0
KCAL_PER_G_CARB: float = 4.0
KCAL_PER_G_FAT: float = 9.0

# --- Safety guardrails -----------------------------------------------------
# Maximum sustainable rate of weight change. ~1% of body mass per week is the
# common upper bound; we cap absolute daily energy delta accordingly.
MAX_WEEKLY_WEIGHT_CHANGE_KG: float = 1.0
# Never recommend intake below these floors, regardless of deficit maths.
MIN_CALORIES_MALE: float = 1500.0
MIN_CALORIES_FEMALE: float = 1200.0

# --- Macro policy ----------------------------------------------------------
# Protein grams per kg of *current* body weight, by goal. Higher protein while
# cutting preserves lean mass; higher while bulking supports synthesis.
PROTEIN_G_PER_KG: dict[str, float] = {
    "lose": 2.0,
    "maintain": 1.6,
    "gain": 1.8,
}
# Fraction of total daily calories that should come from fat.
FAT_CALORIE_FRACTION: float = 0.25
# Carbohydrates fill the remaining calories after protein and fat.

# Daily water target: millilitres per kg of body weight (baseline hydration).
WATER_ML_PER_KG: float = 35.0

# --- BMI classification (WHO) ---------------------------------------------
BMI_UNDERWEIGHT_MAX: float = 18.5
BMI_NORMAL_MAX: float = 25.0
BMI_OVERWEIGHT_MAX: float = 30.0

# --- Meal energy distribution ---------------------------------------------
# Fraction of daily calories allocated to each meal (must sum to 1.0).
MEAL_CALORIE_SPLIT: dict[str, float] = {
    "breakfast": 0.30,
    "lunch": 0.40,
    "dinner": 0.30,
}
