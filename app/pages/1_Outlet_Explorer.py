"""
Outlet Explorer Page
Allows business users to browse outlets, filter by province/distributor, and search by ID.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os
import sys

# Always resolve paths from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)
sys.path.append(str(PROJECT_ROOT / 'app'))
from styles import apply_modern_theme


@st.cache_data
def load_explorer_data():
    """Load and merge prediction + feature + segment data."""
    try:
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
    except FileNotFoundError:
        return None

    try:
        features = pd.read_csv('data/gold/model_features.csv')
        feat_cols = ['Outlet_ID', 'Province', 'Distributor_ID', 'avg_monthly_liters',
                     'Latitude', 'Longitude', 'Outlet_Type', 'Outlet_Size']
        feat_cols = [c for c in feat_cols if c in features.columns]
        predictions = predictions.merge(features[feat_cols], on='Outlet_ID', how='left')
    except FileNotFoundError:
        pass

    try:
        segments = pd.read_csv('data/gold/outlet_segments.csv')
        seg_cols = ['Outlet_ID', 'outlet_segment', 'confidence_score', 'potential_gap']
        seg_cols = [c for c in seg_cols if c in segments.columns]
        predictions = predictions.merge(segments[seg_cols], on='Outlet_ID', how='left')
    except FileNotFoundError:
        pass

    try:
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
        predictions = predictions.merge(allocations, on='Outlet_ID', how='left')
    except FileNotFoundError:
        pass

    return predictions


st.set_page_config(page_title="Outlet Explorer", page_icon="🔍", layout="wide")
apply_modern_theme()

st.title("🔍 Outlet Explorer")
st.write("Browse and filter outlets by province, distributor, and search criteria")

df = load_explorer_data()

if df is None:
    st.error("Predictions file not found. Run the full pipeline first.")
    st.stop()

# Filters section
st.subheader("Filters")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if 'Province' in df.columns:
        provinces = ["All"] + sorted(df['Province'].dropna().unique().tolist())
        selected_province = st.selectbox("Province", provinces)
    else:
        selected_province = "All"

with col2:
    if 'Distributor_ID' in df.columns:
        distributors = ["All"] + sorted(df['Distributor_ID'].dropna().astype(str).unique().tolist())
        selected_distributor = st.selectbox("Distributor", distributors)
    else:
        selected_distributor = "All"

with col3:
    if 'outlet_segment' in df.columns:
        segment_list = ["All"] + sorted(df['outlet_segment'].dropna().unique().tolist())
        selected_segment = st.selectbox("Segment", segment_list)
    else:
        selected_segment = "All"

with col4:
    if 'confidence_score' in df.columns:
        confidence_range = st.slider("Confidence Score", 0.0, 1.0, (0.0, 1.0))
    else:
        confidence_range = (0.0, 1.0)

# Search
search_outlet = st.text_input("Search by Outlet ID", "")

# Apply filters
filtered = df.copy()

if selected_province != "All":
    filtered = filtered[filtered['Province'] == selected_province]
if selected_distributor != "All":
    filtered = filtered[filtered['Distributor_ID'].astype(str) == selected_distributor]
if selected_segment != "All":
    filtered = filtered[filtered['outlet_segment'] == selected_segment]
if 'confidence_score' in filtered.columns:
    filtered = filtered[
        (filtered['confidence_score'].fillna(0) >= confidence_range[0]) &
        (filtered['confidence_score'].fillna(1) <= confidence_range[1])
    ]
if search_outlet:
    filtered = filtered[filtered['Outlet_ID'].astype(str).str.contains(search_outlet, case=False)]

st.subheader(f"Results: {len(filtered):,} outlets found")

# Display metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Avg Potential (L/month)", f"{filtered['Maximum_Monthly_Liters'].mean():,.0f}")
with col2:
    if 'avg_monthly_liters' in filtered.columns:
        st.metric("Avg Current Sales (L/month)", f"{filtered['avg_monthly_liters'].mean():,.0f}")
with col3:
    if 'confidence_score' in filtered.columns:
        st.metric("Avg Confidence", f"{filtered['confidence_score'].mean():.0%}")
with col4:
    if 'potential_gap' in filtered.columns:
        st.metric("Avg Potential Gap", f"{filtered['potential_gap'].mean():,.0f}L")

# Data table
st.subheader("Outlet Details")
display_cols = ['Outlet_ID', 'Maximum_Monthly_Liters']
for c in ['Province', 'Distributor_ID', 'avg_monthly_liters', 'outlet_segment',
           'confidence_score', 'potential_gap', 'Trade_Spend_Allocation_LKR']:
    if c in filtered.columns:
        display_cols.append(c)

st.dataframe(filtered[display_cols], use_container_width=True, height=400)

# Download option
st.download_button(
    label="Download Filtered Results (CSV)",
    data=filtered[display_cols].to_csv(index=False),
    file_name="outlet_explorer_results.csv",
    mime="text/csv"
)

# Visualization
st.subheader("Potential vs Current Sales")
if 'avg_monthly_liters' in filtered.columns:
    fig = px.scatter(
        filtered.dropna(subset=['avg_monthly_liters']),
        x='avg_monthly_liters',
        y='Maximum_Monthly_Liters',
        hover_data=['Outlet_ID', 'Province'] if 'Province' in filtered.columns else ['Outlet_ID'],
        color='outlet_segment' if 'outlet_segment' in filtered.columns else None,
        title='Outlet Potential Analysis',
        labels={'avg_monthly_liters': 'Current Avg Sales (L)', 'Maximum_Monthly_Liters': 'Predicted Potential (L)'},
        opacity=0.6
    )
    st.plotly_chart(fig, use_container_width=True)
