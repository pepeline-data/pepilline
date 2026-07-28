#!/usr/bin/env python3

import os
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

COLUMN_CITY_NAME = "city"
COLUMN_COUNTRY = "country"
COLUMN_LAT = "latitude"
COLUMN_LON = "longitude"
COLUMN_DATETIME = "datetime"

POLLUTANT_COLUMNS = ["aqi", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]

JOURS_FR = None


def get_engine():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("ERREUR : DATABASE_URL manquant. Copie .env.example en .env et remplis-le.")
    return create_engine(db_url)


def load_clean_csv():
    load_dotenv()
    csv_path = os.getenv("CLEAN_CSV_PATH", "clean/aqi_clean.csv")
    if not os.path.exists(csv_path):
        sys.exit(f"ERREUR : fichier introuvable : {csv_path}")

    df = pd.read_csv(csv_path)

    required = [COLUMN_CITY_NAME, COLUMN_COUNTRY, COLUMN_LAT, COLUMN_LON, COLUMN_DATETIME]
    missing = [c for c in required if c not in df.columns]
    if missing:
        sys.exit(
            f"ERREUR : colonnes attendues absentes du CSV : {missing}\n"
            f"Colonnes disponibles : {list(df.columns)}\n"
            "-> Adapte les constantes COLUMN_* en haut de ce script."
        )

    df[COLUMN_DATETIME] = pd.to_datetime(df[COLUMN_DATETIME])
    return df


def upsert_dim_city(engine, df):
    cities = df[[COLUMN_CITY_NAME, COLUMN_COUNTRY, COLUMN_LAT, COLUMN_LON]].drop_duplicates()

    with engine.begin() as conn:
        for _, row in cities.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO dim_city (city_name, country, latitude, longitude)
                    VALUES (:city_name, :country, :lat, :lon)
                    ON CONFLICT (city_name, country) DO NOTHING
                    """
                ),
                {
                    "city_name": row[COLUMN_CITY_NAME],
                    "country": row[COLUMN_COUNTRY],
                    "lat": row[COLUMN_LAT],
                    "lon": row[COLUMN_LON],
                },
            )
    print(f"dim_city : {len(cities)} villes traitées (insert si nouvelles).")


def upsert_dim_time(engine, df):
    timestamps = df[[COLUMN_DATETIME]].drop_duplicates()

    with engine.begin() as conn:
        for _, row in timestamps.iterrows():
            dt: datetime = row[COLUMN_DATETIME]
            conn.execute(
                text(
                    """
                    INSERT INTO dim_time
                        (full_datetime, date, hour, day, month, year, day_of_week, is_weekend)
                    VALUES
                        (:full_dt, :date, :hour, :day, :month, :year, :dow, :is_weekend)
                    ON CONFLICT (full_datetime) DO NOTHING
                    """
                ),
                {
                    "full_dt": dt,
                    "date": dt.date(),
                    "hour": dt.hour,
                    "day": dt.day,
                    "month": dt.month,
                    "year": dt.year,
                    "dow": dt.strftime("%A"),
                    "is_weekend": dt.weekday() >= 5,
                },
            )
    print(f"dim_time : {len(timestamps)} horodatages traités (insert si nouveaux).")


def upsert_facts(engine, df):
    present_pollutants = [c for c in POLLUTANT_COLUMNS if c in df.columns]
    if not present_pollutants:
        print("ATTENTION : aucune colonne de polluant reconnue dans le CSV.")

    with engine.begin() as conn:
        city_map = {
            (r["city_name"], r["country"]): r["city_id"]
            for r in conn.execute(text("SELECT city_id, city_name, country FROM dim_city")).mappings()
        }
        time_map = {
            r["full_datetime"]: r["time_id"]
            for r in conn.execute(text("SELECT time_id, full_datetime FROM dim_time")).mappings()
        }

        inserted = 0
        for _, row in df.iterrows():
            city_id = city_map.get((row[COLUMN_CITY_NAME], row[COLUMN_COUNTRY]))
            time_id = time_map.get(pd.Timestamp(row[COLUMN_DATETIME]).to_pydatetime())
            if city_id is None or time_id is None:
                continue

            values = {"city_id": city_id, "time_id": time_id}
            for col in present_pollutants:
                values[col] = row[col] if pd.notna(row[col]) else None

            cols = ", ".join(values.keys())
            placeholders = ", ".join(f":{k}" for k in values.keys())
            update_cols = ", ".join(f"{c} = EXCLUDED.{c}" for c in present_pollutants)

            conn.execute(
                text(
                    f"""
                    INSERT INTO fact_aqi_measures ({cols})
                    VALUES ({placeholders})
                    ON CONFLICT (city_id, time_id) DO UPDATE SET {update_cols}
                    """
                ),
                values,
            )
            inserted += 1

    print(f"fact_aqi_measures : {inserted} lignes insérées/mises à jour.")


def main():
    engine = get_engine()
    df = load_clean_csv()

    print(f"Lecture de clean/aqi_clean.csv : {len(df)} lignes, {df[COLUMN_CITY_NAME].nunique()} villes.")

    upsert_dim_city(engine, df)
    upsert_dim_time(engine, df)
    upsert_facts(engine, df)

    print("Chargement terminé.")


if __name__ == "__main__":
    main()
