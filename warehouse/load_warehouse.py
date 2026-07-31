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
                    INSERT INTO dim_city (name, country, latitude, longitude)
                    VALUES (:name, :country, :lat, :lon)
                    ON CONFLICT (name, country) DO NOTHING
                    """
                ),
                {
                    "name": row[COLUMN_CITY_NAME],
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
                        (date, hour, day_of_week, is_weekend, month, year)
                    VALUES
                        (:date, :hour, :dow, :is_weekend, :month, :year)
                    ON CONFLICT (date, hour) DO NOTHING
                    """
                ),
                {
                    "date": dt.date(),
                    "hour": dt.hour,
                    "dow": dt.strftime("%A"),
                    "is_weekend": dt.weekday() >= 5,
                    "month": dt.month,
                    "year": dt.year,
                },
            )
    print(f"dim_time : {len(timestamps)} horodatages traités (insert si nouveaux).")


def upsert_facts(engine, df):
    present_pollutants = [c for c in POLLUTANT_COLUMNS if c in df.columns]
    if not present_pollutants:
        print("ATTENTION : aucune colonne de polluant reconnue dans le CSV.")

    with engine.begin() as conn:
        city_map = {
            (r["name"], r["country"]): r["id_city"]
            for r in conn.execute(text("SELECT id_city, name, country FROM dim_city")).mappings()
        }
        time_map = {
            (r["date"], r["hour"]): r["id_time"]
            for r in conn.execute(text("SELECT id_time, date, hour FROM dim_time")).mappings()
        }

        inserted = 0
        for _, row in df.iterrows():
            city_id = city_map.get((row[COLUMN_CITY_NAME], row[COLUMN_COUNTRY]))
            dt = pd.Timestamp(row[COLUMN_DATETIME]).to_pydatetime()
            time_id = time_map.get((dt.date(), dt.hour))
            if city_id is None or time_id is None:
                continue

            values = {"id_city": city_id, "id_time": time_id}
            for col in present_pollutants:
                values[col] = row[col] if pd.notna(row[col]) else None

            cols = ", ".join(values.keys())
            placeholders = ", ".join(f":{k}" for k in values.keys())
            update_cols = ", ".join(f"{c} = EXCLUDED.{c}" for c in present_pollutants)

            conn.execute(
                text(
                    f"""
                    INSERT INTO fact_aqi ({cols})
                    VALUES ({placeholders})
                    ON CONFLICT (id_time, id_city) DO UPDATE SET {update_cols}
                    """
                ),
                values,
            )
            inserted += 1

    print(f"fact_aqi : {inserted} lignes insérées/mises à jour.")


def main():
    engine = get_engine()
    df = load_clean_csv()

    n_cities = df[COLUMN_CITY_NAME].nunique()
    print(f"Lecture de clean/aqi_clean.csv : {len(df)} lignes, {n_cities} villes.")

    upsert_dim_city(engine, df)
    upsert_dim_time(engine, df)
    upsert_facts(engine, df)

    print("Chargement terminé.")


if __name__ == "__main__":
    main()
