"""
fetch_city.py

Fonctions de base pour interroger l'API OpenWeatherMap Air Pollution
et sauvegarder les réponses brutes (JSON) dans raw/<ville>/.
"""

import os
import re
import json
import unicodedata
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")

BASE_URL_CURRENT = "https://api.openweathermap.org/data/2.5/air_pollution"
BASE_URL_HISTORY = "https://api.openweathermap.org/data/2.5/air_pollution/history"


def slugify(city_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", city_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _ensure_dir(raw_dir: str, city_slug: str) -> str:
    city_dir = os.path.join(raw_dir, city_slug)
    os.makedirs(city_dir, exist_ok=True)
    return city_dir


def _check_api_key():
    if not API_KEY:
        raise RuntimeError(
            "OPENWEATHER_API_KEY manquant. Vérifiez votre fichier .env "
            "(voir README.md / consigne 1)."
        )


def fetch_city(city_name: str, lat: float, lon: float, raw_dir: str = "raw") -> str:
    """Récupère la pollution ACTUELLE d'une ville et sauvegarde le JSON brut."""
    _check_api_key()
    city_slug = slugify(city_name)
    city_dir = _ensure_dir(raw_dir, city_slug)

    params = {"lat": lat, "lon": lon, "appid": API_KEY}
    response = requests.get(BASE_URL_CURRENT, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    filename = f"{city_slug}_{ts}.json"
    filepath = os.path.join(city_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def fetch_city_history(
    city_name: str,
    lat: float,
    lon: float,
    start_ts: int,
    end_ts: int,
    raw_dir: str = "raw",
) -> str:
    """
    Récupère l'historique de pollution d'une ville entre start_ts et end_ts
    (timestamps Unix en secondes) et sauvegarde le JSON brut.

    Retourne None si le fichier existe déjà (pour permettre de rejouer le
    backfill sans dupliquer les données déjà téléchargées).
    """
    _check_api_key()
    city_slug = slugify(city_name)
    city_dir = _ensure_dir(raw_dir, city_slug)

    filename = f"{city_slug}_history_{start_ts}_{end_ts}.json"
    filepath = os.path.join(city_dir, filename)

    if os.path.exists(filepath):
        return None

    params = {
        "lat": lat,
        "lon": lon,
        "start": start_ts,
        "end": end_ts,
        "appid": API_KEY,
    }
    response = requests.get(BASE_URL_HISTORY, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath