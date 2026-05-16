"""
Final Submission Validator for QuadNova.
Verifies the integrity of the prediction CSV before submission.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def validate():
    print("=== QUADNOVA SUBMISSION AUDIT ===")
    
    pred_path = Path("outputs/predictions/quadnova_predictions.csv")
    master_path = Path("data/bronze/outlet_master.csv")
    
    if not pred_path.exists():
        print(f"ERROR: {pred_path} not found!")
        return

    df = pd.read_csv(pred_path)
    
    # 1. Column Check
    required_cols = ['Outlet_ID', 'Maximum_Monthly_Liters']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        print(f"FAILED: Missing columns {missing_cols}")
    else:
        print("PASSED: Column Structure")

    # 2. Null Check
    null_count = df.isnull().sum().sum()
    if null_count > 0:
        print(f"FAILED: Found {null_count} null values!")
    else:
        print("PASSED: No Nulls")

    # 3. Negative Check
    neg_count = (df['Maximum_Monthly_Liters'] < 0).sum()
    if neg_count > 0:
        print(f"FAILED: Found {neg_count} negative predictions!")
    else:
        print("PASSED: No Negative Values")

    # 4. Duplicate Check
    dup_count = df['Outlet_ID'].duplicated().sum()
    if dup_count > 0:
        print(f"FAILED: Found {dup_count} duplicate Outlet_IDs!")
    else:
        print("PASSED: No Duplicates")

    # 5. Row Count Check (Comparison with Bronze Master)
    if master_path.exists():
        master_ids = pd.read_csv(master_path)['Outlet_ID'].unique()
        pred_ids = df['Outlet_ID'].unique()
        
        missing_ids = set(master_ids) - set(pred_ids)
        if len(missing_ids) > 0:
            print(f"FAILED: {len(missing_ids)} outlets from master missing in predictions!")
        else:
            print(f"PASSED: All {len(master_ids)} master outlets accounted for")
    
    print("---------------------------------")
    print(f"Final Count: {len(df)} Outlets")
    print(f"Mean Potential: {df['Maximum_Monthly_Liters'].mean():.2f}")
    print("=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    validate()
