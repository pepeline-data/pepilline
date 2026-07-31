DROP TABLE IF EXISTS fact_aqi;
DROP TABLE IF EXISTS dim_time;
DROP TABLE IF EXISTS dim_city;

CREATE TABLE dim_city (
    id_city     SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    latitude    NUMERIC(9,6) NOT NULL,
    longitude   NUMERIC(9,6) NOT NULL,
    UNIQUE (name, country)
);

CREATE TABLE dim_time (
    id_time         SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_of_week     VARCHAR(10) NOT NULL,   -- e.g. 'Monday'
    is_weekend      BOOLEAN NOT NULL,
    month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    year            SMALLINT NOT NULL,
    UNIQUE (date, hour)
);

CREATE TABLE fact_aqi (
    id_fact     SERIAL PRIMARY KEY,
    id_time     INTEGER NOT NULL REFERENCES dim_time(id_time),
    id_city     INTEGER NOT NULL REFERENCES dim_city(id_city),
    aqi         SMALLINT,
    co          NUMERIC(10,4),
    no          NUMERIC(10,4),
    no2         NUMERIC(10,4),
    o3          NUMERIC(10,4),
    so2         NUMERIC(10,4),
    pm2_5       NUMERIC(10,4),
    pm10        NUMERIC(10,4),
    nh3         NUMERIC(10,4),
    UNIQUE (id_time, id_city)
);

CREATE INDEX idx_fact_aqi_city ON fact_aqi(id_city);
CREATE INDEX idx_fact_aqi_time ON fact_aqi(id_time);
CREATE INDEX idx_dim_time_date ON dim_time(date);