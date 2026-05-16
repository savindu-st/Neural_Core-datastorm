"""
Evidence Collector for QuadNova.
Aggregates all technical summaries into a single 'evidence' folder for judges.
"""

import pandas as pd
from pathlib import Path
import shutil

def collect_evidence():
    print("=== QUADNOVA EVIDENCE COLLECTION ===")
    
    evidence_path = Path("outputs/evidence")
    evidence_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Feature Importance
    importance_src = Path("models/feature_importance.csv")
    if importance_src.exists():
        shutil.copy(importance_src, evidence_path / "feature_importance.csv")
        print("COPIED: feature_importance.csv")

    # 2. Segment Summary (From BI Report)
    bi_report_path = Path("outputs/predictions/business_intelligence_report.csv")
    if bi_report_path.exists():
        bi_df = pd.read_csv(bi_report_path)
        segment_summary = bi_df.groupby('outlet_segment').size().reset_index(name='count')
        segment_summary.to_csv(evidence_path / "segment_summary.csv", index=False)
        print("GENERATED: segment_summary.csv")
        
        risk_summary = bi_df.groupby('risk_level').size().reset_index(name='count')
        risk_summary.to_csv(evidence_path / "risk_summary.csv", index=False)
        print("GENERATED: risk_summary.csv")

    # 3. Rejected Reason Summary (Data Forensics)
    rejected_path = Path("data/rejected")
    if rejected_path.exists():
        all_rejections = []
        for file in rejected_path.glob("*.csv"):
            all_rejections.append(pd.read_csv(file))
        
        if all_rejections:
            full_rejected = pd.concat(all_rejections)
            # Ensure columns exist
            if 'dataset' not in full_rejected.columns: full_rejected['dataset'] = 'unknown'
            if 'rejection_reason' not in full_rejected.columns: full_rejected['rejection_reason'] = 'unspecified'
            
            reason_summary = full_rejected.groupby(['dataset', 'rejection_reason']).size().reset_index(name='count')
            reason_summary.to_csv(evidence_path / "rejected_reason_counts.csv", index=False)
            print("GENERATED: rejected_reason_counts.csv")

    print("---------------------------------")
    print(f"Evidence folder ready at: {evidence_path}")
    print("=== COLLECTION COMPLETE ===")

if __name__ == "__main__":
    collect_evidence()
