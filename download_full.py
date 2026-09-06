import urllib.request
import json
import os
import sys

API_URL = "https://job-market-api.subhadipk920.workers.dev/50000"
OUTPUT_PATH = os.path.join("data", "raw", "jobs_raw.json")

def ingest_full_data():
    print(f"Fetching full dataset from {API_URL}...")
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status != 200:
                print(f"Failed to fetch data. HTTP Status: {response.status}")
                sys.exit(1)
            raw_bytes = response.read()
            raw_text = raw_bytes.decode('utf-8')
            raw_data = json.loads(raw_text)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    if not isinstance(raw_data, dict) or "data" not in raw_data:
        print("Unexpected data format. Missing 'data' key.")
        sys.exit(1)

    records = raw_data["data"]
    records_count = len(records)

    # Save untouched raw text / json payload directly
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(raw_text)

    file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)

    print(f"Status: SUCCESS")
    print(f"Retrieved Record Count: {records_count}")
    print(f"API Returned Count: {raw_data.get('returned_count')}")
    print(f"Raw File Path: {OUTPUT_PATH}")
    print(f"File Size: {file_size_mb:.2f} MB")
    print(f"Response Keys: {list(raw_data.keys())}")
    if records_count > 0:
        print(f"Sample Record Keys ({len(records[0].keys())} columns): {list(records[0].keys())}")

if __name__ == "__main__":
    ingest_full_data()
