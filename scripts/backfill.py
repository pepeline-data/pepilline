import sys
import os
import time
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(__file__))
from fetch_city import fetch_city

VILLES = [
    {"name": "Antananarivo", "lat": -18.8792, "lon": 47.5079},
    {"name": "New Delhi",    "lat": 28.6139,  "lon": 77.2090},
    {"name": "Paris",        "lat": 48.8566,  "lon": 2.3522},
    {"name": "Los Angeles",  "lat": 34.0522,  "lon": -118.2437},
    {"name": "Reykjavik",    "lat": 64.1466,  "lon": -21.9426},
]

MONTHS_BACK = 12


def generate_monthly_chunks(months_back):
    """Génère des tranches (start, end) en timestamp Unix, une par mois, du plus ancien au plus récent."""
    now = datetime.now(timezone.utc)
    chunks = []
    for i in range(months_back, 0, -1):
        end_dt = now - timedelta(days=(i - 1) * 30)
        start_dt = now - timedelta(days=i * 30)
        chunks.append((int(start_dt.timestamp()), int(end_dt.timestamp())))
    return chunks


def run_backfill():
    chunks = generate_monthly_chunks(MONTHS_BACK)
    total_calls = len(VILLES) * len(chunks)
    call_count = 0

    for ville in VILLES:
        for start, end in chunks:
            call_count += 1
            print(f"[{call_count}/{total_calls}] {ville['name']} : {datetime.fromtimestamp(start, tz=timezone.utc).date()} -> {datetime.fromtimestamp(end, tz=timezone.utc).date()}")
            fetch_city(ville["name"], ville["lat"], ville["lon"], start=start, end=end)
            time.sleep(1)  # petite pause pour ne pas saturer l'API


if __name__ == "__main__":

    run_backfill()
