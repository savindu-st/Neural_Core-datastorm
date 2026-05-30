import streamlit as st
import plotly.io as pio

def apply_modern_theme():
    """Injects advanced custom CSS to create a modern, React-like UI."""
    
    # Configure global Plotly theme
    pio.templates.default = "plotly_dark"
    
    st.markdown("""
        <style>
            /* Import Inter Font */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            /* Apply global font */
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif !important;
            }
            
            /* App Background */
            .stApp {
                background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                color: #f8fafc;
            }
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {
                background: rgba(15, 23, 42, 0.7);
                backdrop-filter: blur(12px);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            /* Main Header */
            .main-header {
                font-weight: 700;
                background: linear-gradient(to right, #3b82f6, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 2rem;
                font-size: 3rem !important;
            }
            
            h1, h2, h3 {
                color: #f8fafc !important;
                font-weight: 600 !important;
                letter-spacing: -0.025em;
            }
            
            /* Metric Cards (Glassmorphism) */
            [data-testid="stMetric"] {
                background: rgba(30, 41, 59, 0.6);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
            }
            
            [data-testid="stMetric"]:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
                border-color: rgba(59, 130, 246, 0.5);
            }
            
            [data-testid="stMetricValue"] {
                font-size: 2rem !important;
                font-weight: 700 !important;
                color: #60a5fa !important;
            }
            
            [data-testid="stMetricLabel"] {
                font-size: 0.9rem !important;
                font-weight: 500 !important;
                color: #94a3b8 !important;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            /* Buttons */
            .stButton > button {
                background: linear-gradient(to right, #3b82f6, #6366f1);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0.5rem 1rem;
                transition: opacity 0.2s, transform 0.1s;
            }
            
            .stButton > button:hover {
                opacity: 0.9;
                transform: scale(1.02);
                color: white;
            }
            
            /* Dataframes / Tables */
            [data-testid="stDataFrame"] {
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.1);
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background-color: rgba(30, 41, 59, 0.8) !important;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
            }
            
            /* Selectboxes and Inputs */
            .stSelectbox > div > div, .stTextInput > div > div {
                background-color: rgba(15, 23, 42, 0.6) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 8px !important;
                color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)
