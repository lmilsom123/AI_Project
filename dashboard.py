import streamlit as st
import json
import pandas as pd
from pathlib import Path

LOG_FILE = "logs.json"

st.set_page_config(page_title="Meal App Dashboard", layout="wide")

st.title("📊 Meal Recommender Analytics Dashboard")

# -----------------------------
# LOAD DATA
# -----------------------------
if not Path(LOG_FILE).exists():
    st.warning("No logs found yet.")
    st.stop()

with open(LOG_FILE) as f:
    logs = json.load(f)

if len(logs) == 0:
    st.warning("Logs are empty.")
    st.stop()

df = pd.DataFrame(logs)

# -----------------------------
# CLEAN DATA
# -----------------------------
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

for col in [
    "success", "attempts", "mood", "dietary",
    "allergies", "ingredients_count",
    "response_length", "meal",
    "docs_pulled", "similarity_score"
]:
    if col not in df.columns:
        df[col] = None

# ✅ Fill missing meals
df["meal"] = df["meal"].fillna("Unknown")

# -----------------------------
# KPIs
# -----------------------------
st.subheader("📈 Key Metrics")

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Total Queries", len(df))
col2.metric("Success Rate", f"{df['success'].mean()*100:.1f}%")
col3.metric("Avg Attempts", f"{df['attempts'].mean():.2f}")
col4.metric("Avg Response Length", f"{df['response_length'].mean():.0f}")

col5.metric(
    "Avg Docs Pulled",
    f"{df['docs_pulled'].mean():.1f}" if df["docs_pulled"].notnull().any() else "N/A"
)

col6.metric(
    "Avg Similarity",
    f"{df['similarity_score'].mean():.2f}" if df["similarity_score"].notnull().any() else "N/A"
)

st.divider()

# -----------------------------
# 📅 Usage Over Time
# -----------------------------
if "timestamp" in df.columns:
    st.subheader("📅 Usage Over Time")
    usage = df.groupby(df["timestamp"].dt.date).size()
    st.line_chart(usage)

# -----------------------------
# 🧠 Mood Analysis
# -----------------------------
if df["mood"].notnull().any():
    st.subheader("🧠 Mood Trends")

    col1, col2 = st.columns(2)

    col1.bar_chart(df["mood"].value_counts())

    mood_success = df.groupby("mood")["success"].mean()
    col2.bar_chart(mood_success)

# -----------------------------
# 🥗 Dietary Analysis
# -----------------------------
if df["dietary"].notnull().any():
    st.subheader("🥗 Dietary Insights")

    col1, col2 = st.columns(2)

    col1.bar_chart(df["dietary"].value_counts())

    diet_success = df.groupby("dietary")["success"].mean()
    col2.bar_chart(diet_success)

# -----------------------------
# 🧾 Ingredient Analysis
# -----------------------------
if df["ingredients_count"].notnull().any():
    st.subheader("🧾 Ingredient Behavior")

    col1, col2 = st.columns(2)

    col1.bar_chart(df["ingredients_count"].value_counts().sort_index())

    ing_success = df.groupby("ingredients_count")["success"].mean()
    col2.line_chart(ing_success)

# =============================================================================
# 🔥 NEW SECTION 1: MEAL TRACKING
# =============================================================================
if df["meal"].notnull().any():
    st.subheader("🍽️ Meal Performance")

    col1, col2 = st.columns(2)

    # Most recommended meals (excluding Unknown)
    top_meals = df[df["meal"] != "Unknown"]["meal"].value_counts().head(10)
    col1.bar_chart(top_meals)

    # Meal success rate
    meal_success = df.groupby("meal")["success"].mean().sort_values(ascending=False).head(10)
    col2.bar_chart(meal_success)

    st.caption("Left: Most frequently recommended meals | Right: Best performing meals")

# =============================================================================
# 🔥 NEW SECTION 2: USER SEGMENTATION
# =============================================================================
st.subheader("👥 User Segmentation")

def segment_user(x):
    if x is None:
        return "Unknown"
    elif x <= 2:
        return "Simple User"
    elif x <= 5:
        return "Moderate User"
    else:
        return "Complex User"

df["user_segment"] = df["ingredients_count"].apply(segment_user)

col1, col2 = st.columns(2)

segment_counts = df["user_segment"].value_counts()
col1.bar_chart(segment_counts)

segment_success = df.groupby("user_segment")["success"].mean()
col2.bar_chart(segment_success)

st.caption("Segments based on how many ingredients users provide")

# =============================================================================
# 🔥 BONUS: SEGMENT x MOOD
# =============================================================================
if df["mood"].notnull().any():
    st.subheader("🧠 Segment vs Mood Behavior")

    pivot = pd.pivot_table(
        df,
        values="success",
        index="user_segment",
        columns="mood",
        aggfunc="mean"
    )

    st.dataframe(pivot)

# =============================================================================
# 🔍 RAW DATA
# =============================================================================
with st.expander("🔍 View Raw Logs"):
    st.dataframe(df)