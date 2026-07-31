import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

BASE_URL_CURRENT = "http://api.openweathermap.org/data/2.5/air_pollution"
BASE_URL_HISTORY = "http://api.openweathermap.org/data/2.5/air_pollution/history"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "raw")


def fetch_city(city_name, lat, lon, start=None, end=None, raw_dir=None):
    if raw_dir is None:
        raw_dir = DEFAULT_RAW_DIR    
    if start and end:
        url = BASE_URL_HISTORY
        params = {"lat": lat, "lon": lon, "start": start, "end": end, "appid": API_KEY}
    else:
        url = BASE_URL_CURRENT
        params = {"lat": lat, "lon": lon, "appid": API_KEY}

    response = requests.get(url, params=params, timeout=15)

    if response.status_code != 200:
        print(f"[ERREUR] {city_name} : status {response.status_code} - {response.text}")
        return None

    data = response.json()

    city_folder = city_name.lower().replace(" ", "_")
    city_path = os.path.join(raw_dir, city_folder)
    os.makedirs(city_path, exist_ok=True)

    timestamp_str = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    filename = f"{city_folder}_{timestamp_str}.json"
    filepath = os.path.join(city_path, filename)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[OK] {city_name} : {len(data.get('list', []))} entrées sauvegardées -> {filepath}")
    return filepath


if __name__ == "__main__":
    fetch_city("Antananarivo", -18.8792, 47.5079)