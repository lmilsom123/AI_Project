import streamlit as st
import json
from pathlib import Path
from main import run_pipeline, LOG_FILE

st.title("🍽️ What Should I Eat?")

# ✅ UPDATED: multi-select dietary
dietary_options = [
    "vegetarian", "vegan", "gluten-free",
    "high-protein", "low-carb", "low-fat",
    "keto", "bulking", "cutting",
    "dairy-free", "pescatarian"
]

dietary = st.multiselect("Dietary preferences", dietary_options)

# ✅ NEW: allergies input
allergy_options = ["dairy", "gluten", "nuts", "soy", "shellfish", "egg"]
allergies = st.multiselect("Allergies", allergy_options)

mood = st.text_input("What are you in the mood for?")
ingredients = st.text_input("Ingredients you have (comma separated)")

if st.button("Suggest a Meal"):
    user_input = {
        # ✅ IMPORTANT: convert list → comma string (matches your backend)
        "dietary": ", ".join(dietary),
        "allergies": ", ".join(allergies),
        "mood": mood,
        "ingredients": [i.strip() for i in ingredients.split(",")] if ingredients else []
    }

    with st.spinner("Thinking..."):
        result = run_pipeline(user_input)

    if result["success"]:
        st.success(result["output"])
    else:
        st.error(result["output"])

    st.caption(f"Took {result['attempts']} attempt(s)")

    # Dashboard section
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)

        total = len(logs)
        successes = sum(1 for l in logs if l["success"])

        st.divider()
        st.subheader("📊 Dashboard")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Queries", total)
        col2.metric("Success Rate", f"{successes/total*100:.1f}%")
        col3.metric("Avg Attempts", f"{sum(l['attempts'] for l in logs)/total:.2f}")