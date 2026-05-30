"""
Outlet Explorer Page
Allows business users to browse outlets, filter by province/distributor, and search by ID.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


def load_data():
    """Load outlet data."""
    try:
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
        segments = pd.read_csv('data/gold/outlet_segments.csv')
        return predictions, allocations, segments
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        return None, None, None


st.set_page_config(page_title="Outlet Explorer", page_icon="🔍", layout="wide")

st.title("🔍 Outlet Explorer")
st.write("Browse and filter outlets by province, distributor, and search criteria")

predictions, allocations, segments = load_data()

if predictions is None:
    st.stop()

# Filters section
st.subheader("Filters")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if 'Province' in predictions.columns:
        provinces = ["All"] + sorted(predictions['Province'].unique())
        selected_province = st.selectbox("Province", provinces)
    else:
        selected_province = "All"

with col2:
    if 'Distributor_ID' in predictions.columns:
        distributors = ["All"] + sorted(predictions['Distributor_ID'].unique().astype(str))
        selected_distributor = st.selectbox("Distributor", distributors)
    else:
        selected_distributor = "All"

with col3:
    if 'Segment' in segments.columns:
        segment_list = ["All"] + sorted(segments['Segment'].unique())
        selected_segment = st.selectbox("Segment", segment_list)
    else:
        selected_segment = "All"

with col4:
    confidence_range = st.slider("Confidence Score", 0.0, 1.0, (0.0, 1.0))

# Search
search_outlet = st.text_input("Search by Outlet ID", "")

# Apply filters
filtered = predictions.copy()

if selected_province != "All":
    filtered = filtered[filtered['Province'] == selected_province]

if selected_distributor != "All":
    filtered = filtered[filtered['Distributor_ID'].astype(str) == selected_distributor]

if selected_segment != "All":
    segment_outlets = segments[segments['Segment'] == selected_segment]['Outlet_ID'].values
    filtered = filtered[filtered['Outlet_ID'].isin(segment_outlets)]

filtered = filtered[
    (filtered.get('Confidence_Score', 0) >= confidence_range[0]) &
    (filtered.get('Confidence_Score', 1) <= confidence_range[1])
]

if search_outlet:
    filtered = filtered[filtered['Outlet_ID'].astype(str).str.contains(search_outlet, case=False)]

st.subheader(f"Results: {len(filtered)} outlets found")

# Display metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    avg_potential = filtered['Maximum_Monthly_Liters'].mean() if 'Maximum_Monthly_Liters' in filtered.columns else 0
    st.metric("Avg Potential (L/month)", f"{avg_potential:,.0f}")
with col2:
    avg_current = filtered.get('Current_Average_Sales', pd.Series([0])).mean()
    st.metric("Avg Current Sales (L/month)", f"{avg_current:,.0f}")
with col3:
    avg_confidence = filtered['Confidence_Score'].mean() if 'Confidence_Score' in filtered.columns else 0
    st.metric("Avg Confidence", f"{avg_confidence:.0%}")
with col4:
    if 'Competition_Level' in filtered.columns:
        avg_competition = filtered['Competition_Level'].mean()
        st.metric("Avg Competition Level", f"{avg_competition:.1f}")

# Data table
st.subheader("Outlet Details")
display_cols = [col for col in ['Outlet_ID', 'Province', 'Distributor_ID', 'Maximum_Monthly_Liters', 
                                 'Current_Average_Sales', 'Confidence_Score', 'Competition_Level'] 
                if col in filtered.columns]
st.dataframe(filtered[display_cols], use_container_width=True, height=400)

# Download option
st.download_button(
    label="Download Filtered Results (CSV)",
    data=filtered.to_csv(index=False),
    file_name="outlet_explorer_results.csv",
    mime="text/csv"
)

# Visualization
st.subheader("Potential vs Current Sales")
if all(col in filtered.columns for col in ['Maximum_Monthly_Liters', 'Current_Average_Sales']):
    fig = px.scatter(
        filtered,
        x='Current_Average_Sales',
        y='Maximum_Monthly_Liters',
        size='Confidence_Score',
        hover_data=['Outlet_ID', 'Province'],
        color='Competition_Level' if 'Competition_Level' in filtered.columns else None,
        title='Outlet Potential Analysis'
    )
    st.plotly_chart(fig, use_container_width=True)
