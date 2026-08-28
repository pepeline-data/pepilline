
# ARCHITECTURE.md

## Pipeline de collecte et d'analyse de la qualité de l'air (AQI)

**Projet** : DONNEES2 — Data Engineering
**Équipe** : 5 membres
**Période couverte** : 12 mois (backfill) + collecte continue horaire

---

## 1. Résumé de l'architecture

Le pipeline a pour objectif de collecter automatiquement, à une fréquence horaire, les données de qualité de l'air (AQI) pour cinq villes réparties sur quatre continents. Ces données sont ensuite transformées en un format propre, cohérent et normalisé, avant d'être chargées dans un entrepôt de données (data warehouse) modélisé selon un schéma en étoile.

Ce système permet de produire un dataset fiable, directement exploitable dans le cadre du cours IA1.

┌─────────────────────────┐
│ OpenWeatherMap API │
│ Air Pollution │
└────────────┬────────────┘
│
│ Appel horaire (continu)
│ + Backfill (12 mois, one-shot)
▼
┌─────────────────────────────────────────────┐
│ Apache Airflow — DAG : dag_pipeline_complet │
│ Planification : @hourly │
│ │
│ ┌──────────────────┐ │
│ │ collect_aqi_data │ → Appel API (5 villes) │
│ └────────┬─────────┘ │
│ ▼ │
│ ┌──────────────────┐ │
│ │ build_clean_csv │ → Nettoyage & fusion │
│ └────────┬─────────┘ │
│ ▼ │
│ ┌──────────────────┐ │
│ │ load_warehouse │ → Chargement DB │
│ └────────┬─────────┘ │
└──────────┼────────────────────────────────────┘
▼
┌─────────────────────────────────────┐
│ Data Warehouse — PostgreSQL (Neon) │
│ Schéma en étoile │
│ dim_city · dim_time · fact_aqi │
└─────────────────────────────────────┘


---

## 2. Stack technique et justifications

| Composant | Choix | Justification |
|---|---|---|
| **Source de données** | OpenWeatherMap Air Pollution API | API gratuite fournissant un historique horaire exploitable via l'endpoint `/air_pollution/history`, avec une profondeur allant jusqu'à 12 mois, indispensable pour le backfill. |
| **Langage** | Python 3.14 | Écosystème riche (requests, pandas, SQLAlchemy), adapté à l'ingestion, au traitement et au chargement de données. Compatible avec Apache Airflow 3.x. |
| **Orchestrateur** | Apache Airflow 3.3.0 | Permet la planification, la supervision, la gestion des erreurs (retries) et fournit une interface claire pour la démonstration. |
| **Stockage brut (raw/)** | Fichiers JSON | Conservation des données brutes sans modification, servant de source de vérité. |
| **Stockage propre (clean/)** | CSV unique | Format simple, lisible et interopérable pour les analyses IA1. |
| **Entrepôt de données** | PostgreSQL (Neon) | Solution gratuite, accessible publiquement, compatible avec les contraintes du projet et les opérations d'upsert. |
| **Modélisation** | Schéma en étoile | Structure simple et efficace pour l'analyse (dimensions : temps et ville). |
| **Gestion des secrets** | Variables d'environnement (`.env`, jamais commité) | Sécurisation de la clé API et des identifiants de connexion à la base hors du dépôt Git. |

---

## 3. Décisions de conception

### 3.1 DAG unique et séquentiel

Le pipeline repose sur un seul DAG (`dag_pipeline_complet`) structuré en trois tâches enchaînées :

collect_aqi_data >> build_clean_csv >> load_warehouse


Ce choix garantit :
- un ordre d'exécution déterministe
- une meilleure lisibilité dans Airflow
- une démonstration simplifiée du pipeline complet

### 3.2 Déduplication à double niveau

La contrainte métier « une ville + une heure = une seule donnée » est assurée à deux niveaux :

- **Au niveau transformation** (`build_clean.py`) : suppression des doublons via `drop_duplicates` sur `(ville, date_heure)`
- **Au niveau base de données** (PostgreSQL) : contrainte `UNIQUE (id_time, id_city)` combinée à `ON CONFLICT DO UPDATE`

Cela garantit l'intégrité même en cas de rejouement du pipeline.

### 3.3 Isolation des exécutions (staging tables)

Lors des premiers tests, des conflits sont apparus lors d'exécutions simultanées du DAG. Solution adoptée : génération de noms uniques pour les tables temporaires via `uuid4`, isolant complètement chaque exécution, même en cas de parallélisme.

### 3.4 Séparation raw / clean

- **`raw/`** : données immuables (source de vérité)
- **`clean/`** : dataset reconstruit à chaque exécution

Cette approche garantit la reproductibilité totale, l'absence de corruption irréversible, et la possibilité de recalcul complet à tout moment.

---

## 4. Backfill

Le script `scripts/backfill.py` est exécuté manuellement (hors Airflow, en dehors du DAG horaire).

Caractéristiques :
- couvre 12 mois d'historique
- découpage en tranches de 30 jours (12 tranches par ville)
- respecte les limites de l'API
- rejouable sans duplication : une tranche déjà présente dans `raw/` est automatiquement sautée

Résultat : 60 fichiers d'historique générés (5 villes × 12 tranches), en plus des fichiers de collecte courante accumulés au fil des runs horaires.

---

## 5. Villes couvertes

| Ville | Pays | Latitude | Longitude |
|---|---|---|---|
| Antananarivo | Madagascar | -18.8792 | 47.5079 |
| New Delhi | Inde | 28.6139 | 77.2090 |
| Paris | France | 48.8566 | 2.3522 |
| Los Angeles | États-Unis | 34.0522 | -118.2437 |
| Reykjavik | Islande | 64.1466 | -21.9426 |

---

## 6. Structure du repository

pepilline/
├── raw/ # Données brutes (JSON, par ville et appel API)
├── clean/ # aqi_clean.csv (reconstruit à chaque exécution)
├── dags/ # dag_pipeline_complet.py
├── scripts/ # fetch_city.py, backfill.py, build_clean.py
├── warehouse/ # create_schema.sql, load_warehouse.py
├── notebooks/ # Prototype API (Colab) + notebook d'analyse IA1
├── README.md # Documentation générale et schéma
├── ARCHITECTURE.md # Ce document
├── RAPPORT.md # Méthode de travail, difficultés, résolutions
├── GUIDE_AIRFLOW.md # Guide d'installation et dépannage Airflow
├── GUIDE_METABASE.md # Guide d'installation et dépannage Metabase
└── SETUP.md # Guide d'installation (Windows / Linux)


---

## 7. Déploiement

Pendant le développement, Airflow tourne en mode `standalone` sur une machine
de développement du groupe, avec :
- `AIRFLOW_HOME` fixé dans `~/.bashrc` pour persister entre les sessions
- `dags_folder` pointant directement vers `dags/` du repo (pas de copie ni de
  lien symbolique, pour éviter les problèmes de résolution de chemin relatif
  dans le DAG)
- Le DAG `dag_pipeline_complet` activé et planifié `@hourly`

**Accès pour la vérification** : un tunnel ngrok expose temporairement
l'interface Airflow publiquement (voir README.md, section "Accès distant").
Cette solution est provisoire, adaptée à la démonstration immédiate, et
dépend de la disponibilité de la machine de développement. Pour une
continuité réelle après le rendu, le groupe prévoit de migrer vers un
hébergement permanent (VPS gratuit type Oracle Cloud Free Tier).

---

## 8. Limites connues

- **Airflow en mode `standalone`** : adapté à la démonstration et au
  développement, mais sans haute disponibilité ni redémarrage automatique en
  cas de crash du processus — à surveiller si hébergé sur une machine
  personnelle après le rendu.
- **Couverture du backfill** : ~360 jours au lieu de 365 (découpage en
  tranches de 30 jours), sans impact sur la qualité des données grâce à la
  déduplication stricte par (ville, date_heure).
- **Historique de runs automatiques** : le pipeline a été rendu pleinement
  autonome tardivement dans le développement du projet ; l'historique de runs
  disponible au moment du rendu peut ne pas couvrir 5 jours calendaires
  distincts (voir RAPPORT.md, section 7, pour le détail).
- **Accès distant temporaire (ngrok)** : le lien public dépend d'un tunnel
  actif sur la machine de développement du groupe ; le mot de passe généré
  pour l'accès Airflow change à chaque réinitialisation de la base metadata
  et doit être revérifié avant chaque démonstration (voir GUIDE_AIRFLOW.md).

