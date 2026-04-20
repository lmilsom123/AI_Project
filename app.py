import streamlit as st
import json
from pathlib import Path
from main_knn import run_pipeline, LOG_FILE

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

mood = st.text_input("What are you in the mood for?")
ingredients = st.text_input("Ingredients you have (comma separated)")

# -----------------------------
# Button Logic
# -----------------------------
if st.button("Suggest a Meal"):

    user_input = {
        "dietary": ", ".join(dietary),
        "allergies": ", ".join(allergies),
        "mood": mood,
        "ingredients": [i.strip() for i in ingredients.split(",")] if ingredients else []
    }

    try:
        with st.spinner("Thinking..."):
            output = run_pipeline(user_input)

        # ✅ Since pipeline returns STRING
        st.success("Here’s your meal 👇")
        st.markdown(f"```\n{output}\n```")

        success = True

    except Exception as e:
        st.error(f"Error: {e}")
        output = str(e)
        success = False

    # -----------------------------
    # Logging (NEW - matches your backend)
    # -----------------------------
    log_entry = {
        "success": success,
        "attempts": 1  # (you can upgrade this later)
    }

    logs = []
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)

    logs.append(log_entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    # -----------------------------
    # Dashboard
    # -----------------------------
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)

        total = len(logs)
        successes = sum(1 for l in logs if l["success"])
        avg_attempts = sum(l["attempts"] for l in logs) / total if total else 0

        st.divider()
        st.subheader("📊 Dashboard")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Queries", total)
        col2.metric("Success Rate", f"{(successes/total)*100:.1f}%")
        col3.metric("Avg Attempts", f"{avg_attempts:.2f}")