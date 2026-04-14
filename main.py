# =============================================================================
# WHAT SHOULD I EAT - Generative AI System
# Architecture: Context Assembly > LLM Call > Validation > Control > Dashboard
# =============================================================================

import json
import requests
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"
MAX_RETRIES = 3
LOG_FILE = "logs.json"

with open("foods.json") as f:
    FOODS = json.load(f)

FORBIDDEN_KEYWORDS = {
    "vegetarian": ["chicken", "beef", "pork", "fish", "meat"],
    "vegan": ["chicken", "beef", "pork", "fish", "meat", "cheese", "egg", "dairy"],
    "gluten-free": ["pasta", "bread", "wheat", "flour", "croutons"]
}

# =============================================================================
# BOX 2: CONTEXT ASSEMBLY
# =============================================================================

def assemble_context(user_input: dict) -> str:
    dietary = user_input.get("dietary", "").lower()
    allergies = user_input.get("allergies", "").lower()

    dietary_list = [d.strip() for d in dietary.split(",") if d]
    allergy_list = [a.strip() for a in allergies.split(",") if a]

    filtered = [
        f for f in FOODS
        if (all(tag in f["dietary_tags"] for tag in dietary_list) if dietary_list else True)
        and (not any(allergen in f.get("allergens", []) for allergen in allergy_list))
    ]

    if not filtered:
        filtered = FOODS

    # ✅ UPDATED: include macros in context
    food_list = "\n".join(
        f"- {item['name']} ({item['cuisine']}): "
        f"{', '.join(item['ingredients'])} | "
        f"Calories: {item['macros']['calories']}, "
        f"Protein: {item['macros']['protein']}g, "
        f"Carbs: {item['macros']['carbs']}g, "
        f"Fat: {item['macros']['fat']}g"
        for item in filtered
    )

    return f"""
You are a helpful meal suggestion assistant.

The user wants: {user_input.get('mood', 'something good')}
Dietary preferences: {dietary if dietary else 'none'}
Allergies: {allergies if allergies else 'none'}
Ingredients they have: {', '.join(user_input.get('ingredients', []))}

Available meals:
{food_list}

Suggest ONE meal from the list.

Use the macros provided above EXACTLY as written for that meal.

Use exactly this format:
MEAL: <meal name>
MACROS: Calories=<cal>, Protein=<g>, Carbs=<g>, Fat=<g>
REASON: <one sentence>
"""

# =============================================================================
# BOX 3: LLM CALL (OLLAMA)
# =============================================================================

def call_ollama(prompt: str) -> str:
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    })
    response.raise_for_status()
    return response.json()["response"]

# =============================================================================
# BOX 4: VALIDATION
# =============================================================================

def validate_output(raw_output: str, user_input: dict) -> tuple[bool, str]:
    lines = raw_output.strip().splitlines()

    has_meal = any(line.startswith("MEAL:") for line in lines)
    has_macros = any(line.startswith("MACROS:") for line in lines)
    has_reason = any(line.startswith("REASON:") for line in lines)

    if not has_meal or not has_macros or not has_reason:
        return False, "Output missing MEAL, MACROS, or REASON fields"

    dietary = user_input.get("dietary", "").lower()
    allergies = user_input.get("allergies", "").lower()

    dietary_list = [d.strip() for d in dietary.split(",") if d]
    allergy_list = [a.strip() for a in allergies.split(",") if a]

    meal_line = next((l for l in lines if l.startswith("MEAL:")), "").lower()

    # dietary validation
    for d in dietary_list:
        if d in FORBIDDEN_KEYWORDS:
            for word in FORBIDDEN_KEYWORDS[d]:
                if word in meal_line:
                    return False, f"Meal may contain '{word}', violating {d}"

    # allergy validation
    for food in FOODS:
        if food["name"].lower() in meal_line:
            for allergen in food.get("allergens", []):
                if allergen in allergy_list:
                    return False, f"Meal contains allergen '{allergen}'"

    return True, "OK"

# =============================================================================
# BOX 5: CONTROL & ORCHESTRATION
# =============================================================================

def run_pipeline(user_input: dict) -> dict:
    trace = []

    for attempt in range(1, MAX_RETRIES + 1):
        context = assemble_context(user_input)
        raw_output = call_ollama(context)
        is_valid, reason = validate_output(raw_output, user_input)

        trace.append({
            "attempt": attempt,
            "output": raw_output,
            "valid": is_valid,
            "reason": reason
        })

        if is_valid:
            return {
                "success": True,
                "output": raw_output,
                "attempts": attempt,
                "trace": trace
            }

    return {
        "success": False,
        "output": "Sorry, couldn't find a valid suggestion. Try adjusting your preferences.",
        "attempts": MAX_RETRIES,
        "trace": trace
    }

# =============================================================================
# BOX 6: DASHBOARD
# =============================================================================

def log_and_display(result: dict, user_input: dict):
    logs = []

    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)

    logs.append({
        "dietary": user_input.get("dietary"),
        "allergies": user_input.get("allergies"),
        "success": result["success"],
        "attempts": result["attempts"]
    })

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    total = len(logs)
    successes = sum(1 for l in logs if l["success"])

    print("\n--- DASHBOARD ---")
    print(f"Total queries:     {total}")
    print(f"Success rate:      {successes/total*100:.1f}%")
    print(f"Avg attempts:      {sum(l['attempts'] for l in logs)/total:.2f}")
    print(f"Validation fails:  {total - successes}")

# =============================================================================
# BOX 1: USER INTERACTION
# =============================================================================

if __name__ == "__main__":
    print("=== What Should I Eat? ===")

    dietary = input("Dietary preferences (comma separated): ").strip()
    allergies = input("Allergies (comma separated): ").strip()
    mood = input("What are you in the mood for? ").strip()
    ingredients = input("Ingredients you have (comma separated, or leave blank): ").strip()

    user_input = {
        "dietary": dietary,
        "allergies": allergies,
        "mood": mood,
        "ingredients": [i.strip() for i in ingredients.split(",")] if ingredients else []
    }

    result = run_pipeline(user_input)

    print("\n=== RESULT ===")
    print(result["output"])
    print(f"(Took {result['attempts']} attempt(s))")

    log_and_display(result, user_input)