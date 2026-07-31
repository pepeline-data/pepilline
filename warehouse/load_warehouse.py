import os
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
CLEAN_FILE = os.path.join(PROJECT_ROOT, "clean", "aqi_clean.csv")


def load_clean_data():
    return pd.read_csv(CLEAN_FILE, parse_dates=["date_heure"])


def build_dim_city(df):
    cities = df[["ville", "pays", "latitude", "longitude"]].drop_duplicates()
    return cities.rename(columns={"ville": "name", "pays": "country"})


def build_dim_time(df):
    dt = df["date_heure"].dt.tz_localize(None)
    times = pd.DataFrame({"date": dt.dt.date, "hour": dt.dt.hour}).drop_duplicates()
    times["day_of_week"] = pd.to_datetime(times["date"]).dt.day_name()
    times["is_weekend"] = pd.to_datetime(times["date"]).dt.weekday >= 5
    times["month"] = pd.to_datetime(times["date"]).dt.month
    times["year"] = pd.to_datetime(times["date"]).dt.year
    return times


def load_warehouse():
    engine = create_engine(DATABASE_URL)
    df = load_clean_data()

    run_suffix = uuid.uuid4().hex[:8]
    staging_city = f"staging_city_{run_suffix}"
    staging_time = f"staging_time_{run_suffix}"
    staging_fact = f"staging_fact_{run_suffix}"

    # 1. dim_city
    dim_city_df = build_dim_city(df)
    dim_city_df.to_sql(staging_city, engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO dim_city (name, country, latitude, longitude)
            SELECT name, country, latitude, longitude FROM {staging_city}
            ON CONFLICT (name, country) DO NOTHING
        """))
        conn.execute(text(f"DROP TABLE {staging_city}"))
    print(f"dim_city : {len(dim_city_df)} villes traitées")

    # 2. dim_time
    dim_time_df = build_dim_time(df)
    dim_time_df.to_sql(staging_time, engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO dim_time (date, hour, day_of_week, is_weekend, month, year)
            SELECT date, hour, day_of_week, is_weekend, month, year FROM {staging_time}
            ON CONFLICT (date, hour) DO NOTHING
        """))
        conn.execute(text(f"DROP TABLE {staging_time}"))
    print(f"dim_time : {len(dim_time_df)} tranches horaires traitées")

    # 3. Mappings
    with engine.connect() as conn:
        city_map = pd.read_sql("SELECT id_city, name FROM dim_city", conn)
        time_map = pd.read_sql("SELECT id_time, date, hour FROM dim_time", conn)

    df["date"] = df["date_heure"].dt.tz_localize(None).dt.date
    df["hour"] = df["date_heure"].dt.tz_localize(None).dt.hour
    df = df.merge(city_map, left_on="ville", right_on="name")
    df = df.merge(time_map, on=["date", "hour"])

    pollutants = ["aqi", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]
    fact_df = df[["id_time", "id_city"] + pollutants]
    fact_df = fact_df.drop_duplicates(subset=["id_time", "id_city"], keep="last")

    # 4. fact_aqi
    fact_df.to_sql(staging_fact, engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO fact_aqi (id_time, id_city, {", ".join(pollutants)})
            SELECT id_time, id_city, {", ".join(pollutants)} FROM {staging_fact}
            ON CONFLICT (id_time, id_city) DO UPDATE SET
                {", ".join(f"{p} = EXCLUDED.{p}" for p in pollutants)}
        """))
        conn.execute(text(f"DROP TABLE {staging_fact}"))
    print(f"fact_aqi : {len(fact_df)} lignes chargées")


if __name__ == "__main__":
    load_warehouse()