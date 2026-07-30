import sys
import os
import time
import argparse
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(__file__))
from fetch_city import fetch_city_history

VILLES = [
    {"name": "Antananarivo", "lat": -18.8792, "lon": 47.5079},
    {"name": "New Delhi", "lat": 28.6139, "lon": 77.2090},
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
    {"name": "Reykjavik", "lat": 64.1466, "lon": -21.9426},
]

CHUNK_DAYS = 30
SLEEP_BETWEEN_CALLS = 1

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")


def build_chunks(months: int, now: datetime):
    """Découpe la période [now - months*30j, now] en tranches de CHUNK_DAYS jours."""
    total_days = months * 30
    chunks = []
    period_start = now - timedelta(days=total_days)

    cursor = period_start
    while cursor < now:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), now)
        chunks.append((int(cursor.timestamp()), int(chunk_end.timestamp())))
        cursor = chunk_end

    return chunks


def run_backfill(months: int = 12):
    now = datetime.now(timezone.utc)
    chunks = build_chunks(months, now)

    total = len(VILLES) * len(chunks)
    done = 0
    skipped = 0
    errors = 0

    print(
        f"Backfill : {len(VILLES)} villes x {len(chunks)} tranches de {CHUNK_DAYS}j "
        f"({total} appels max)"
    )

    for ville in VILLES:
        for start_ts, end_ts in chunks:
            try:
                filepath = fetch_city_history(
                    ville["name"], ville["lat"], ville["lon"],
                    start_ts, end_ts, raw_dir=RAW_DIR,
                )
                if filepath is None:
                    skipped += 1
                    print(f"  [skip] {ville['name']} {start_ts}-{end_ts} (déjà présent)")
                else:
                    done += 1
                    print(f"  [ok]   {ville['name']} {start_ts}-{end_ts} -> {filepath}")
                    time.sleep(SLEEP_BETWEEN_CALLS)
            except Exception as e:
                errors += 1
                print(f"  [ERREUR] {ville['name']} {start_ts}-{end_ts} : {e}")

    print(f"\nTerminé. {done} téléchargés, {skipped} déjà présents (skip), {errors} erreurs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill AQI 12 mois pour les 5 villes")
    parser.add_argument(
        "--months", type=int, default=12,
        help="Nombre de mois d'historique à récupérer (défaut : 12)",
    )
    args = parser.parse_args()

    run_backfill(months=args.months)