import json
import pandas as pd
import os
import sys

json_path = os.path.join("data", "raw", "jobs_raw.json")
csv_path = os.path.join("data", "raw", "jobs_raw.csv")

print(f"Loading raw JSON from {json_path}...")
with open(json_path, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

records = raw_data["data"]
df = pd.DataFrame(records)

json_rows, json_cols = df.shape
print(f"JSON record count: {json_rows:,} rows x {json_cols} columns")

print(f"Saving exact data to CSV at {csv_path}...")
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

# Verify CSV by reading it back
print("Verifying saved CSV file...")
df_csv = pd.read_csv(csv_path, dtype=str)
csv_rows, csv_cols = df_csv.shape
print(f"CSV record count: {csv_rows:,} rows x {csv_cols} columns")

# Validation check
rows_match = (json_rows == csv_rows)
cols_match = (json_cols == csv_cols)
cols_list_match = (list(df.columns) == list(df_csv.columns))

print("\n=== VALIDATION RESULT ===")
print(f"Rows match ({json_rows:,} == {csv_rows:,}): {rows_match}")
print(f"Columns count match ({json_cols} == {csv_cols}): {cols_match}")
print(f"Column names match: {cols_list_match}")
print(f"CSV File Size: {os.path.getsize(csv_path) / (1024 * 1024):.2f} MB")

if rows_match and cols_match and cols_list_match:
    print("\nSUCCESS: CSV dataset fully matches JSON raw dataset.")
else:
    print("\nERROR: Mismatch detected in validation.")
    sys.exit(1)
