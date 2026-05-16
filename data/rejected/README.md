# Rejected Records - Data Forensics Store

This folder acts as the **Quarantine Zone** for the pipeline. Every record that fails a Data Quality check is stored here with a documented failure reason.

**Why this is important:**
As per the competition requirements (Section 4.1), we do not silently drop "messy" data. Instead, we perform **Data Forensics** to separate true market signals from legacy system artifacts.

**Contents:**
- `dataset_rejected_timestamp.csv`: Individual quarantined batches.
- These records are excluded from the Silver and Gold layers to ensure model robustness.

Detailed summaries of these rejections can be found in the `reports/forensics_summary.md` and `outputs/evidence/rejected_reason_counts.csv` files.
