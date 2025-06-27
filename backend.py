import requests
import time
import json
import os

# --- CONFIGURATION ---
# Load environment variables with sensible defaults
APE_KEY = os.environ.get("MONKEYTYPE_APE_KEY")
UPDATES_PER_DAY = int(os.environ.get("UPDATES_PER_DAY", 1))

# Calculate sleep time. If UPDATES_PER_DAY is 0 or less, sleep for a very long time.
# This prevents a division-by-zero error and stops the loop.
SLEEP_INTERVAL_SECONDS = (24 * 60 * 60) / UPDATES_PER_DAY if UPDATES_PER_DAY > 0 else 99999999

BASE_URL = "https://api.monkeytype.com/results"
HEADERS = {
    "Authorization": f"ApeKey {APE_KEY}"
}
SAVE_FILE = "monkeytype_results.json"


def load_existing_results():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: JSON file is corrupted. Starting fresh.")
            return []
    return []

def get_latest_timestamp_and_ids(results):
    if not results:
        return None, set()
    latest_timestamp = max(r.get("timestamp", 0) for r in results)
    ids_at_latest = {r["_id"] for r in results if r.get("timestamp") == latest_timestamp}
    return latest_timestamp, ids_at_latest

def fetch_new_results(since_timestamp):
    all_new = []
    limit = 1000
    offset = 0

    while True:
        print(f"Fetching with offset {offset}...")
        params = {"limit": limit, "offset": offset}
        if since_timestamp:
            params["onOrAfterTimestamp"] = since_timestamp

        try:
            response = requests.get(BASE_URL, headers=HEADERS, params=params)
            response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
            data = response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from API response: {e}")
            break

        if not data:
            print("No more data from API.")
            break

        all_new.extend(data)
        if len(data) < limit:
            break

        offset += limit
        time.sleep(1) # Be polite to the API

    print(f"Fetched a total of {len(all_new)} new results from the API.")
    return all_new

def merge_results(existing, new, latest_ts, existing_ids_at_latest_ts):
    # Use a dictionary for efficient de-duplication and updates
    combined = {r["_id"]: r for r in existing}

    new_results_count = 0
    for r in new:
        ts = r.get("timestamp", 0)
        _id = r.get("_id")

        # Skip results that are older than our latest known timestamp
        if latest_ts and ts < latest_ts:
            continue
        # Skip results with the same timestamp and ID (duplicates from the overlap)
        if ts == latest_ts and _id in existing_ids_at_latest_ts:
            continue
        
        # This is a new or updated result
        if _id not in combined:
            new_results_count += 1
        combined[_id] = r
    
    print(f"Added or updated {new_results_count} records.")
    return sorted(combined.values(), key=lambda x: x.get("timestamp", 0))

def run_fetch_cycle():
    """Performs one complete fetch and update cycle."""
    if not APE_KEY:
        print("Error: MONKEYTYPE_KEY environment variable is not set. Exiting.")
        return

    print("--- Starting fetch cycle ---")
    existing_results = load_existing_results()
    latest_ts, ids_at_latest_ts = get_latest_timestamp_and_ids(existing_results)

    if latest_ts:
        print(f"Latest existing timestamp is: {latest_ts}")

    new_results = fetch_new_results(latest_ts)
    if new_results:
        merged = merge_results(existing_results, new_results, latest_ts or 0, ids_at_latest_ts)
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved {len(merged)} total results to {SAVE_FILE}")
    else:
        print("No new results found to merge.")
    print("--- Fetch cycle complete ---")



while True:
    run_fetch_cycle()
    print(f"Sleeping for {SLEEP_INTERVAL_SECONDS / 60:.2f} minutes...")
    time.sleep(SLEEP_INTERVAL_SECONDS)