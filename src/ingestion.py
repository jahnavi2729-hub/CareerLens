import urllib.request
import urllib.error
import json
import os
import sys

API_URL = "https://job-market-api.subhadipk920.workers.dev/50000"
OUTPUT_PATH = os.path.join("data", "raw", "jobs_raw.json")

def ingest_data():
    print(f"Fetching full dataset from {API_URL}...")
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status != 200:
                print(f"Failed to fetch data. HTTP Status: {response.status}")
                sys.exit(1)
            raw_text = response.read().decode('utf-8')
            raw_data = json.loads(raw_text)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response body: {e.read().decode('utf-8')}")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    # Validate response format
    if not isinstance(raw_data, dict) or "data" not in raw_data:
        print("Unexpected data format. Missing 'data' key.")
        sys.exit(1)
    
    if not raw_data.get("success", True):
        print("API returned success=false")
        sys.exit(1)

    records = raw_data["data"]
    records_count = len(records)
    if records_count == 0:
        print("No job records retrieved.")
        columns = []
    else:
        columns = list(records[0].keys())

    # Create directories if they don't exist
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    # Save untouched API response
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(raw_text)

    file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)

    print(f"Status: SUCCESS")
    print(f"Records retrieved: {records_count}")
    print(f"Columns count: {len(columns)}")
    print(f"Columns: {columns}")
    print(f"Raw file path: {OUTPUT_PATH}")
    print(f"File size: {file_size_mb:.2f} MB")

if __name__ == "__main__":
    ingest_data()
