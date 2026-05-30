"""
Data Quality Page
Shows data quality metrics and rejected records evidence.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


def load_data():
    """Load data quality information."""
    try:
        predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
        
        quality_summary = None
        rejected_reasons = None
        risk_summary = None
        
        if Path('outputs/evidence/data_quality_summary.csv').exists():
            quality_summary = pd.read_csv('outputs/evidence/data_quality_summary.csv')
        
        if Path('outputs/evidence/rejected_reason_counts.csv').exists():
            rejected_reasons = pd.read_csv('outputs/evidence/rejected_reason_counts.csv')
        
        if Path('outputs/evidence/risk_summary.csv').exists():
            risk_summary = pd.read_csv('outputs/evidence/risk_summary.csv')
        
        return predictions, quality_summary, rejected_reasons, risk_summary
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        return None, None, None, None


st.set_page_config(page_title="Data Quality", page_icon="🔍", layout="wide")

st.title("🔍 Data Quality & Rejected Records Evidence")
st.write("Quality assurance and data cleaning pipeline transparency")

predictions, quality_summary, rejected_reasons, risk_summary = load_data()

if predictions is None:
    st.stop()

# Overview metrics
st.subheader("Data Pipeline Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if quality_summary is not None and 'total_records' in quality_summary.columns:
        total_records = quality_summary['total_records'].values[0] if len(quality_summary) > 0 else 'N/A'
    else:
        total_records = "N/A"
    st.metric("Total Raw Records", total_records)

with col2:
    clean_records = len(predictions)
    st.metric("Clean Records (Used)", clean_records)

with col3:
    if quality_summary is not None and 'rejected_count' in quality_summary.columns:
        rejected_count = quality_summary['rejected_count'].values[0] if len(quality_summary) > 0 else 0
    else:
        rejected_count = 0
    st.metric("Rejected Records", rejected_count)

with col4:
    if total_records != "N/A" and rejected_count > 0:
        rejection_rate = (rejected_count / (clean_records + rejected_count)) * 100
        st.metric("Rejection Rate", f"{rejection_rate:.1f}%")

# Rejection Reasons
st.subheader("Rejection Reasons Breakdown")
if rejected_reasons is not None and len(rejected_reasons) > 0:
    fig = px.pie(
        rejected_reasons,
        names=rejected_reasons.columns[0] if len(rejected_reasons.columns) > 0 else None,
        values=rejected_reasons.columns[1] if len(rejected_reasons.columns) > 1 else None,
        title='Rejected Records by Reason'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(rejected_reasons, use_container_width=True)
else:
    st.info("No rejection reason data available")

# Data Quality Details
st.subheader("Data Quality Metrics")
if quality_summary is not None and len(quality_summary) > 0:
    st.dataframe(quality_summary, use_container_width=True)

# Missing Values
st.subheader("Missing Value Summary")
missing_data = predictions.isnull().sum()
missing_data = missing_data[missing_data > 0].sort_values(ascending=False)
if len(missing_data) > 0:
    fig = px.bar(
        missing_data,
        labels={'index': 'Column', 'value': 'Missing Count'},
        title='Missing Values by Column'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.success("✅ No missing values detected in clean dataset!")

# Coordinate Quality
st.subheader("Geographic Coordinate Quality")
if 'Latitude' in predictions.columns and 'Longitude' in predictions.columns:
    valid_coords = predictions.dropna(subset=['Latitude', 'Longitude'])
    coord_quality = (len(valid_coords) / len(predictions)) * 100
    st.metric("Valid Coordinates", f"{coord_quality:.1f}%")
    
    if len(valid_coords) > 0:
        fig = px.scatter_geo(
            valid_coords,
            lat='Latitude',
            lon='Longitude',
            hover_data=['Outlet_ID'],
            title='Outlet Geographic Distribution',
            projection='natural earth'
        )
        st.plotly_chart(fig, use_container_width=True)

# Risk Summary
st.subheader("Risk Summary")
if risk_summary is not None and len(risk_summary) > 0:
    st.dataframe(risk_summary, use_container_width=True)
else:
    # Show basic risk stats
    if 'Confidence_Score' in predictions.columns:
        low_confidence = len(predictions[predictions['Confidence_Score'] < 0.6])
        st.write(f"⚠️ **{low_confidence}** outlets with confidence score < 0.6 (requires manual review)")

# Data Sources
st.subheader("Data Sources & Integrity")
st.write("""
**Primary Data Sources:**
- Outlet master data (distributor systems)
- Point of Sale (POS) transaction records
- Geographic coordinates (GPS/mapping)
- External POI data (competitor locations)

**Quality Checks Applied:**
✓ Duplicate detection and deduplication
✓ Coordinate validation (valid lat/long range)
✓ Date consistency checks
✓ Outlier detection (extreme sales values)
✓ Missing value assessment
✓ Reference data validation

**Known Data Limitations:**
- Some historical transactions may lack complete geographic data
- Competitor data updated quarterly (may lag current market)
- Seasonal variations in outlet activity not fully captured
- Small outlets may have sparse transaction history
""")

# Download Evidence
st.subheader("📥 Download Evidence Files")
if Path('outputs/evidence/data_quality_summary.csv').exists():
    with open('outputs/evidence/data_quality_summary.csv', 'rb') as f:
        st.download_button(
            label="Download Quality Summary",
            data=f.read(),
            file_name="data_quality_summary.csv",
            mime="text/csv"
        )
