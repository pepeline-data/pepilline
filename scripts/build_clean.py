import os
import json
import glob
import pandas as pd
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "raw")
CLEAN_DIR = os.path.join(PROJECT_ROOT, "clean")
CLEAN_FILE = os.path.join(CLEAN_DIR, "aqi_clean.csv")

# Coordonnées de référence pour chaque ville (utilisées pour compléter les lignes)
VILLES_INFO = {
    "antananarivo": {"nom": "Antananarivo", "pays": "Madagascar", "lat": -18.8792, "lon": 47.5079},
    "new_delhi":    {"nom": "New Delhi",    "pays": "Inde",       "lat": 28.6139,  "lon": 77.2090},
    "paris":        {"nom": "Paris",        "pays": "France",     "lat": 48.8566,  "lon": 2.3522},
    "los_angeles":  {"nom": "Los Angeles",  "pays": "USA",        "lat": 34.0522,  "lon": -118.2437},
    "reykjavik":    {"nom": "Reykjavik",    "pays": "Islande",    "lat": 64.1466,  "lon": -21.9426},
}


def load_all_raw_files():
    rows = []
    json_files = glob.glob(os.path.join(RAW_DIR, "*", "*.json"))
    print(f"Fichiers raw trouvés : {len(json_files)}")

    for filepath in json_files:
        city_folder = os.path.basename(os.path.dirname(filepath))
        if city_folder not in VILLES_INFO:
            print(f"[SKIP] Dossier ville inconnu : {city_folder}")
            continue

        info = VILLES_INFO[city_folder]

        with open(filepath, "r") as f:
            data = json.load(f)

        for entry in data.get("list", []):
            row = {
                "ville": info["nom"],
                "pays": info["pays"],
                "latitude": info["lat"],
                "longitude": info["lon"],
                "date_heure": datetime.fromtimestamp(entry["dt"], tz=timezone.utc),
                "aqi": entry["main"]["aqi"],
                **entry["components"],
            }
            rows.append(row)

    return rows


def build_clean():
    rows = load_all_raw_files()
    if not rows:
        print("Aucune donnée trouvée dans raw/. Rien à faire.")
        return

    df = pd.DataFrame(rows)
    print(f"Total de lignes avant dédup : {len(df)}")

    # Déduplication : même ville + même heure = une seule ligne
    df = df.drop_duplicates(subset=["ville", "date_heure"], keep="last")
    print(f"Total de lignes après dédup : {len(df)}")

    # Tri chronologique par ville puis par date
    df = df.sort_values(by=["ville", "date_heure"]).reset_index(drop=True)

    os.makedirs(CLEAN_DIR, exist_ok=True)
    df.to_csv(CLEAN_FILE, index=False)
    print(f"Fichier clean écrit : {CLEAN_FILE}")
    print(df.groupby("ville").size())


if __name__ == "__main__":
    build_clean()