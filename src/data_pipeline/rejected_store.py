"""
Systematic Rejected Records Store.

Provides partitioned storage and tracking of rejected records with 
auditable metadata (timestamps, reasons) and aggregates them for dashboard reporting.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RejectedStore:
    """Manages appending and summarizing rejected records in data/rejected/."""
    
    def __init__(self, rejected_dir: str = "data/rejected"):
        self.rejected_path = Path(rejected_dir)
        self.rejected_path.mkdir(parents=True, exist_ok=True)
        self.summary_file = self.rejected_path / "rejected_summary.csv"
        
    def store_rejected(self, df: pd.DataFrame, mask: pd.Series, dataset_name: str, reason: str):
        """Filters, annotates, and appends rejected records to dataset-specific CSV files."""
        count = int(mask.sum())
        if count == 0:
            return
            
        rejected_df = df[mask].copy()
        rejected_df["dataset"] = dataset_name
        rejected_df["rejection_reason"] = reason
        rejected_df["rejection_timestamp"] = datetime.now().isoformat()
        
        # Write to dataset-specific file to maintain schema integrity
        dest_file = self.rejected_path / f"rejected_{dataset_name}.csv"
        
        if dest_file.exists():
            # If the schema matches or if we append directly
            rejected_df.to_csv(dest_file, mode='a', header=False, index=False)
        else:
            rejected_df.to_csv(dest_file, index=False)
            
        logger.warning(f"Quarantined {count} records for {dataset_name} in rejected store. Reason: {reason}")
        self._update_summary(dataset_name, count, reason)

    def _update_summary(self, dataset_name: str, count: int, reason: str):
        """Dynamically tracks and aggregates rejected metrics to rejected_summary.csv."""
        new_row = {
            "dataset": dataset_name,
            "rejection_reason": reason,
            "count": count,
            "last_updated": datetime.now().isoformat()
        }
        
        new_df = pd.DataFrame([new_row])
        
        if self.summary_file.exists():
            summary_df = pd.read_csv(self.summary_file)
            # Check if this dataset & reason combination already exists
            match = (summary_df["dataset"] == dataset_name) & (summary_df["rejection_reason"] == reason)
            if match.any():
                summary_df.loc[match, "count"] += count
                summary_df.loc[match, "last_updated"] = datetime.now().isoformat()
            else:
                summary_df = pd.concat([summary_df, new_df], ignore_index=True)
            summary_df.to_csv(self.summary_file, index=False)
        else:
            new_df.to_csv(self.summary_file, index=False)
            
    def clear_store(self):
        """Clears previous execution audit logs."""
        for file in self.rejected_path.glob("rejected_*.csv"):
            if file.exists():
                file.unlink()
        logger.info("Cleared previous rejected store audit logs.")
