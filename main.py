# =============================================================================
# WHAT SHOULD I EAT - KNN + OLLAMA HYBRID
# =============================================================================

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

# =============================================================================
# STEP 1: FILTER DATA
# =============================================================================

def filter_foods(user_input):
    dietary = user_input.get("dietary", "").lower()
    allergies = user_input.get("allergies", "").lower()

    dietary_list = [d.strip() for d in dietary.split(",") if d]
    allergy_list = [a.strip() for a in allergies.split(",") if a]

    filtered = [
        f for f in FOODS
        if (all(tag in f["dietary_tags"] for tag in dietary_list) if dietary_list else True)
        and (not any(allergen in f.get("allergens", []) for allergen in allergy_list))
    ]

    return filtered if filtered else FOODS


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

    model = NearestNeighbors(n_neighbors=3)
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


# 🔥 UPDATED: STRICT PROMPT (prevents dashboard/extra output)
def build_prompt(user_input, meal_names, lookup):
    meal_details = "\n".join([
        f"- {m}: Calories {lookup[m]['macros']['calories']}, "
        f"Protein {lookup[m]['macros']['protein']}g, "
        f"Carbs {lookup[m]['macros']['carbs']}g, "
        f"Fat {lookup[m]['macros']['fat']}g"
        for m in meal_names
    ])

    return f"""
You are a meal recommendation assistant.

User wants: {user_input.get("mood", "")}

Here are top matches:
{meal_details}

Choose ONE meal.

Respond EXACTLY in this format and NOTHING else:

MEAL: <name>
MACROS: Calories=<cal>, Protein=<g>, Carbs=<g>, Fat=<g>
REASON: <one short sentence>

DO NOT include:
- multiple meals
- analysis
- explanations
- dashboards
- extra text
"""


# =============================================================================
# STEP 6: PIPELINE
# =============================================================================

def run_pipeline(user_input):
    foods = filter_foods(user_input)

    knn_meals, lookup = get_knn_meals(user_input, foods)

    prompt = build_prompt(user_input, knn_meals, lookup)

    output = call_ollama(prompt)

    return output


# =============================================================================
# STEP 7: CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("=== What Should I Eat? (KNN + AI) ===")

    user_input = {
        "dietary": input("Dietary: "),
        "allergies": input("Allergies: "),
        "mood": input("Mood: "),
        "ingredients": []
    }

    result = run_pipeline(user_input)

    print("\n=== RESULT ===")
    print(result)