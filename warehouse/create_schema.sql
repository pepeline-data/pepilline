DROP TABLE IF EXISTS fact_aqi_measures;
DROP TABLE IF EXISTS dim_time;
DROP TABLE IF EXISTS dim_city;

CREATE TABLE dim_city (
    city_id     SERIAL PRIMARY KEY,
    city_name   VARCHAR(100)   NOT NULL,
    country     VARCHAR(100)   NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    UNIQUE (city_name, country)
);

CREATE TABLE dim_time (
    time_id       SERIAL PRIMARY KEY,
    full_datetime TIMESTAMP NOT NULL UNIQUE,
    date          DATE        NOT NULL,
    hour          SMALLINT    NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day           SMALLINT    NOT NULL,
    month         SMALLINT    NOT NULL,
    year          SMALLINT    NOT NULL,
    day_of_week   VARCHAR(10) NOT NULL,
    is_weekend    BOOLEAN     NOT NULL
);

CREATE TABLE fact_aqi_measures (
    fact_id     SERIAL PRIMARY KEY,
    city_id     INTEGER NOT NULL REFERENCES dim_city(city_id),
    time_id     INTEGER NOT NULL REFERENCES dim_time(time_id),

    aqi         SMALLINT,
    co          DOUBLE PRECISION,
    no          DOUBLE PRECISION,
    no2         DOUBLE PRECISION,
    o3          DOUBLE PRECISION,
    so2         DOUBLE PRECISION,
    pm2_5       DOUBLE PRECISION,
    pm10        DOUBLE PRECISION,
    nh3         DOUBLE PRECISION,

    UNIQUE (city_id, time_id)
);

CREATE INDEX idx_fact_city ON fact_aqi_measures(city_id);
CREATE INDEX idx_fact_time ON fact_aqi_measures(time_id);
CREATE INDEX idx_dim_time_date ON dim_time(date);
