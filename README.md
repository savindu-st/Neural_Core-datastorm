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
├── config/              # Pipeline Configurations (YAML)
├── data/
│   ├── bronze/          # Raw Ingestion (Untouched CSVs)
│   ├── silver/          # Cleaned Data (Sanitized Parquet files)
│   ├── gold/            # Enriched Data (Model-ready Features & POIs)
│   ├── external/        # External Data (Scraped POIs)
│   ├── quarantine/      # Suspicious records flagged for review
│   ├── rejected/        # Quarantined Records (Data Forensics Store)
│
├── models/              # Serialized Model Artifacts
├── notebooks/           # Jupyter Notebooks for EDA
├── outputs/
│   ├── charts/          # Generated Visualizations
│   ├── evidence/        # Explainability evidence
│   ├── predictions/     # quadnova_predictions.csv
│   └── submission/      # Final packages
│
├── reports/             # Forensics, Data Eng Docs & GenAI Transparency Log
├── src/
│   ├── data_pipeline/   # Ingestion, Cleaning (DQ Engine), Transformation
│   ├── features/        # Advanced Feature Engineering (Saturation, Stability)
│   ├── models/          # Tobit Regression, Training, Prediction
│   ├── scraper/         # High-performance BBox POI Scraper
│   └── utils/           # Shared DQ Library & Config handlers
│
├── tests/               # Automated Unit & Integration Tests
└── README.md
```

---

# Execution & Deployment

You can run the entire system (data pipelines, modeling, and interactive web dashboard) in two different ways:

### Option A: Local Execution (Recommended)
This runs the entire end-to-end data engineering pipeline, model training, GenAI explanation generation, and launches the web application dashboard automatically.

1. **Setup Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Add Raw Data**:
   Place all raw competition CSV files in `data/bronze/`.

3. **Run Pipeline & Web Application**:
   ```bash
   python run_pipeline.py
   ```
   *This single command runs all pipeline stages sequentially (ingestion, cleaning, POI scraping, feature engineering, Tobit modeling, XAI, and visualization generation) and starts both the FastAPI backend (port `8000`) and the React dashboard (port `3000`).*

---

### Option B: Dockerized Web App Execution
You can build and start the interactive web application dashboard stack using Docker Compose:

1. **Start Services**:
   ```bash
   docker-compose up --build
   ```
   *This command spins up two services:*
   *   **Backend**: FastAPI service running on `http://localhost:8000`
   *   **Frontend**: React / Vite dashboard running on `http://localhost:3000`

---

# Final Deliverables
*   **Predictions**: `outputs/predictions/quadnova_predictions.csv`
*   **BI Report**: `outputs/predictions/business_intelligence_report.csv`
*   **Data Engineering & Forensics Report**: `reports/data_engineering_and_forensics.md`
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

* `src/scraper/poi_fast_scraper.py` setup.
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
