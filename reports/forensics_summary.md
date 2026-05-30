# Data Forensics and Hygiene Audit Report

**Total Records Quarantined:** 50216

## 1. System Anomaly Summary
This table summarizes the types of legacy system artifacts and human data-entry errors trapped during the Silver-layer cleaning process.

| Dataset | Rejection Reason | Frequency |
|---------|------------------|-----------|
| outlet_coordinates | Geospatial Out-of-Bounds/Format | 41 |
| outlet_master | Mandatory Field Null (Outlet_Size) | 197 |
| transactions | Transaction Validation: negative_bill | 4754 |
| transactions | Transaction Validation: negative_volume | 4854 |
| transactions | Transaction Validation: referential_orphan | 11605 |
| transactions | Transaction Validation: statistical_outlier | 28765 |

## 2. Technical Methodology
- **Null Validation**: Enforced mandatory master data fields.
- **Referential Integrity**: Cross-referenced transactions against validated outlet masters to eliminate orphan signals.
- **Value Range Assertions**: Trapped negative volumes and billing value artifacts from ERP sync errors.
- **Statistical Forensics**: Used IQR-based outlier detection to isolate 'ghost entries' (Volume > 10x IQR) from true market demand.
