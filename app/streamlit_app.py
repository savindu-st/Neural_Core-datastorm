"""
Main Outlet Intelligence Web App
Streamlit application for browsing predictions and outlet-level reasoning.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import logging

# Set page config
st.set_page_config(
    page_title="QuadNova Outlet Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_data
def load_data():
    """Load all required datasets."""
    try:
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
        explanations = pd.read_csv('outputs/predictions/outlet_explanations.csv')
        segments = pd.read_csv('data/gold/outlet_segments.csv')
        features = pd.read_csv('data/gold/model_features.csv') if Path('data/gold/model_features.csv').exists() else None
        
        logger.info("All datasets loaded successfully")
        return predictions, allocations, explanations, segments, features
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        st.error(f"Error loading data: {e}")
        return None, None, None, None, None


def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">🎯 QuadNova Outlet Intelligence</h1>', unsafe_allow_html=True)
        st.write("Predictive potential allocation engine for beverage distribution")
    
    # Load data
    predictions, allocations, explanations, segments, features = load_data()
    
    if predictions is None:
        st.error("Unable to load required datasets. Please ensure all CSV files are in place.")
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Executive Overview", "Outlet Explorer", "Budget Allocation", "XAI Explanation", "Data Quality Evidence"]
    )
    
    if page == "Executive Overview":
        show_executive_overview(predictions, allocations, segments)
    elif page == "Outlet Explorer":
        show_outlet_explorer(predictions, allocations, explanations, segments)
    elif page == "Budget Allocation":
        show_budget_allocation(allocations, segments)
    elif page == "XAI Explanation":
        show_xai_explanation(predictions, explanations, segments)
    elif page == "Data Quality Evidence":
        show_data_quality(predictions)


def show_executive_overview(predictions, allocations, segments):
    """Executive Overview Page."""
    st.title("Executive Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Outlets", len(predictions))
    with col2:
        avg_potential = predictions['Maximum_Monthly_Liters'].mean() if 'Maximum_Monthly_Liters' in predictions.columns else 0
        st.metric("Avg Potential (L/month)", f"{avg_potential:,.0f}")
    with col3:
        total_allocation = allocations['Trade_Spend_Allocation_LKR'].sum() if 'Trade_Spend_Allocation_LKR' in allocations.columns else 0
        st.metric("Total Budget Allocated", f"₹{total_allocation:,.0f}")
    with col4:
        avg_confidence = predictions['Confidence_Score'].mean() if 'Confidence_Score' in predictions.columns else 0
        st.metric("Avg Confidence", f"{avg_confidence:.0%}")
    
    st.subheader("Outlet Distribution by Segment")
    if 'Segment' in segments.columns:
        segment_counts = segments['Segment'].value_counts()
        fig = px.bar(segment_counts, labels={'index': 'Segment', 'value': 'Count'})
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Potential vs Current Sales")
    if all(col in predictions.columns for col in ['Maximum_Monthly_Liters', 'Current_Average_Sales']):
        fig = px.scatter(
            predictions,
            x='Current_Average_Sales',
            y='Maximum_Monthly_Liters',
            size='Confidence_Score',
            hover_data=['Outlet_ID'],
            title='Outlet Potential vs Current Performance'
        )
        st.plotly_chart(fig, use_container_width=True)


def show_outlet_explorer(predictions, allocations, explanations, segments):
    """Outlet Explorer Page."""
    st.title("Outlet Explorer")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'Province' in predictions.columns:
            selected_province = st.multiselect(
                "Province",
                predictions['Province'].unique() if 'Province' in predictions.columns else []
            )
        else:
            selected_province = None
    
    with col2:
        if 'Distributor_ID' in predictions.columns:
            selected_distributor = st.multiselect(
                "Distributor",
                predictions['Distributor_ID'].unique() if 'Distributor_ID' in predictions.columns else []
            )
        else:
            selected_distributor = None
    
    with col3:
        search_outlet = st.text_input("Search by Outlet ID")
    
    # Apply filters
    filtered = predictions.copy()
    if selected_province:
        filtered = filtered[filtered['Province'].isin(selected_province)]
    if selected_distributor:
        filtered = filtered[filtered['Distributor_ID'].isin(selected_distributor)]
    if search_outlet:
        filtered = filtered[filtered['Outlet_ID'].astype(str).str.contains(search_outlet, case=False)]
    
    st.write(f"Showing {len(filtered)} outlets")
    
    # Display table
    display_cols = ['Outlet_ID', 'Maximum_Monthly_Liters', 'Confidence_Score']
    if 'Current_Average_Sales' in filtered.columns:
        display_cols.append('Current_Average_Sales')
    
    st.dataframe(filtered[display_cols], use_container_width=True)


def show_budget_allocation(allocations, segments):
    """Budget Allocation Page."""
    st.title("Western Province Budget Allocation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_budget = allocations['Trade_Spend_Allocation_LKR'].sum() if 'Trade_Spend_Allocation_LKR' in allocations.columns else 0
        st.metric("Total Budget", f"₹{total_budget:,.0f}")
    
    with col2:
        expected_incremental = allocations['Expected_Incremental_Liters'].sum() if 'Expected_Incremental_Liters' in allocations.columns else 0
        st.metric("Expected Incremental Liters", f"{expected_incremental:,.0f}L")
    
    # Budget by distributor
    st.subheader("Budget Allocation by Distributor")
    if 'Distributor_ID' in allocations.columns and 'Trade_Spend_Allocation_LKR' in allocations.columns:
        distributor_budget = allocations.groupby('Distributor_ID')['Trade_Spend_Allocation_LKR'].sum().sort_values(ascending=False)
        fig = px.bar(distributor_budget, labels={'index': 'Distributor', 'value': 'Budget (₹)'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Top funded outlets
    st.subheader("Top 20 Funded Outlets")
    if 'Trade_Spend_Allocation_LKR' in allocations.columns:
        top_outlets = allocations.nlargest(20, 'Trade_Spend_Allocation_LKR')
        fig = px.bar(
            top_outlets,
            x='Outlet_ID',
            y='Trade_Spend_Allocation_LKR',
            title='Top 20 Outlet Allocations'
        )
        st.plotly_chart(fig, use_container_width=True)


def show_xai_explanation(predictions, explanations, segments):
    """XAI Explanation Page."""
    st.title("Outlet-Level XAI Explanation")
    
    if len(explanations) == 0:
        st.warning("No explanations available. Run outlet_reasoning.py first.")
        return
    
    # Select outlet
    outlet_id = st.selectbox("Select Outlet", explanations['Outlet_ID'])
    
    explanation_row = explanations[explanations['Outlet_ID'] == outlet_id]
    if len(explanation_row) == 0:
        st.error("Outlet not found in explanations")
        return
    
    row = explanation_row.iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Predicted Potential", f"{row['Predicted_Potential']:,.0f}L")
    with col2:
        st.metric("Confidence", f"{row['Confidence_Level']:.0%}")
    with col3:
        st.metric("Segment", row['Segment'])
    
    st.subheader("Business Explanation")
    st.write(row['Business_Explanation'])
    
    st.subheader("Key Drivers")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Positive Drivers:**")
        st.write(row['Top_Positive_Drivers'])
    with col2:
        st.write("**Negative Drivers:**")
        st.write(row['Top_Negative_Drivers'])
    
    st.subheader("Recommended Action")
    st.info(row['Recommended_Action'])


def show_data_quality(predictions):
    """Data Quality Evidence Page."""
    st.title("Data Quality & Rejected Records")
    
    # Load quality summary if available
    quality_path = Path('outputs/evidence/data_quality_summary.csv')
    if quality_path.exists():
        quality_df = pd.read_csv(quality_path)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Raw Records", quality_df.get('total_records', len(predictions)))
        with col2:
            clean = quality_df.get('clean_records', len(predictions))
            st.metric("Clean Records", clean)
        with col3:
            st.metric("Rejection Rate", f"{quality_df.get('rejection_rate', 0):.1%}")
        
        st.subheader("Rejection Reasons")
        rejected_path = Path('outputs/evidence/rejected_reason_counts.csv')
        if rejected_path.exists():
            rejected_reasons = pd.read_csv(rejected_path)
            st.dataframe(rejected_reasons)
    
    st.subheader("Outlet Segments Distribution")
    st.write(f"Total outlets in predictions: {len(predictions)}")


if __name__ == '__main__':
    main()
