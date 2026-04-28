import streamlit as st
import json
from pathlib import Path
from sarahmain import run_pipeline, LOG_FILE
import time

st.set_page_config(page_title="What Should I Eat?", page_icon="🍽️")

st.title("🍽️ What Should I Eat?")

# -----------------------------
# Inputs
# -----------------------------
dietary_options = [
    "vegetarian", "vegan", "gluten-free",
    "high-protein", "low-carb", "low-fat",
    "keto", "bulking", "cutting",
    "dairy-free", "pescatarian"
]

dietary = st.multiselect("Dietary preferences", dietary_options)

allergy_options = ["dairy", "gluten", "nuts", "soy", "shellfish", "egg"]
allergies = st.multiselect("Allergies", allergy_options)

meal_type = st.selectbox(
    "What meal are you looking for?",
    ["Breakfast", "Lunch", "Dinner"]
)
ingredients = st.text_input("Ingredients you have (comma separated)")

# -----------------------------
# Button Logic
# -----------------------------
if st.button("Suggest a Meal"):

    user_input = {
        "dietary": ", ".join(dietary),
        "allergies": ", ".join(allergies),
        "meal_type": meal_type.lower(),
        "ingredients": [i.strip() for i in ingredients.split(",")] if ingredients else []
    }

    try:
        with st.spinner("Thinking..."):
            result = run_pipeline(user_input)

        # ✅ Extract structured outputs
        output = result.get("output", "")
        meal = result.get("meal", "Unknown")
        retrieved_docs = result.get("retrieved_docs", [])
        similarities = result.get("similarities", [])

        st.success("Here’s your meal 👇")
        st.markdown(f"```\n{output}\n```")

        success = True

    except Exception as e:
        st.error(f"Error: {e}")
        output = str(e)

        # fallback values so logging doesn't break
        meal = "Unknown"
        retrieved_docs = []
        similarities = []

        success = False

    # -----------------------------
    # Logging
    # -----------------------------
    log_entry = {
        "timestamp": time.time(),
        "success": success,
        "attempts": 1,
        "meal_type": meal_type,
        "dietary": ", ".join(dietary),
        "allergies": ", ".join(allergies),
        "ingredients_count": len(user_input["ingredients"]),
        "response_length": len(output),

        # ✅ NOW THESE WILL WORK
        "meal": meal,
        "docs_pulled": len(retrieved_docs),
        "similarity_score": max(similarities) if similarities else 0
    }

    logs = []
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)

    logs.append(log_entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)