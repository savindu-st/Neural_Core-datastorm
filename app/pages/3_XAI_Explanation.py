"""
XAI Explanation Page
Outlet drill-down page showing model explanations and drivers.
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


def load_data():
    """Load explanation data."""
    try:
        explanations = pd.read_csv('outputs/predictions/outlet_explanations.csv')
        allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')
        return explanations, allocations
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        return None, None


st.set_page_config(page_title="XAI Explanation", page_icon="🔬", layout="wide")
apply_modern_theme()

st.title("🔬 Outlet-Level XAI Explanation")
st.write("Understand why each outlet received its predicted potential and recommended actions")

explanations, allocations = load_data()

if explanations is None:
    st.stop()

if len(explanations) == 0:
    st.warning("No outlet explanations available. Please run the outlet_reasoning.py script first.")
    st.stop()

# Outlet selector
outlet_id = st.selectbox(
    "Select an Outlet",
    sorted(explanations['Outlet_ID'].unique()),
    format_func=str
)

# Get explanation data
explanation_row = explanations[explanations['Outlet_ID'] == outlet_id]
if len(explanation_row) == 0:
    st.error("Outlet not found")
    st.stop()

row = explanation_row.iloc[0]

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Predicted Potential", f"{row['Predicted_Potential']:,.0f}L/month")
with col2:
    st.metric("Confidence Level", f"{row['Confidence_Level']:.0%}")
with col3:
    st.metric("Segment", row['Segment'])
with col4:
    # Get allocation if available
    allocation_row = allocations[allocations['Outlet_ID'] == outlet_id]
    if not allocation_row.empty and 'Trade_Spend_Allocation_LKR' in allocation_row.columns:
        allocation = allocation_row.iloc[0]['Trade_Spend_Allocation_LKR']
        st.metric("Recommended Budget", f"₹{allocation:,.0f}")

st.divider()

# Business Explanation
st.subheader("📊 Business Explanation")
st.markdown(f"""
{row['Business_Explanation']}
""")

# Key Drivers
st.subheader("🎯 Key Performance Drivers")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**✅ Positive Drivers** (boosting potential)")
    positive_drivers = str(row['Top_Positive_Drivers']).split(',') if pd.notna(row['Top_Positive_Drivers']) else []
    for driver in positive_drivers:
        st.write(f"• {driver.strip()}")

with col2:
    st.markdown("**❌ Negative Drivers** (limiting potential)")
    negative_drivers = str(row['Top_Negative_Drivers']).split(',') if pd.notna(row['Top_Negative_Drivers']) else []
    for driver in negative_drivers:
        st.write(f"• {driver.strip()}")

st.divider()

# Recommended Action
st.subheader("💡 Recommended Action")
st.info(row['Recommended_Action'])

st.divider()

# Confidence explanation
st.subheader("📈 Confidence Interpretation")
confidence = row['Confidence_Level']
if confidence >= 0.8:
    confidence_text = "🟢 **High Confidence** - Model has strong signal. Recommendations are reliable."
elif confidence >= 0.6:
    confidence_text = "🟡 **Medium Confidence** - Adequate data but some uncertainty remains."
else:
    confidence_text = "🔴 **Low Confidence** - Limited data. Monitor closely before major investment."

st.write(confidence_text)

# Export explanation
st.subheader("📥 Export")
st.download_button(
    label="Download This Explanation (JSON)",
    data=pd.DataFrame([row]).to_json(orient='records', indent=2),
    file_name=f"outlet_{outlet_id}_explanation.json",
    mime="application/json"
)

# Browse other outlets
st.subheader("🔗 Browse Similar Outlets")
same_segment = explanations[explanations['Segment'] == row['Segment']].head(5)
if len(same_segment) > 1:
    st.write(f"Other outlets in **{row['Segment']}** segment:")
    st.dataframe(
        same_segment[['Outlet_ID', 'Predicted_Potential', 'Confidence_Level']],
        use_container_width=True
    )
