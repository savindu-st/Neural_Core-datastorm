# Data Storm 7.0 — Potential-Based Allocation Model
## Team: QuadNova

### Problem Statement
The objective of this challenge is to estimate the latent maximum monthly beverage purchase potential for traditional retail outlets across Sri Lanka for January 2026. 

Historical sales are treated as censored demand because observed sales may be limited by operational constraints such as stockouts, delivery caps, or credit limitations. Our approach utilizes **Tobit (Censored) Regression** and advanced **Spatial Analytics** to uncap this potential.

---

# Project Structure (Lakehouse Architecture)
```text
QuadNova-datastorm/
│
├── data/
│   ├── bronze/     # Raw Ingestion (Untouched CSVs)
│   ├── silver/     # Cleaned Data (Sanitized Parquet files)
│   ├── gold/       # Enriched Data (Model-ready Features & POIs)
│   ├── rejected/   # Quarantined Records (Data Forensics Store)
│
├── src/
│   ├── data_pipeline/   # Ingestion, Cleaning (DQ Engine), Transformation
│   ├── features/        # Advanced Feature Engineering (Saturation, Stability)
│   ├── models/          # Tobit Regression, Training, Prediction
│   ├── scraper/         # High-performance BBox POI Scraper
│   └── utils/           # Shared DQ Library & Config handlers
│
├── reports/             # Forensics Summary & GenAI Transparency Log
├── outputs/
│   ├── predictions/     # quadnova_predictions.csv
│
├── models/              # Serialized Model Artifacts
└── README.md
```

---

# Running the Pipeline End-to-End

### 1. Setup Environment
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Add Raw Data
Place all provided CSV files in `data/bronze/`.

### 3. Execute Pipeline
```bash
# Data Forensics & Cleaning
python -m src.data_pipeline.clean

# External POI Acquisition (BBox + KD-Tree)
python -m src.scraper.poi_fast_scraper

# Gold Layer Transformation
python -m src.data_pipeline.transform

# Advanced Feature Engineering
python -m src.features.build_features

# Model Training & Explainability
python -m src.models.train_model

# Generate Final Submission & BI Report
python -m src.models.predict

# Generate Technical Audit Report
python -m src.data_pipeline.generate_forensics_report
```

---

# Final Deliverables
*   **Predictions**: `outputs/predictions/quadnova_predictions.csv`
*   **BI Report**: `outputs/predictions/business_intelligence_report.csv`
*   **Forensics Audit**: `reports/forensics_summary.md`
*   **GenAI Log**: `reports/genai_log.md`

---

# Team Workflow Sequence

### Member 1: Data Engineering & Forensics
*   Developed the **Bronze → Silver → Gold** Lakehouse pipeline.
*   Built the **Reusable DQ Engine** and the automated **Forensics Audit** system.
*   Managed referential integrity and statistical outlier detection.

### Member 2: Modeling & Features
*   Implemented the **Tobit Regression (Censored)** model logic.
*   Engineered advanced features: **Market Saturation Index**, **Temporal Stability**, and **Outlet Density**.
*   Developed the **Business Intelligence Layer** (Confidence Scoring, Segmentation).

### Member 3: Scraper & Documentation
*   Developed the **High-Performance Bounding Box Scraper** (Scipy KD-Tree).
*   Managed the **GenAI Transparency Log** and technical documentation.
*   Designed the **Business Recommendation** engine for final reporting.

---

# Workflow Sequence

## PHASE 1 — PROJECT SETUP (Hour 0–1)

### All Members

1. Clone/open project.
2. Create folder structure.
3. Add raw CSVs into:

```text
data/bronze/
```

4. Check dataset columns.
5. Confirm file names.

### Member 1 Starts

* `src/data_pipeline/ingest.py`
* `src/data_pipeline/clean.py`

### Member 2 Starts

* Inspect datasets.
* Plan feature list.
* Prepare latent demand approach.

### Member 3 Starts

* `src/scraper/poi_scraper.py` setup.
* Report template.

---

## PHASE 2 — DATA CLEANING + POI COLLECTION (Hour 1–3)

### Member 1

1. Build cleaning checks:

   * nulls
   * duplicates
   * invalid coordinates
   * invalid dates
   * negative sales

2. Save rejected records:

```text
data/rejected/
```

3. Save cleaned files:

```text
data/silver/
```

### Member 2

1. Wait for sample cleaned dataset.
2. Prepare feature engineering logic.
3. Prepare latent demand formula.
4. Create:

```text
src/features/build_features.py
```

### Member 3

1. Start POI scraping.

Collect:

* schools
* hospitals
* restaurants
* bus stands
* fuel stations

2. Save:

```text
data/gold/poi_data.csv
```

3. Start simple charts.

---

## PHASE 3 — GOLD DATASET + FEATURES (Hour 3–5)

### Member 1

1. Merge all cleaned datasets.
2. Create:

```text
data/gold/final_dataset.csv
```

3. Send dataset to Member 2.

### Member 2

1. Load:

```text
data/gold/final_dataset.csv
```

2. Merge:

```text
data/gold/poi_data.csv
```

3. Create features:

   * avg_sales
   * historical_max_sales
   * sales_std
   * growth_rate
   * inactive_days
   * poi_score
   * seasonality_score

### Member 3

1. Finish POI dataset.
2. Finish charts/maps.
3. Start `README.md`.
4. Start `gemini.md`.

---

## PHASE 4 — MODELING + REPORT BUILDING (Hour 5–7)

### Member 2

1. Build latent demand logic.
2. Create potential formula.
3. Optional ML refinement.
4. Generate predictions.

Save:

```text
outputs/predictions/teamname_predictions.csv
```

### Member 1

1. Final validation.

2. Check:

   * nulls
   * duplicates
   * dataset consistency

3. Help debugging.

### Member 3

1. Build report sections.
2. Add charts/screenshots.
3. Add architecture diagram.
4. Add GenAI usage section.

---

## PHASE 5 — FINALIZATION (Hour 7–9)

### Member 2

1. Final prediction validation.
2. Check:

   * no negative predictions
   * no nulls
   * no duplicates

### Member 1

1. Cleanup repo.
2. Verify all folders.
3. Final debugging support.

### Member 3

1. Finalize PDF report.
2. Finalize `README.md`.
3. Prepare submission folder.

---

## PHASE 6 — SUBMISSION (Hour 9–10)

### All Members

1. Verify:

   * predictions CSV
   * report PDF
   * repo structure

2. Final package:

```text
outputs/submission/
```

3. Upload:

   * GitHub / ZIP
   * PDF
   * predictions CSV

4. Final sanity check before submission.
