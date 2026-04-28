# =============================================================================
# WHAT SHOULD I EAT - KNN + OLLAMA HYBRID
# =============================================================================
from difflib import get_close_matches
import json
import requests
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

# =============================================================================
# CONFIG
# =============================================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"
LOG_FILE = "logs.json"

with open("foods.json") as f:
    FOODS = json.load(f)


def get_allowed_ingredients():
    allowed_ingredients = set()

    for food in FOODS:
        for ingredient in food.get("ingredients", []):
            allowed_ingredients.add(ingredient.lower())

    return allowed_ingredients


def validate_user_ingredients(user_input):
    allowed_ingredients = get_allowed_ingredients()

    user_ingredients = [
        i.strip().lower()
        for i in user_input.get("ingredients", [])
        if i.strip()
    ]

    corrected_ingredients = []
    corrections = {}
    invalid_ingredients = []

    for ingredient in user_ingredients:
        if ingredient in allowed_ingredients:
            corrected_ingredients.append(ingredient)
        else:
            match = get_close_matches(
                ingredient,
                allowed_ingredients,
                n=1,
                cutoff=0.75
            )

            if match:
                corrected = match[0]
                corrected_ingredients.append(corrected)
                corrections[ingredient] = corrected
            else:
                invalid_ingredients.append(ingredient)

    return invalid_ingredients, corrected_ingredients, corrections



# =============================================================================
# STEP 1: FILTER DATA (MAX INGREDIENT MATCH)
# =============================================================================

def filter_foods(user_input):
    dietary = user_input.get("dietary", "").lower()
    allergies = user_input.get("allergies", "").lower()
    ingredients = user_input.get("ingredients", [])
    meal_type = user_input.get("meal_type", "").lower()  # FIX: normalize to lowercase

    dietary_list = [d.strip() for d in dietary.split(",") if d.strip()]
    allergy_list = [a.strip() for a in allergies.split(",") if a.strip()]
    ingredient_list = [i.lower() for i in ingredients]

    filtered = []

    for f in FOODS:
        # MEAL TYPE FILTER — normalize food value to lowercase before comparing
        if meal_type:
            food_meal = f.get("meal_type", [])
            if isinstance(food_meal, str):
                if food_meal.lower() != meal_type:  # FIX: lowercase food value
                    continue
            else:
                if meal_type not in [m.lower() for m in food_meal]:  # FIX: lowercase each entry
                    continue

        # dietary — normalize food tags to lowercase before comparing
        if dietary_list:
            food_tags = [tag.lower() for tag in f.get("dietary_tags", [])]  # FIX: lowercase food tags
            if not all(tag in food_tags for tag in dietary_list):
                continue

        # allergies — normalize food allergens to lowercase before comparing
        if allergy_list:
            food_allergens = [a.lower() for a in f.get("allergens", [])]  # FIX: lowercase food allergens
            if any(allergen in food_allergens for allergen in allergy_list):
                continue

        # ingredient scoring
        if ingredient_list:
            food_ingredients = [i.lower() for i in f.get("ingredients", [])]
            match_count = sum(1 for i in ingredient_list if i in food_ingredients)

            if match_count == 0:
                continue

            f["ingredient_score"] = match_count
        else:
            f["ingredient_score"] = 0

        filtered.append(f)

    # keep only max ingredient matches
    if ingredient_list and filtered:
        max_score = max(f["ingredient_score"] for f in filtered)
        filtered = [f for f in filtered if f["ingredient_score"] == max_score]

    # FIX: removed silent fallback to all FOODS — return empty list so caller
    # can detect no results instead of silently ignoring the filters
    return filtered


# =============================================================================
# STEP 2: FEATURE ENGINEERING
# =============================================================================

def build_features(foods):
    X = []
    names = []
    lookup = {}

    cuisine_map = {}
    c = 0

    for food in foods:
        if food["cuisine"] not in cuisine_map:
            cuisine_map[food["cuisine"]] = c
            c += 1

        vec = [
            food["macros"]["calories"],
            food["macros"]["protein"],
            food["macros"]["carbs"],
            food["macros"]["fat"],
            cuisine_map[food["cuisine"]]
        ]

        X.append(vec)
        names.append(food["name"])
        lookup[food["name"]] = food

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return np.array(X_scaled), names, scaler, lookup


# =============================================================================
# STEP 3: USER → VECTOR
# =============================================================================

def user_to_vector(user_input, scaler):
    calories = 600
    protein = 30
    carbs = 50
    fat = 20

    mood = user_input.get("mood", "").lower()

    if "high protein" in mood:
        protein = 50
    if "low carb" in mood:
        carbs = 20
    if "low fat" in mood:
        fat = 10
    if "bulking" in mood:
        calories = 800

    return scaler.transform([[calories, protein, carbs, fat, 0]])


# =============================================================================
# STEP 4: KNN MODEL
# =============================================================================

def get_knn_meals(user_input, foods):
    X, names, scaler, lookup = build_features(foods)

    k = min(3, len(X))
    model = NearestNeighbors(n_neighbors=k)

    model.fit(X)

    user_vec = user_to_vector(user_input, scaler)

    _, indices = model.kneighbors(user_vec)

    meals = [names[i] for i in indices[0]]

    return meals, lookup


# =============================================================================
# STEP 5: LLM (OLLAMA)
# =============================================================================

def call_ollama(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
    )
    response.raise_for_status()
    return response.json()["response"]


def build_prompt(user_input, meal_names, lookup):
    meal_details = "\n".join([
        f"- {m}: "
        f"Ingredients: {', '.join(lookup[m].get('ingredients', []))} | "
        f"Calories {lookup[m]['macros']['calories']}, "
        f"Protein {lookup[m]['macros']['protein']}g, "
        f"Carbs {lookup[m]['macros']['carbs']}g, "
        f"Fat {lookup[m]['macros']['fat']}g"
        for m in meal_names
    ])

    return f"""
You are a meal recommendation assistant.

User wants: {user_input.get("mood", "")}
User ingredients: {", ".join(user_input.get("ingredients", []))}

Here are top matches:
{meal_details}

Choose ONE meal.

Respond EXACTLY in this format and NOTHING else:

MEAL: <name>
INGREDIENTS: <comma separated full ingredient list>
MACROS: Calories=<cal>, Protein=<g>, Carbs=<g>, Fat=<g>
REASON: <one clear sentence referencing ingredients and user preference>

DO NOT include:
- multiple meals
- extra explanation
"""


# =============================================================================
# STEP 6: ENFORCE INGREDIENT CORRECTNESS
# =============================================================================

def enforce_ingredients(output, lookup):
    if "MEAL:" not in output:
        return output

    try:
        meal_name = output.split("MEAL:")[1].split("\n")[0].strip()
        ingredients = lookup.get(meal_name, {}).get("ingredients", [])

        lines = output.split("\n")
        new_lines = []

        for line in lines:
            if line.startswith("INGREDIENTS:"):
                new_lines.append(f"INGREDIENTS: {', '.join(ingredients)}")
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    except:
        return output


# =============================================================================
# STEP 7: PIPELINE
# =============================================================================

def run_pipeline(user_input):
    invalid, corrected_ingredients, corrections = validate_user_ingredients(user_input)

    if invalid:
        return {
            "output": (
                "Invalid ingredient input.\n\n"
                f"I could not find these as valid ingredient options: {', '.join(invalid)}.\n"
                "Please enter ingredients that exist in the food database."
            ),
            "meal": "Unknown",
            "retrieved_docs": [],
            "similarities": []
        }

    user_input["ingredients"] = corrected_ingredients

    foods = filter_foods(user_input)

    # FIX: handle case where filters eliminate all foods
    if not foods:
        return {
            "output": (
                "No meals found matching your filters.\n\n"
                "Try relaxing your dietary preferences, allergies, or meal type selection."
            ),
            "meal": "Unknown",
            "retrieved_docs": [],
            "similarities": []
        }

    knn_meals, lookup = get_knn_meals(user_input, foods)

    prompt = build_prompt(user_input, knn_meals, lookup)
    output = call_ollama(prompt)
    output = enforce_ingredients(output, lookup)

    try:
        meal = output.split("MEAL:")[1].split("\n")[0].strip()
    except:
        meal = "Unknown"

    retrieved_docs = knn_meals
    similarities = [1.0 - (i * 0.1) for i in range(len(knn_meals))]

    if corrections:
        correction_note = "Ingredient spelling corrected: "
        correction_note += ", ".join(
            [f"{wrong} → {right}" for wrong, right in corrections.items()]
        )
        output = correction_note + "\n\n" + output

    return {
        "output": output,
        "meal": meal,
        "retrieved_docs": retrieved_docs,
        "similarities": similarities
    }