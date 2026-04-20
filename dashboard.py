import streamlit as st
import json
import pandas as pd
import numpy as np
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
LOG_FILE = "logs.json"

st.set_page_config(page_title="Meal App Dashboard", layout="wide")

st.title("📊 Meal Recommender Analytics Dashboard")

# -----------------------------
# LOAD DATA
# -----------------------------
if not Path(LOG_FILE).exists():
    st.warning("No logs found yet. Run the main app first.")
    st.stop()

with open(LOG_FILE) as f:
    logs = json.load(f)

if len(logs) == 0:
    st.warning("Logs file is empty.")
    st.stop()

df = pd.DataFrame(logs)

# -----------------------------
# CLEAN DATA
# -----------------------------
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

# Ensure all columns exist
cols = [
    "success", "attempts", "mood", "dietary",
    "allergies", "ingredients_count", "response_length"
]
for col in cols:
    if col not in df.columns:
        df[col] = None

# -----------------------------
# SIDEBAR FILTERS (🔥 important)
# -----------------------------
st.sidebar.header("🔎 Filters")

# Date filter
if "timestamp" in df.columns:
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        [min_date, max_date]
    )

    if len(date_range) == 2:
        start, end = date_range
        df = df[
            (df["timestamp"].dt.date >= start) &
            (df["timestamp"].dt.date <= end)
        ]

# Mood filter
if df["mood"].notnull().any():
    moods = df["mood"].dropna().unique()
    selected_moods = st.sidebar.multiselect("Mood", moods, default=moods)
    df = df[df["mood"].isin(selected_moods)]

# Dietary filter
if df["dietary"].notnull().any():
    diets = df["dietary"].dropna().unique()
    selected_diets = st.sidebar.multiselect("Dietary", diets, default=diets)
    df = df[df["dietary"].isin(selected_diets)]

# -----------------------------
# KPI METRICS
# -----------------------------
st.subheader("📈 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Queries", len(df))

success_rate = df["success"].mean() * 100 if df["success"].notnull().any() else 0
col2.metric("Success Rate", f"{success_rate:.1f}%")

avg_attempts = df["attempts"].mean() if df["attempts"].notnull().any() else 0
col3.metric("Avg Attempts", f"{avg_attempts:.2f}")

avg_response = df["response_length"].mean() if df["response_length"].notnull().any() else 0
col4.metric("Avg Response Length", f"{avg_response:.0f}")

st.divider()

# -----------------------------
# USAGE OVER TIME
# -----------------------------
if "timestamp" in df.columns and df["timestamp"].notnull().any():
    st.subheader("📅 Usage Over Time")

    daily_usage = df.groupby(df["timestamp"].dt.date).size()
    st.line_chart(daily_usage)

# -----------------------------
# MOOD ANALYSIS
# -----------------------------
if df["mood"].notnull().any():
    st.subheader("🧠 Mood Trends")

    col1, col2 = st.columns(2)

    mood_counts = df["mood"].value_counts()
    col1.bar_chart(mood_counts)

    # Mood vs success
    mood_success = df.groupby("mood")["success"].mean()
    col2.bar_chart(mood_success)

# -----------------------------
# DIETARY ANALYSIS
# -----------------------------
if df["dietary"].notnull().any():
    st.subheader("🥗 Dietary Insights")

    col1, col2 = st.columns(2)

    diet_counts = df["dietary"].value_counts()
    col1.bar_chart(diet_counts)

    diet_success = df.groupby("dietary")["success"].mean()
    col2.bar_chart(diet_success)

# -----------------------------
# INGREDIENT ANALYSIS
# -----------------------------
if df["ingredients_count"].notnull().any():
    st.subheader("🧾 Ingredient Behavior")

    col1, col2 = st.columns(2)

    ingredient_dist = df["ingredients_count"].value_counts().sort_index()
    col1.bar_chart(ingredient_dist)

    # Ingredients vs success
    ing_success = df.groupby("ingredients_count")["success"].mean()
    col2.line_chart(ing_success)

# -----------------------------
# SUCCESS / FAILURE BREAKDOWN
# -----------------------------
if df["success"].notnull().any():
    st.subheader("✅ Success vs Failure")

    success_counts = df["success"].value_counts()
    st.bar_chart(success_counts)

# -----------------------------
# CORRELATION INSIGHTS (🔥 advanced)
# -----------------------------
numeric_cols = ["attempts", "ingredients_count", "response_length"]

available_cols = [c for c in numeric_cols if df[c].notnull().any()]

if len(available_cols) >= 2:
    st.subheader("📉 Correlation Insights")

    corr = df[available_cols].corr()
    st.dataframe(corr)

# -----------------------------
# FUN INSIGHTS (🔥 storytelling)
# -----------------------------
st.subheader("💡 Quick Insights")

if len(df) > 0:
    most_common_mood = df["mood"].mode()[0] if df["mood"].notnull().any() else "N/A"
    avg_ing = df["ingredients_count"].mean() if df["ingredients_count"].notnull().any() else 0

    st.write(f"• Most common mood: **{most_common_mood}**")
    st.write(f"• Avg ingredients per query: **{avg_ing:.1f}**")

# -----------------------------
# RAW DATA
# -----------------------------
with st.expander("🔍 View Raw Logs"):
    st.dataframe(df)