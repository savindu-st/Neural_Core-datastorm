# Gold Layer - Enriched Model Features

This folder contains the final, model-ready features and external POI data produced by the transformation and feature engineering scripts.

**Note on Large Files:**
Due to competition submission size limits, the large `.csv` files in this directory have been removed from the final ZIP/GitHub repository. These files can be perfectly reproduced by running the full pipeline:

```bash
python -m src.data_pipeline.transform
python -m src.features.build_features
```
