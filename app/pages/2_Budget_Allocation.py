"""
Budget Allocation Page
Shows Western Province LKR 5M budget allocation and ROI metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
import sys

# Always resolve paths from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)
sys.path.append(str(PROJECT_ROOT / 'app'))
from styles import apply_modern_theme


@st.cache_data
def load_data():
    """Load budget allocation data and merge with features."""
    try:
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
    except FileNotFoundError as e:
        st.error("Data file not found: outputs/predictions/quadnova_budget_allocations.csv")
        return None

    try:
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
        allocations = allocations.merge(predictions, on='Outlet_ID', how='left')
    except FileNotFoundError:
        pass

    try:
        features = pd.read_csv('data/gold/model_features.csv')
        if 'Distributor_ID' in features.columns:
            allocations = allocations.merge(features[['Outlet_ID', 'Distributor_ID']], on='Outlet_ID', how='left')
    except FileNotFoundError:
        pass

    return allocations


st.set_page_config(page_title="Budget Allocation", page_icon="💰", layout="wide")
apply_modern_theme()

st.title("💰 Budget Allocation Strategy")
st.write("Western Province LKR 5M Budget Allocation Analysis")

allocations = load_data()

if allocations is None:
    st.stop()

# Summary metrics
st.subheader("Allocation Summary")
col1, col2, col3, col4 = st.columns(4)

total_budget = allocations['Trade_Spend_Allocation_LKR'].sum() if 'Trade_Spend_Allocation_LKR' in allocations.columns else 0
total_outlets = len(allocations)
avg_allocation = total_budget / total_outlets if total_outlets > 0 else 0
expected_incremental = allocations['Expected_Incremental_Liters'].sum() if 'Expected_Incremental_Liters' in allocations.columns else 0

with col1:
    st.metric("Total Budget Allocated", f"LKR {total_budget:,.0f}")
with col2:
    st.metric("Number of Outlets", total_outlets)
with col3:
    st.metric("Avg Allocation/Outlet", f"LKR {avg_allocation:,.0f}")
with col4:
    st.metric("Expected Incremental Liters", f"{expected_incremental:,.0f}L" if expected_incremental > 0 else "N/A")

# Budget by distributor
st.subheader("Budget Allocation by Distributor")
if 'Distributor_ID' in allocations.columns and 'Trade_Spend_Allocation_LKR' in allocations.columns:
    distributor_budget = allocations.groupby('Distributor_ID').agg({
        'Trade_Spend_Allocation_LKR': 'sum',
        'Outlet_ID': 'count'
    }).rename(columns={'Outlet_ID': 'Outlet_Count'}).sort_values('Trade_Spend_Allocation_LKR', ascending=False)

    fig = px.bar(
        distributor_budget.reset_index(),
        x='Distributor_ID',
        y='Trade_Spend_Allocation_LKR',
        hover_data=['Outlet_Count'],
        title='Budget by Distributor',
        labels={'Trade_Spend_Allocation_LKR': 'Budget (LKR)', 'Distributor_ID': 'Distributor'}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(distributor_budget, use_container_width=True)
else:
    st.info("Distributor information not available.")

# Top 20 funded outlets
st.subheader("Top 20 Outlet Allocations")
if 'Trade_Spend_Allocation_LKR' in allocations.columns:
    top_outlets = allocations.nlargest(20, 'Trade_Spend_Allocation_LKR')

    hover_data = []
    if 'Expected_Incremental_Liters' in top_outlets.columns:
        hover_data.append('Expected_Incremental_Liters')
    if 'Distributor_ID' in top_outlets.columns:
        hover_data.append('Distributor_ID')

    fig = px.bar(
        top_outlets,
        x='Outlet_ID',
        y='Trade_Spend_Allocation_LKR',
        title='Top 20 Outlets by Budget Allocation',
        labels={'Trade_Spend_Allocation_LKR': 'Budget (LKR)'},
        hover_data=hover_data if hover_data else None
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

    display_cols = ['Outlet_ID', 'Trade_Spend_Allocation_LKR']
    if 'Expected_Incremental_Liters' in top_outlets.columns:
        display_cols.append('Expected_Incremental_Liters')
    st.dataframe(top_outlets[display_cols], use_container_width=True)

# ROI Analysis
st.subheader("ROI vs Budget Allocation")
if 'Risk_Adjusted_ROI' in allocations.columns and 'Trade_Spend_Allocation_LKR' in allocations.columns:
    fig = px.scatter(
        allocations,
        x='Trade_Spend_Allocation_LKR',
        y='Risk_Adjusted_ROI',
        size='Expected_Incremental_Liters' if 'Expected_Incremental_Liters' in allocations.columns else None,
        hover_data=['Outlet_ID'],
        title='Risk-Adjusted ROI vs Budget Allocation',
        labels={'Trade_Spend_Allocation_LKR': 'Budget (LKR)', 'Risk_Adjusted_ROI': 'ROI (%)'}
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("ROI data not fully available for scatter plot.")

# Download allocation strategy
st.subheader("Export Allocation Plan")
st.download_button(
    label="Download Allocation Plan (CSV)",
    data=allocations.to_csv(index=False),
    file_name="budget_allocation_plan.csv",
    mime="text/csv"
)
