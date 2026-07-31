# Projet AQI — Pipeline de collecte de la qualité de l’air

---

## 1. Villes couvertes

| Ville        | Pays       | Latitude | Longitude |
| ------------ | ---------- | -------- | --------- |
| Antananarivo | Madagascar | -18.8792 | 47.5079   |
| New Delhi    | Inde       | 28.6139  | 77.2090   |
| Paris        | France     | 48.8566  | 2.3522    |
| Los Angeles  | États-Unis | 34.0522  | -118.2437 |
| Reykjavik    | Islande    | 64.1466  | -21.9426  |

---

## 2. Contrat de données — clean/aqi_clean.csv

Chaque ligne représente une mesure unique pour une ville donnée à une heure donnée.
Le fichier est trié chronologiquement par ville et ne contient aucun doublon.

* *Clé unique* : (ville, date_heure)
* *Génération* : fichier entièrement reconstruit à chaque exécution de scripts/build_clean.py

### Schéma des colonnes

| Colonne    | Description                | Format / Unité                                  |
| ---------- | -------------------------- | ----------------------------------------------- |
| ville      | Nom de la ville            | Texte                                           |
| pays       | Pays associé               | Texte                                           |
| latitude   | Coordonnée géographique    | Degrés décimaux                                 |
| longitude  | Coordonnée géographique    | Degrés décimaux                                 |
| date_heure | Horodatage de la mesure    | UTC — ISO (YYYY-MM-DD HH:MM:SS+00:00)         |
| aqi        | Indice de qualité de l’air | Échelle OpenWeather (1 = bon, 5 = très mauvais) |
| co         | Monoxyde de carbone        | µg/m³                                           |
| no         | Monoxyde d’azote           | µg/m³                                           |
| no2        | Dioxyde d’azote            | µg/m³                                           |
| o3         | Ozone                      | µg/m³                                           |
| so2        | Dioxyde de soufre          | µg/m³                                           |
| pm2_5      | Particules fines ≤ 2.5 µm  | µg/m³                                           |
| pm10       | Particules fines ≤ 10 µm   | µg/m³                                           |
| nh3        | Ammoniac                   | µg/m³                                           |

### Informations complémentaires

* *Source des données* : OpenWeatherMap Air Pollution API (/air_pollution, /air_pollution/history)
* *Période couverte* : ~12 mois (backfill) + collecte horaire continue
* *Particularité* : l’échelle AQI utilisée est celle d’OpenWeather (1 à 5), différente de l’échelle US (0 à 500)

### Limites connues

Le backfill étant découpé en tranches de 30 jours :

* couverture ≈ 360 jours au lieu de 365
* impact négligeable grâce à la déduplication stricte (ville, date_heure)

---

## 3. Structure du stockage

raw/{ville}/{ville}_{timestamp_appel}.json   # données brutes, immuables
clean/aqi_clean.csv                         # dataset consolidé, régénéré à chaque run

---

## 4. Schéma du Data Warehouse

Le modèle suit une architecture en *schéma en étoile* :

* 1 table de faits : fact_aqi
* 2 tables de dimensions : dim_time, dim_city

---

### 4.1 Table dim_city

| Colonne      | Type         | Description        |
| ------------ | ------------ | ------------------ |
| id_city (PK) | SERIAL       | Identifiant unique |
| name         | VARCHAR(100) | Nom de la ville    |
| country      | VARCHAR(100) | Pays               |
| latitude     | NUMERIC(9,6) | Latitude           |
| longitude    | NUMERIC(9,6) | Longitude          |

*Contrainte* :

UNIQUE (name, country)

---

### 4.2 Table dim_time

| Colonne      | Type        | Description        |
| ------------ | ----------- | ------------------ |
| id_time (PK) | SERIAL      | Identifiant unique |
| date         | DATE        | Date               |
| hour         | SMALLINT    | Heure (0–23)       |
| day_of_week  | VARCHAR(10) | Jour de la semaine |
| is_weekend   | BOOLEAN     | Indique week-end   |
| month        | SMALLINT    | Mois               |
| year         | SMALLINT    | Année              |

*Contrainte* :

UNIQUE (date, hour)

---

### 4.3 Table fact_aqi

| Colonne                                | Type          | Description          |
| -------------------------------------- | ------------- | -------------------- |
| id_fact (PK)                           | SERIAL        | Identifiant unique   |
| id_time (FK)                           | INTEGER       | Référence dim_time |
| id_city (FK)                           | INTEGER       | Référence dim_city |
| aqi                                    | SMALLINT      | Indice AQI           |
| co, no, no2, o3, so2, pm2_5, pm10, nh3 | NUMERIC(10,4) | Polluants            |

*Contrainte clé* :

UNIQUE (id_time, id_city)

Cette contrainte permet :

* l’**upsert**
* la prévention de toute duplication

---

### Cohérence des volumes

* ~8 500 tranches horaires
* × 5 villes
* ≈ *42 000 lignes* dans fact_aqi

L’écart avec la valeur théorique (~8 760 heures/an) s’explique par le découpage du backfill en tranches de 30 jours.

---

## 5. Chargement du Data Warehouse

Script rejouable sans duplication :

python warehouse/load_warehouse.py

Fonctionnement :

1. Lecture de clean/aqi_clean.csv
2. Alimentation des dimensions
3. Chargement de fact_aqi en *upsert*

---

## 6. Accès à la base de données

* *Fournisseur* : Neon (PostgreSQL managé)
* *Connexion* : via variable d’environnement DATABASE_URL (non versionnée)

Format :

postgresql://<user>:<password>@<host>/<dbname>?sslmode=require

Pour un accès en lecture (vérification), contacter le responsable du projet.

---

## 7. Orchestration

Le pipeline est orchestré avec Apache Airflow (dags/dag_pipeline_complet.py) :

* *Fréquence* : @hourly
* *Tâches* :

  1. collect_aqi_data → ingestion API → raw/
  2. build_clean_csv → transformation → clean/
  3. load_warehouse → chargement PostgreSQL

---

## 8. Backfill

Exécution manuelle :

python scripts/backfill.py

Caractéristiques :

* couvre 12 mois d’historique
* découpage en tranches de 30 jours
* génération de données dans raw/
* script entièrement rejouable

---