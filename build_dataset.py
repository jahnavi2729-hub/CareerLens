"""
CareerLens Dataset Build Integration Script
-------------------------------------------
1. Downloads baseline dataset from Job Market API (data/raw/jobs_raw.json).
2. Scans data/raw/ for Apify scraped dataset JSON files (e.g. naukri_apify_ci.json, naukri_bangalore_20_raw.json).
3. Converts Apify raw JSON records using src.naukri_adapter.convert_naukri_to_careerlens.
4. Merges baseline and Apify datasets.
5. Deduplicates records by job 'id' (keeping latest/Apify version).
6. Runs feature engineering & cleaning via src.preprocessing.preprocess.
7. Saves processed dataset to data/processed/jobs_clean.csv.
8. Runs data quality validation via src.validation.validate_dataset.
"""

import json
import os
import glob
import sys
from pathlib import Path
import pandas as pd

# Add CareerLens root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from download_full import ingest_full_data
from src.naukri_adapter import convert_naukri_to_careerlens
from src.preprocessing import preprocess
from src.validation import validate_dataset, EXPECTED_COLUMNS


def build_combined_dataset():
    print("==========================================================================")
    print("            CAREERLENS COMBINED DATASET BUILD PIPELINE                    ")
    print("==========================================================================")

    # Step 1: Ensure baseline dataset is present
    raw_baseline_path = os.path.join("data", "raw", "jobs_raw.json")
    if not os.path.exists(raw_baseline_path):
        print("1. Baseline dataset data/raw/jobs_raw.json not found. Fetching from Job Market API...")
        ingest_full_data()
    else:
        print(f"1. Found baseline dataset at {raw_baseline_path}.")

    with open(raw_baseline_path, "r", encoding="utf-8") as f:
        baseline_raw = json.load(f)

    baseline_records = baseline_raw.get("data", baseline_raw)
    df_baseline = pd.DataFrame(baseline_records)
    print(f"   Baseline raw dataset: {len(df_baseline):,} rows x {df_baseline.shape[1]} columns")

    # Step 2: Scan for Apify raw JSON datasets in data/raw/
    apify_files = glob.glob(os.path.join("data", "raw", "naukri_*.json"))
    apify_dfs = []

    for file_path in apify_files:
        try:
            print(f"2. Processing Apify raw dataset: {file_path}...")
            with open(file_path, "r", encoding="utf-8") as f:
                apify_raw = json.load(f)
            
            raw_items = apify_raw.get("data", apify_raw) if isinstance(apify_raw, dict) else apify_raw
            if isinstance(raw_items, list) and len(raw_items) > 0:
                df_converted = convert_naukri_to_careerlens(raw_items)
                apify_dfs.append(df_converted)
                print(f"   Converted {len(df_converted):,} records from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"   Warning: Could not process {file_path}: {e}")

    # Step 3: Merge and Deduplicate by ID
    all_dfs = [df_baseline] + apify_dfs
    df_combined_raw = pd.concat(all_dfs, ignore_index=True)
    initial_count = len(df_combined_raw)

    # Ensure 'id' is numeric for clean deduplication
    df_combined_raw["id"] = pd.to_numeric(df_combined_raw["id"], errors="coerce")
    df_combined_raw = df_combined_raw.dropna(subset=["id"])
    df_combined_raw["id"] = df_combined_raw["id"].astype(int)

    # Deduplicate on job ID, keeping the last occurrence (Apify scraped records take precedence)
    df_dedup = df_combined_raw.drop_duplicates(subset=["id"], keep="last").copy()
    final_raw_count = len(df_dedup)

    print(f"\n3. Data Merge & Deduplication Summary:")
    print(f"   Combined Total Records : {initial_count:,}")
    print(f"   Apify Batches Merged   : {len(apify_dfs)}")
    print(f"   Unique Job IDs (Dedup) : {final_raw_count:,}")

    # Step 4: Preprocess & Filter Schema Columns
    print("\n4. Executing Feature Engineering & Cleaning Pipeline...")
    df_processed = preprocess(df_dedup)
    
    # Select exact expected columns for target schema
    valid_cols = [c for c in EXPECTED_COLUMNS if c in df_processed.columns]
    df_processed = df_processed[valid_cols]

    # Step 5: Save processed output
    output_path = os.path.join("data", "processed", "jobs_clean.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_processed.to_csv(output_path, index=False, encoding="utf-8-sig")
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"5. Processed dataset saved to {output_path} ({file_size_mb:.2f} MB)")

    # Step 6: Validate
    print("\n6. Running Data Quality Validation Checks...")
    val_report = validate_dataset(output_path)
    
    print("\n==========================================================================")
    print(f"BUILD SUCCESSFUL: {final_raw_count:,} unique job records in jobs_clean.csv")
    print("==========================================================================")
    return val_report


if __name__ == "__main__":
    build_combined_dataset()
