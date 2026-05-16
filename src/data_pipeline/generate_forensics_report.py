"""
Automated Data Forensics and Hygiene Report Generator.

This script aggregates all quarantined records from the 'Rejected' store
and produces a structured summary for the technical report.

Addresses Section 5.3a:
- Documentation of system anomalies trapped.
- Quantifying records quarantined.
- Summary of DE checks efficacy.
"""

import pandas as pd
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_report():
    rejected_path = Path("data/rejected")
    report_path = Path("reports/forensics_summary.md")
    report_path.parent.mkdir(exist_ok=True)
    
    if not rejected_path.exists():
        logger.warning(f"Rejected path {rejected_path} not found. No report generated.")
        return

    logger.info("Generating Data Forensics report...")
    
    # 1. Collect all rejected CSVs
    all_rejections = []
    for file in rejected_path.glob("*.csv"):
        try:
            df = pd.read_csv(file)
            all_rejections.append(df)
        except Exception as e:
            logger.error(f"Error reading {file}: {e}")
            
    if not all_rejections:
        logger.warning("No rejected records found.")
        return
        
    full_rejected_df = pd.concat(all_rejections, ignore_index=True)
    
    # 2. Safety Check: Ensure columns exist (for older files)
    if 'dataset' not in full_rejected_df.columns:
        full_rejected_df['dataset'] = 'unknown'
    if 'rejection_reason' not in full_rejected_df.columns:
        full_rejected_df['rejection_reason'] = 'unspecified anomaly'

    # 3. Summarize by Dataset and Reason
    summary = full_rejected_df.groupby(['dataset', 'rejection_reason']).size().reset_index(name='count')
    total_rejected = summary['count'].sum()
    
    # 4. Create Markdown Report
    with open(report_path, "w") as f:
        f.write("# Data Forensics and Hygiene Audit Report\n\n")
        f.write(f"**Total Records Quarantined:** {total_rejected}\n\n")
        
        f.write("## 1. System Anomaly Summary\n")
        f.write("This table summarizes the types of legacy system artifacts and human data-entry errors trapped during the Silver-layer cleaning process.\n\n")
        
        # Write table
        f.write("| Dataset | Rejection Reason | Frequency |\n")
        f.write("|---------|------------------|-----------|\n")
        for _, row in summary.iterrows():
            f.write(f"| {row['dataset']} | {row['rejection_reason']} | {row['count']} |\n")
        
        f.write("\n## 2. Technical Methodology\n")
        f.write("- **Null Validation**: Enforced mandatory master data fields.\n")
        f.write("- **Referential Integrity**: Cross-referenced transactions against validated outlet masters to eliminate orphan signals.\n")
        f.write("- **Value Range Assertions**: Trapped negative volumes and billing value artifacts from ERP sync errors.\n")
        f.write("- **Statistical Forensics**: Used IQR-based outlier detection to isolate 'ghost entries' (Volume > 10x IQR) from true market demand.\n")
        
    logger.info(f"Forensics report generated at {report_path}")

if __name__ == "__main__":
    generate_report()
