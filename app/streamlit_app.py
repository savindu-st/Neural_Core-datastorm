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
import os
from styles import apply_modern_theme

# Always resolve paths from project root (parent of app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

# Set page config
st.set_page_config(
    page_title="QuadNova Outlet Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply modern theme
apply_modern_theme()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_data
def load_data():
    """Load and merge all datasets into one enriched dataframe."""
    predictions = None
    allocations = None
    explanations = None
    segments = None
    features = None

    try:
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
    except FileNotFoundError:
        pass

    try:
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
    except FileNotFoundError:
        pass

    try:
        explanations = pd.read_csv('outputs/predictions/outlet_explanations.csv')
    except FileNotFoundError:
        pass

    try:
        segments = pd.read_csv('data/gold/outlet_segments.csv')
    except FileNotFoundError:
        pass

    try:
        features = pd.read_csv('data/gold/model_features.csv')
    except FileNotFoundError:
        pass

    # Build an enriched predictions dataframe by merging everything
    enriched = None
    if predictions is not None:
        enriched = predictions.copy()

        # Merge features (Province, Distributor_ID, avg_monthly_liters, etc.)
        if features is not None:
            feat_cols = ['Outlet_ID', 'Province', 'Distributor_ID', 'avg_monthly_liters',
                         'Latitude', 'Longitude', 'Outlet_Type', 'Outlet_Size']
            feat_cols = [c for c in feat_cols if c in features.columns]
            enriched = enriched.merge(features[feat_cols], on='Outlet_ID', how='left')

        # Merge segments (outlet_segment, confidence_score, potential_gap)
        if segments is not None:
            seg_cols = ['Outlet_ID', 'outlet_segment', 'confidence_score', 'potential_gap']
            seg_cols = [c for c in seg_cols if c in segments.columns]
            enriched = enriched.merge(segments[seg_cols], on='Outlet_ID', how='left')

        # Merge allocations
        if allocations is not None:
            enriched = enriched.merge(allocations, on='Outlet_ID', how='left')

    return enriched, explanations, segments, features


def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">🎯 QuadNova Outlet Intelligence</h1>', unsafe_allow_html=True)
        st.write("Predictive potential allocation engine for beverage distribution")

    # Load data
    enriched, explanations, segments, features = load_data()

    if enriched is None:
        st.error("❌ Core file missing: `outputs/predictions/quadnova_predictions.csv`. Run the full pipeline first.")
        return

    # Show warnings for optional missing files
    missing = []
    if 'Trade_Spend_Allocation_LKR' not in enriched.columns:
        missing.append("`quadnova_budget_allocations.csv` — run: `python src/optimization/budget_optimizer.py`")
    if explanations is None:
        missing.append("`outlet_explanations.csv` — run: `python src/xai/outlet_reasoning.py`")
    if 'outlet_segment' not in enriched.columns:
        missing.append("`outlet_segments.csv` — run: `python src/features/outlet_segmentation.py`")

    if missing:
        with st.expander("⚠️ Some optional files are missing (click to see)", expanded=False):
            for m in missing:
                st.warning(m)

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Executive Overview", "Outlet Explorer", "Budget Allocation", "XAI Explanation", "Data Quality Evidence"]
    )

    if page == "Executive Overview":
        show_executive_overview(enriched)
    elif page == "Outlet Explorer":
        show_outlet_explorer(enriched)
    elif page == "Budget Allocation":
        show_budget_allocation(enriched)
    elif page == "XAI Explanation":
        show_xai_explanation(enriched, explanations)
    elif page == "Data Quality Evidence":
        show_data_quality(enriched)


def show_executive_overview(df):
    """Executive Overview Page."""
    st.title("Executive Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Outlets", f"{len(df):,}")
    with col2:
        avg_potential = df['Maximum_Monthly_Liters'].mean()
        st.metric("Avg Potential (L/month)", f"{avg_potential:,.0f}")
    with col3:
        if 'Trade_Spend_Allocation_LKR' in df.columns:
            total_alloc = df['Trade_Spend_Allocation_LKR'].sum()
            st.metric("Total Budget Allocated", f"LKR {total_alloc:,.0f}")
        else:
            st.metric("Total Budget Allocated", "N/A")
    with col4:
        if 'confidence_score' in df.columns:
            avg_conf = df['confidence_score'].mean()
            if avg_conf > 1:
                st.metric("Avg Confidence", f"{avg_conf:.1f}%")
            else:
                st.metric("Avg Confidence", f"{avg_conf:.1%}")
        else:
            st.metric("Avg Confidence", "N/A")

    # Segment distribution
    st.subheader("Outlet Distribution by Segment")
    if 'outlet_segment' in df.columns:
        segment_counts = df['outlet_segment'].value_counts()
        fig = px.bar(
            x=segment_counts.index, y=segment_counts.values,
            labels={'x': 'Segment', 'y': 'Count'},
            title='Outlet Segment Distribution',
            color=segment_counts.index,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, theme=None)

    # Potential vs Current Sales
    st.subheader("Potential vs Current Sales")
    if 'avg_monthly_liters' in df.columns:
        fig = px.scatter(
            df.dropna(subset=['avg_monthly_liters']),
            x='avg_monthly_liters',
            y='Maximum_Monthly_Liters',
            hover_data=['Outlet_ID'],
            title='Outlet Potential vs Current Performance',
            labels={'avg_monthly_liters': 'Current Avg Sales (L)', 'Maximum_Monthly_Liters': 'Predicted Potential (L)'},
            opacity=0.5
        )
        fig.add_trace(go.Scatter(x=[0, df['avg_monthly_liters'].max()], y=[0, df['avg_monthly_liters'].max()],
                                  mode='lines', name='No Gap Line', line=dict(dash='dash', color='red')))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, theme=None)
    else:
        st.info("Current sales data not available (model_features.csv needed)")


def show_outlet_explorer(df):
    """Outlet Explorer Page."""
    st.title("🔍 Outlet Explorer")

    # Filters
    col1, col2, col3 = st.columns(3)

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
        search_outlet = st.text_input("Search by Outlet ID")

    # Apply filters
    filtered = df.copy()
    if selected_province != "All":
        filtered = filtered[filtered['Province'] == selected_province]
    if selected_distributor != "All":
        filtered = filtered[filtered['Distributor_ID'].astype(str) == selected_distributor]
    if search_outlet:
        filtered = filtered[filtered['Outlet_ID'].astype(str).str.contains(search_outlet, case=False)]

    st.write(f"Showing **{len(filtered):,}** outlets")

    # Display table
    display_cols = ['Outlet_ID', 'Maximum_Monthly_Liters']
    for c in ['Province', 'Distributor_ID', 'avg_monthly_liters', 'outlet_segment', 'confidence_score', 'potential_gap']:
        if c in filtered.columns:
            display_cols.append(c)

    st.dataframe(filtered[display_cols], use_container_width=True, height=400)


def show_budget_allocation(df):
    """Budget Allocation Page."""
    st.title("💰 Western Province Budget Allocation")

    if 'Trade_Spend_Allocation_LKR' not in df.columns:
        st.warning("Budget allocation data not available. Run `python src/optimization/budget_optimizer.py`")
        return

    # Only show allocated outlets
    allocated = df[df['Trade_Spend_Allocation_LKR'].notna() & (df['Trade_Spend_Allocation_LKR'] > 0)]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Budget", f"LKR {allocated['Trade_Spend_Allocation_LKR'].sum():,.0f}")
    with col2:
        st.metric("Outlets Funded", f"{len(allocated):,}")
    with col3:
        avg_alloc = allocated['Trade_Spend_Allocation_LKR'].mean()
        st.metric("Avg Allocation", f"LKR {avg_alloc:,.0f}")

    # Budget by distributor
    st.subheader("Budget Allocation by Distributor")
    if 'Distributor_ID' in allocated.columns:
        dist_budget = allocated.groupby('Distributor_ID')['Trade_Spend_Allocation_LKR'].sum().sort_values(ascending=False)
        fig = px.bar(x=dist_budget.index, y=dist_budget.values,
                     labels={'x': 'Distributor', 'y': 'Budget (LKR)'},
                     title='Budget by Distributor')
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, theme=None)

    # Top funded outlets
    st.subheader("Top 20 Funded Outlets")
    top_outlets = allocated.nlargest(20, 'Trade_Spend_Allocation_LKR')
    fig = px.bar(top_outlets, x='Outlet_ID', y='Trade_Spend_Allocation_LKR',
                 title='Top 20 Outlet Allocations', labels={'Trade_Spend_Allocation_LKR': 'Budget (LKR)'})
    fig.update_xaxes(tickangle=45)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, theme=None)


def show_xai_explanation(df, explanations):
    """XAI Explanation Page."""
    st.title("🔬 Outlet-Level XAI Explanation")

    if explanations is None or len(explanations) == 0:
        st.warning("No explanations available. Run: `python src/xai/outlet_reasoning.py`")
        return

    # Select outlet
    outlet_id = st.selectbox("Select Outlet", sorted(explanations['Outlet_ID'].unique()))

    row = explanations[explanations['Outlet_ID'] == outlet_id].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Predicted Potential", f"{row['Predicted_Potential']:,.0f}L")
    with col2:
        conf = row['Confidence_Level']
        st.metric("Confidence", f"{conf:.0%}" if pd.notna(conf) else "N/A")
    with col3:
        st.metric("Segment", row['Segment'])

    st.subheader("📊 Business Explanation")
    st.write(row['Business_Explanation'])

    st.subheader("🎯 Key Drivers")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Positive Drivers:**")
        pos = str(row['Top_Positive_Drivers']) if pd.notna(row['Top_Positive_Drivers']) else 'N/A'
        st.write(pos)
    with col2:
        st.markdown("**❌ Negative Drivers:**")
        neg = str(row['Top_Negative_Drivers']) if pd.notna(row['Top_Negative_Drivers']) else 'N/A'
        st.write(neg)

    st.subheader("💡 Recommended Action")
    st.info(row['Recommended_Action'])


def show_data_quality(df):
    """Data Quality Evidence Page."""
    st.title("🔍 Data Quality & Rejected Records")

    # Load quality summary if available
    quality_path = Path('outputs/evidence/data_quality_summary.csv')
    rejected_path = Path('outputs/evidence/rejected_reason_counts.csv')

    if quality_path.exists():
        quality_df = pd.read_csv(quality_path)
        st.subheader("Quality Summary")
        st.dataframe(quality_df, use_container_width=True)

    if rejected_path.exists():
        st.subheader("Rejection Reasons")
        rejected_reasons = pd.read_csv(rejected_path)
        fig = px.bar(rejected_reasons, x='rejection_reason', y='count',
                     title='Rejected Records by Reason')
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, theme=None)
        st.dataframe(rejected_reasons, use_container_width=True)

    st.subheader("Dataset Summary")
    st.write(f"Total outlets in predictions: **{len(df):,}**")
    st.write(f"Columns available: {len(df.columns)}")


if __name__ == '__main__':
    main()
