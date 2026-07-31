import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "warehouse"))

from fetch_city import fetch_city
from build_clean import build_clean
from load_warehouse import load_warehouse


VILLES = [
    {"name": "Antananarivo", "lat": -18.8792, "lon": 47.5079},
    {"name": "New Delhi",    "lat": 28.6139,  "lon": 77.2090},
    {"name": "Paris",        "lat": 48.8566,  "lon": 2.3522},
    {"name": "Los Angeles",  "lat": 34.0522,  "lon": -118.2437},
    {"name": "Reykjavik",    "lat": 64.1466,  "lon": -21.9426},
]


def collect_all_cities():
    for ville in VILLES:
        fetch_city(ville["name"], ville["lat"], ville["lon"])


default_args = {
    "owner": "chef_projet",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dag_pipeline_complet",
    description="Pipeline complet : collecte -> transform -> load warehouse",
    default_args=default_args,
    start_date=datetime(2026, 7, 1),
    schedule="@hourly",
    catchup=False,
    tags=["aqi", "pipeline"],
) as dag:

    collect_task = PythonOperator(
        task_id="collect_aqi_data",
        python_callable=collect_all_cities,
    )

    transform_task = PythonOperator(
        task_id="build_clean_csv",
        python_callable=build_clean,
    )

    load_task = PythonOperator(
        task_id="load_warehouse",
        python_callable=load_warehouse,
    )

    collect_task >> transform_task >> load_task