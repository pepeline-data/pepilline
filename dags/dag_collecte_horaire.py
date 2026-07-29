import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

# Permet d'importer fetch_city.py depuis dags/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fetch_city import fetch_city




# Les 5 villes du projet   
VILLES = [
    {"name": "Antananarivo", "lat": -18.8792, "lon": 47.5079},
    {"name": "New Delhi",    "lat": 28.6139,  "lon": 77.2090},
    {"name": "Paris",        "lat": 48.8566,  "lon": 2.3522},
    {"name": "Los Angeles",  "lat": 34.0522,  "lon": -118.2437},
    {"name": "Reykjavik",    "lat": 64.1466,  "lon": -21.9426},
]

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")


def collect_all_cities():
    for ville in VILLES:
        fetch_city(ville["name"], ville["lat"], ville["lon"], raw_dir=RAW_DIR)


default_args = {
    "owner": "chef_projet",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dag_collecte_horaire",
    description="Collecte horaire AQI pour les 5 villes",
    default_args=default_args,
    start_date=datetime(2026, 7, 1),
    schedule="@hourly",
    catchup=False,
    tags=["aqi", "collecte"],
) as dag:

    collecte_task = PythonOperator(
        task_id="collecter_toutes_les_villes",
        python_callable=collect_all_cities,
    )