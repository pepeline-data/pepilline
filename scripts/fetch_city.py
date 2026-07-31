import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")

BASE_URL_CURRENT = "https://api.openweathermap.org/data/2.5/air_pollution"
BASE_URL_HISTORY = "https://api.openweathermap.org/data/2.5/air_pollution/history"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "raw")


def fetch_city(city_name, lat, lon, start=None, end=None, raw_dir=None):
    if raw_dir is None:
        raw_dir = DEFAULT_RAW_DIR

    city_folder = city_name.lower().replace(" ", "_")
    city_path = os.path.join(raw_dir, city_folder)
    os.makedirs(city_path, exist_ok=True)

    if start and end:
        # Historique : nom de fichier basé sur la tranche demandée (start/end),
        # PAS sur l'heure d'exécution -> stable d'un run à l'autre, permet de
        # détecter et sauter les tranches déjà téléchargées (anti-doublon).
        url = BASE_URL_HISTORY
        params = {"lat": lat, "lon": lon, "start": start, "end": end, "appid": API_KEY}
        filename = f"{city_folder}_history_{start}_{end}.json"
    else:
        # Pollution actuelle : le nom peut varier à chaque appel (chaque
        # snapshot est différent), on garde l'horodatage d'exécution ici.
        url = BASE_URL_CURRENT
        params = {"lat": lat, "lon": lon, "appid": API_KEY}
        timestamp_str = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        filename = f"{city_folder}_{timestamp_str}.json"

    filepath = os.path.join(city_path, filename)

    # Anti-doublon : si la tranche d'historique existe déjà, on ne rappelle pas l'API
    if start and end and os.path.exists(filepath):
        print(f"[skip] {city_name} {start}-{end} (déjà présent)")
        return None

    response = requests.get(url, params=params, timeout=15)
    if response.status_code != 200:
        print(f"[ERREUR] {city_name} : status {response.status_code} - {response.text}")
        return None

    data = response.json()

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[OK] {city_name} : {len(data.get('list', []))} entrées sauvegardées -> {filepath}")
    return filepath


if __name__ == "__main__":
    fetch_city("Antananarivo", -18.8792, 47.5079)