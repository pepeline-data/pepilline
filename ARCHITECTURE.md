# ARCHITECTURE.md

## Pipeline de collecte et d’analyse de la qualité de l’air (AQI)

*Projet* : PROJET2.0 — Data Engineering
*Équipe* : 5 membres
*Période couverte* : 12 mois (backfill) + collecte continue horaire

---

## 1. Résumé de l’architecture

Le pipeline a pour objectif de collecter automatiquement, à une fréquence horaire, les données de qualité de l’air (AQI) pour cinq villes réparties sur quatre continents. Ces données sont ensuite transformées en un format propre, cohérent et normalisé, avant d’être chargées dans un entrepôt de données (data warehouse) modélisé selon un schéma en étoile.

Ce système permet de produire un dataset fiable, directement exploitable dans le cadre du cours IA1.

┌─────────────────────────┐
│ OpenWeatherMap API      │
│ Air Pollution           │
└────────────┬────────────┘
             │
             │ Appel horaire (continu)
             │ + Backfill (12 mois, one-shot)
             ▼
┌─────────────────────────────────────────────┐
│ Apache Airflow — DAG : dag_pipeline_complet │
│ Planification : @hourly                     │
│                                             │
│ ┌──────────────────┐                        │
│ │ collect_aqi_data │ → Appel API (5 villes)│
│ └────────┬─────────┘                        │
│          ▼                                  │
│ ┌──────────────────┐                        │
│ │ build_clean_csv  │ → Nettoyage & fusion   │
│ └────────┬─────────┘                        │
│          ▼                                  │
│ ┌──────────────────┐                        │
│ │ load_warehouse   │ → Chargement DB        │
│ └────────┬─────────┘                        │
└──────────┼──────────────────────────────────┘
           ▼
┌─────────────────────────────────────┐
│ Data Warehouse — PostgreSQL (Neon)  │
│ Schéma en étoile                    │
│ dim_city · dim_time · fact_aqi      │
└─────────────────────────────────────┘

---

## 2. Stack technique et justifications

| Composant                    | Choix                            | Justification                                                                                                                                                                   |
| ---------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| *Source de données*        | OpenWeatherMap Air Pollution API | API gratuite fournissant un historique horaire exploitable via l’endpoint /air_pollution/history, avec une profondeur allant jusqu’à 12 mois, indispensable pour le backfill. |
| *Langage*                  | Python 3.12                      | Écosystème riche (requests, pandas, SQLAlchemy), adapté à l’ingestion, au traitement et au chargement de données. Compatible avec Apache Airflow 3.x.                           |
| *Orchestrateur*            | Apache Airflow 3.x               | Permet la planification, la supervision, la gestion des erreurs (retries) et fournit une interface claire pour la démonstration.                                                |
| *Stockage brut (raw/)*     | Fichiers JSON                    | Conservation des données brutes sans modification, servant de source de vérité.                                                                                                 |
| *Stockage propre (clean/)* | CSV unique                       | Format simple, lisible et interopérable pour les analyses IA1.                                                                                                                  |
| *Entrepôt de données*      | PostgreSQL (Neon)                | Solution gratuite, accessible publiquement, compatible avec les contraintes du projet et les opérations d’upsert.                                                               |
| *Modélisation*             | Schéma en étoile                 | Structure simple et efficace pour l’analyse (dimensions : temps et ville).                                                                                                      |
| *Gestion des secrets*      | Variables d’environnement (.env) | Sécurisation des identifiants et clés API hors du dépôt Git.                                                                                                                    |

---

## 3. Décisions de conception

### 3.1 DAG unique et séquentiel

Le pipeline repose sur un seul DAG (dag_pipeline_complet) structuré en trois tâches enchaînées :

collect_aqi_data >> build_clean_csv >> load_warehouse

Ce choix garantit :

* un ordre d’exécution déterministe
* une meilleure lisibilité dans Airflow
* une démonstration simplifiée du pipeline complet

---

### 3.2 Déduplication à double niveau

La contrainte métier « une ville + une heure = une seule donnée » est assurée à deux niveaux :

* *Au niveau transformation (build_clean.py)*
  Suppression des doublons via drop_duplicates sur (ville, date_heure)

* *Au niveau base de données (PostgreSQL)*
  Contrainte :

  
  UNIQUE (id_time, id_city)
  

  combinée à :

  
  ON CONFLICT DO UPDATE
  

Cela garantit l’intégrité même en cas de rejouement du pipeline.

---

### 3.3 Isolation des exécutions (staging tables)

Lors des premiers tests, des conflits sont apparus lors d’exécutions simultanées du DAG.

Solution adoptée :

* Génération de noms uniques pour les tables temporaires via uuid4
* Isolation complète de chaque exécution, même en cas de parallélisme

---

### 3.4 Séparation raw / clean

* *raw/* : données immuables (source de vérité)
* *clean/* : dataset reconstruit à chaque exécution

Cette approche garantit :

* la reproductibilité totale
* l’absence de corruption irréversible
* la possibilité de recalcul complet à tout moment

---

## 4. Backfill

Le script scripts/backfill.py est exécuté manuellement (hors Airflow).

Caractéristiques :

* couvre 12 mois d’historique
* découpage en tranches mensuelles (~30 jours)
* respecte les limites de l’API

Résultat :

* 60 fichiers générés
  (5 villes × 12 mois)
* stockage dans raw/

---

## 5. Villes couvertes

| Ville        | Pays       | Latitude | Longitude |
| ------------ | ---------- | -------- | --------- |
| Antananarivo | Madagascar | -18.8792 | 47.5079   |
| New Delhi    | Inde       | 28.6139  | 77.2090   |
| Paris        | France     | 48.8566  | 2.3522    |
| Los Angeles  | États-Unis | 34.0522  | -118.2437 |
| Reykjavik    | Islande    | 64.1466  | -21.9426  |

---

## 6. Structure du repository

donnee2/
├── raw/              # Données brutes (JSON, par ville et appel API)
├── clean/            # aqi_clean.csv (reconstruit à chaque exécution)
├── dags/             # dag_pipeline_complet.py
├── scripts/          # fetch_city.py, backfill.py, build_clean.py
├── warehouse/        # create_schema.sql, load_warehouse.py
├── notebooks/        # Exploration et tests API
├── README.md         # Documentation générale et schéma
├── ARCHITECTURE.md   # Ce document
└── SETUP.md          # Guide d’installation (Windows / Linux)