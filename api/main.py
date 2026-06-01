import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
from pathlib import Path

app = FastAPI(title="QuadNova API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_data():
    """Loads and enriches the data, returning a Pandas DataFrame."""
    try:
        predictions = pd.read_csv(PROJECT_ROOT / 'outputs/predictions/quadnova_predictions.csv')
    except Exception as e:
        return None, f"Failed to load predictions: {e}"

    # Load optional files
    allocations, explanations, segments, features = None, None, None, None
    try: allocations = pd.read_csv(PROJECT_ROOT / 'outputs/predictions/quadnova_budget_allocations.csv')
    except: pass
    try: explanations = pd.read_csv(PROJECT_ROOT / 'outputs/predictions/outlet_explanations.csv')
    except: pass
    try: segments = pd.read_csv(PROJECT_ROOT / 'data/gold/outlet_segments.csv')
    except: pass
    try: features = pd.read_csv(PROJECT_ROOT / 'data/gold/model_features.csv')
    except: pass

    # Enrich
    enriched = predictions.copy()
    
    if features is not None:
        feat_cols = [c for c in ['Outlet_ID', 'Province', 'Distributor_ID', 'avg_monthly_liters', 'Latitude', 'Longitude', 'Outlet_Type', 'Outlet_Size'] if c in features.columns]
        enriched = enriched.merge(features[feat_cols], on='Outlet_ID', how='left')

    if segments is not None:
        seg_cols = [c for c in ['Outlet_ID', 'outlet_segment', 'confidence_score', 'potential_gap'] if c in segments.columns]
        enriched = enriched.merge(segments[seg_cols], on='Outlet_ID', how='left')

    if allocations is not None:
        enriched = enriched.merge(allocations, on='Outlet_ID', how='left')

    # Replace NaN with None for JSON serialization
    enriched = enriched.replace({np.nan: None})
    if explanations is not None:
        explanations = explanations.replace({np.nan: None})
        
    return enriched, explanations, None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "QuadNova API is running"}

@app.get("/api/overview")
def get_overview():
    df, _, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)

    total_outlets = len(df)
    avg_potential = df['Maximum_Monthly_Liters'].mean()
    total_budget = df['Trade_Spend_Allocation_LKR'].sum() if 'Trade_Spend_Allocation_LKR' in df.columns else 0
    
    # Check if confidence score exists
    avg_confidence = 0
    if 'confidence_score' in df.columns:
        avg_confidence = df['confidence_score'].mean()
        if avg_confidence > 1:
            avg_confidence = avg_confidence / 100.0
            
    # Segments
    segments = {}
    if 'outlet_segment' in df.columns:
        segments = df['outlet_segment'].value_counts().to_dict()

    # Scatter data limit 1000 for perf
    scatter_data = []
    if 'avg_monthly_liters' in df.columns:
        sampled = df.dropna(subset=['avg_monthly_liters', 'Maximum_Monthly_Liters']).sample(min(1000, len(df)))
        scatter_data = sampled[['Outlet_ID', 'avg_monthly_liters', 'Maximum_Monthly_Liters']].to_dict('records')

    return {
        "metrics": {
            "total_outlets": total_outlets,
            "avg_potential": avg_potential,
            "total_budget": total_budget,
            "avg_confidence": avg_confidence
        },
        "segments": segments,
        "scatter_data": scatter_data
    }

@app.get("/api/outlets")
def get_outlets(limit: int = 500, offset: int = 0, province: str = None, distributor: str = None, search: str = None):
    df, _, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)

    if province and province != "All":
        df = df[df['Province'] == province]
    if distributor and distributor != "All":
        df = df[df['Distributor_ID'].astype(str) == distributor]
    if search:
        df = df[df['Outlet_ID'].astype(str).str.contains(search, case=False)]

    total = len(df)
    paginated = df.iloc[offset:offset+limit]
    return {
        "total": total,
        "items": paginated.to_dict('records')
    }

@app.get("/api/outlets/filters")
def get_filters():
    df, _, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)

    provinces = ["All"]
    if 'Province' in df.columns:
        provinces += sorted(df['Province'].dropna().unique().tolist())

    distributors = ["All"]
    if 'Distributor_ID' in df.columns:
        distributors += sorted(df['Distributor_ID'].dropna().astype(str).unique().tolist())

    return {
        "provinces": provinces,
        "distributors": distributors
    }

@app.get("/api/xai/list")
def get_xai_list():
    _, explanations, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)
    if explanations is None:
        return []
    return explanations['Outlet_ID'].astype(str).tolist()

@app.get("/api/xai/{outlet_id}")
def get_xai_explanation(outlet_id: str):
    df, explanations, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)
        
    if explanations is None:
        raise HTTPException(status_code=404, detail="Explanations not generated yet")

    exp_row = explanations[explanations['Outlet_ID'].astype(str) == outlet_id]
    if len(exp_row) == 0:
        raise HTTPException(status_code=404, detail="Outlet not found")

    return exp_row.iloc[0].to_dict()

@app.get("/api/budget")
def get_budget():
    df, _, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)

    # Convert all numeric columns up-front to avoid dtype object errors
    for col in ['Trade_Spend_Allocation_LKR', 'Expected_Incremental_Liters', 'Risk_Adjusted_ROI']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    total_budget = df['Trade_Spend_Allocation_LKR'].sum() if 'Trade_Spend_Allocation_LKR' in df.columns else 0
    total_outlets = int(df['Trade_Spend_Allocation_LKR'].notna().sum()) if 'Trade_Spend_Allocation_LKR' in df.columns else 0
    expected_incremental = df['Expected_Incremental_Liters'].sum() if 'Expected_Incremental_Liters' in df.columns else 0
    avg_allocation = float(total_budget) / total_outlets if total_outlets > 0 else 0

    # Top 20 outlets
    top_outlets = []
    if 'Trade_Spend_Allocation_LKR' in df.columns:
        top_df = df.dropna(subset=['Trade_Spend_Allocation_LKR']).nlargest(20, 'Trade_Spend_Allocation_LKR')
        cols = [c for c in ['Outlet_ID', 'Trade_Spend_Allocation_LKR', 'Expected_Incremental_Liters', 'Distributor_ID'] if c in top_df.columns]
        top_df = top_df[cols].replace({np.nan: None})
        top_outlets = top_df.to_dict('records')
        
    return {
        "summary": {
            "total_budget": total_budget,
            "total_outlets": total_outlets,
            "avg_allocation": avg_allocation,
            "expected_incremental": expected_incremental
        },
        "top_outlets": top_outlets
    }

@app.get("/api/quality")
def get_quality():
    """Return real data quality evidence from CSVs."""
    result = {"datasets": [], "rejections": [], "totals": {"rows_in": 0, "rows_out": 0, "rows_flagged": 0, "rows_dropped": 0}}
    try:
        dq = pd.read_csv(PROJECT_ROOT / 'outputs/evidence/data_quality_summary.csv')
        result["datasets"] = dq.to_dict('records')
        result["totals"] = {
            "rows_in": int(dq['rows_in'].sum()),
            "rows_out": int(dq['rows_out'].sum()),
            "rows_flagged": int(dq['rows_flagged'].sum()),
            "rows_dropped": int(dq['rows_dropped'].sum()),
        }
    except Exception:
        pass
    try:
        rej = pd.read_csv(PROJECT_ROOT / 'outputs/evidence/rejected_reason_counts.csv')
        result["rejections"] = rej.to_dict('records')
    except Exception:
        pass
    return result

@app.get("/api/budget/simulate")
def simulate_budget(total_budget: float = 5000000):
    """Re-allocate budget proportionally given a new total."""
    df, _, err = load_data()
    if err:
        raise HTTPException(status_code=500, detail=err)

    for col in ['Trade_Spend_Allocation_LKR', 'Expected_Incremental_Liters', 'Risk_Adjusted_ROI']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Trade_Spend_Allocation_LKR' not in df.columns:
        raise HTTPException(status_code=400, detail="No allocation data")

    original_total = df['Trade_Spend_Allocation_LKR'].sum()
    if original_total == 0:
        raise HTTPException(status_code=400, detail="Original budget is zero")

    scale = total_budget / original_total
    df['Simulated_Allocation'] = df['Trade_Spend_Allocation_LKR'] * scale
    if 'Expected_Incremental_Liters' in df.columns:
        df['Simulated_Incremental'] = df['Expected_Incremental_Liters'] * scale

    funded = df.dropna(subset=['Trade_Spend_Allocation_LKR'])
    top20 = funded.nlargest(20, 'Simulated_Allocation')
    cols = [c for c in ['Outlet_ID', 'Simulated_Allocation', 'Simulated_Incremental', 'Distributor_ID'] if c in top20.columns]

    return {
        "total_budget": total_budget,
        "total_outlets": int(funded['Trade_Spend_Allocation_LKR'].notna().sum()),
        "avg_allocation": total_budget / max(len(funded), 1),
        "expected_incremental": float(funded['Simulated_Incremental'].sum()) if 'Simulated_Incremental' in funded.columns else 0,
        "top_outlets": top20[cols].replace({np.nan: None}).to_dict('records')
    }


if __name__ == "__main__":
    import os
    port = int(os.getenv("QUADNOVA_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
