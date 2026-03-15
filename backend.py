import requests
import time
import json
import os
from threading import Lock

# --- CONFIGURATION ---
APE_KEY = os.environ.get("MONKEYTYPE_APE_KEY")
BASE_URL = "https://api.monkeytype.com/results"
HEADERS = {"Authorization": f"ApeKey {APE_KEY}"}
SAVE_FILE = "data/monkeytype_results.json"
file_lock = Lock()

def run_fetch_cycle():
    """Fetches new results and merges them into the local JSON file."""
    if not APE_KEY:
        print("Error: MONKEYTYPE_APE_KEY not set.")
        return False

    # 1. Load Existing
    existing_results = []
    if os.path.exists(SAVE_FILE):
        with file_lock:
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    existing_results = json.load(f)
            except: pass

    # 2. Determine where to start fetching
    latest_ts = 0
    ids_at_latest = set()
    if existing_results:
        latest_ts = max(r.get("timestamp", 0) for r in existing_results)
        ids_at_latest = {r["_id"] for r in existing_results if r.get("timestamp") == latest_ts}

    # 3. Fetch from API
    all_new = []
    limit, offset = 1000, 0
    while True:
        params = {"limit": limit, "offset": offset, "onOrAfterTimestamp": latest_ts}
        try:
            response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data: break
            all_new.extend(data)
            if len(data) < limit: break
            offset += limit
            time.sleep(0.5)
        except Exception as e:
            print(f"Fetch error: {e}")
            break

    if not all_new:
        return False

    # 4. Merge and Deduplicate
    combined = {r["_id"]: r for r in existing_results}
    new_count = 0
    for r in all_new:
        _id = r.get("_id")
        ts = r.get("timestamp", 0)
        if ts == latest_ts and _id in ids_at_latest:
            continue
        if _id not in combined:
            new_count += 1
        combined[_id] = r

    if new_count > 0:
        sorted_data = sorted(combined.values(), key=lambda x: x.get("timestamp", 0))
        with file_lock:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(sorted_data, f, indent=2)
        print(f"Added {new_count} new records.")
        return True
    return False

if __name__ == "__main__":
    # Standard background loop logic
    UPDATES_PER_DAY = int(os.environ.get("UPDATES_PER_DAY", 1))
    SLEEP_SEC = (24 * 3600) / UPDATES_PER_DAY if UPDATES_PER_DAY > 0 else 3600
    while True:
        run_fetch_cycle()
        time.sleep(SLEEP_SEC)
