"""
Budget Allocation Page
Shows Western Province LKR 5M budget allocation and ROI metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def load_data():
    """Load budget allocation data."""
    try:
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
        return allocations, predictions
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        return None, None


st.set_page_config(page_title="Budget Allocation", page_icon="💰", layout="wide")

st.title("💰 Budget Allocation Strategy")
st.write("Western Province LKR 5M Budget Allocation Analysis")

allocations, predictions = load_data()

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
    st.metric("Total Budget Allocated", f"₹{total_budget:,.0f}")
with col2:
    st.metric("Number of Outlets", total_outlets)
with col3:
    st.metric("Avg Allocation/Outlet", f"₹{avg_allocation:,.0f}")
with col4:
    st.metric("Expected Incremental Liters", f"{expected_incremental:,.0f}L")

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
        labels={'Trade_Spend_Allocation_LKR': 'Budget (₹)', 'Distributor_ID': 'Distributor'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(distributor_budget, use_container_width=True)

# Top 20 funded outlets
st.subheader("Top 20 Outlet Allocations")
if 'Trade_Spend_Allocation_LKR' in allocations.columns:
    top_outlets = allocations.nlargest(20, 'Trade_Spend_Allocation_LKR')
    
    fig = px.bar(
        top_outlets,
        x='Outlet_ID',
        y='Trade_Spend_Allocation_LKR',
        title='Top 20 Outlets by Budget Allocation',
        labels={'Trade_Spend_Allocation_LKR': 'Budget (₹)'},
        hover_data=['Expected_Incremental_Liters'] if 'Expected_Incremental_Liters' in top_outlets.columns else None
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(top_outlets[['Outlet_ID', 'Trade_Spend_Allocation_LKR', 
                              'Expected_Incremental_Liters']] if 'Expected_Incremental_Liters' in top_outlets.columns 
                             else top_outlets[['Outlet_ID', 'Trade_Spend_Allocation_LKR']], use_container_width=True)

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
        labels={'Trade_Spend_Allocation_LKR': 'Budget (₹)', 'Risk_Adjusted_ROI': 'ROI (%)'}
    )
    st.plotly_chart(fig, use_container_width=True)

# Download allocation strategy
st.subheader("Export Allocation Plan")
st.download_button(
    label="Download Allocation Plan (CSV)",
    data=allocations.to_csv(index=False),
    file_name="budget_allocation_plan.csv",
    mime="text/csv"
)
