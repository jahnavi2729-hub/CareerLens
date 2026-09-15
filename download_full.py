import urllib.request
import urllib.error
import http.client
import json
import os
import sys
import time

API_URL = "https://job-market-api.subhadipk920.workers.dev/50000"
OUTPUT_PATH = os.path.join("data", "raw", "jobs_raw.json")

def download_stream_with_retries(url, max_retries=3, timeout=120):
    """
    Downloads URL content using streaming chunks with automatic retries and
    IncompleteRead exception handling to safely receive large payloads (~47MB).
    """
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    for attempt in range(1, max_retries + 1):
        print(f"Fetching dataset from {url} (Attempt {attempt}/{max_retries})...")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    print(f"  HTTP Error Status: {response.status}")
                    if attempt < max_retries:
                        time.sleep(2 * attempt)
                        continue
                    sys.exit(1)
                
                # Chunked reading to avoid IncompleteRead on large payloads
                chunks = []
                while True:
                    try:
                        chunk = response.read(1024 * 1024)  # 1MB chunk
                        if not chunk:
                            break
                        chunks.append(chunk)
                    except http.client.IncompleteRead as e:
                        print(f"  Warning: IncompleteRead encountered ({len(e.partial):,} bytes read). Appending partial content.")
                        chunks.append(e.partial)
                        break
                
                raw_bytes = b"".join(chunks)
                raw_text = raw_bytes.decode('utf-8', errors='ignore')
                raw_data = json.loads(raw_text)
                
                if isinstance(raw_data, dict) and "data" in raw_data and len(raw_data["data"]) > 0:
                    print(f"  Successfully received {len(raw_data['data']):,} records ({len(raw_bytes)/(1024*1024):.2f} MB).")
                    return raw_text, raw_data
                else:
                    print("  Downloaded payload failed JSON verification or contained empty data.")
        except Exception as e:
            print(f"  Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
    
    print(f"Error: Failed to reliably download dataset after {max_retries} attempts.")
    sys.exit(1)


def ingest_full_data():
    raw_text, raw_data = download_stream_with_retries(API_URL, max_retries=3, timeout=120)

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
