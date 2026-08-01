# Rapport de projet — Pipeline AQI (DONNEES2)

## 1. Objectif du projet

Déployer un pipeline automatisé de collecte de données de qualité de l'air (AQI)
pour 5 villes (Antananarivo, New Delhi, Paris, Los Angeles, Reykjavik), avec
backfill historique et collecte horaire continue, transformation en un dataset
propre, et chargement dans un data warehouse modélisé en schéma en étoile.

## 2. Composition du groupe et répartition des tâches

| Membre | Rôle | Livrables |
|---|---|---|
| NJAKA | Chef de projet & Orchestration Airflow | Cadrage du projet, structure du repo, prototype Colab, DAG `dag_pipeline_complet.py`, déploiement Airflow |
| HIRAINA | Collecte & Backfill | `scripts/fetch_city.py`, `scripts/backfill.py`, backfill 12 mois sur les 5 villes |
| FRANCO | Transformation | `scripts/build_clean.py`, contrat de données `clean/aqi_clean.csv` |
| NEKENA | Data Warehouse | `warehouse/create_schema.sql`, `warehouse/load_warehouse.py`, base PostgreSQL sur Neon |
| ANDY | Documentation & preuves | `README.md`, `ARCHITECTURE.md`, coordination des captures et de la vidéo |

## 3. Méthode de travail

- **Gestion de version** : une branche par tâche (`feature/backfill-script`,
  `feature/warehouse-star-schema`, `feature/hourly-collection-dag`...), jamais
  de commit direct sur `main`, Pull Request + review avant merge.
- **Convention de commits** : `feat(scope): description`,
  `fix(scope): description`.
- **Point de synchro** : check-ins réguliers pour débloquer les dépendances
  entre tâches (ex. FRANCO dépendait des premières données de HIRAINA dans `raw/`
  pour commencer à tester `build_clean.py`).
- **Découpage du travail** : les tâches indépendantes (warehouse, documentation)
  ont démarré en parallèle de la collecte, pour ne pas bloquer sur le chemin
  critique collecte → transformation → chargement.

## 4. Architecture finale

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le détail complet. Résumé :

```
OpenWeatherMap Air Pollution API
        │  collecte horaire + backfill 12 mois
        ▼
Apache Airflow — DAG unique "dag_pipeline_complet" (@hourly)
  collect_aqi_data >> build_clean_csv >> load_warehouse
        ▼
raw/ (JSON bruts) → clean/aqi_clean.csv (CSV unique reconstruit)
        ▼
PostgreSQL (Neon) — schéma en étoile : dim_city, dim_time, fact_aqi
```

Choix notable : consolidation des 3 étapes du pipeline (collecte, transformation,
chargement) en **un seul DAG séquentiel** plutôt que 3 DAGs séparés, pour
simplifier l'orchestration, garantir un ordre d'exécution déterministe, et
faciliter la démonstration.

## 5. Difficultés rencontrées et résolutions

### 5.1 Environnement de développement

- **Venv créé au mauvais endroit / dans le mauvais dossier** : plusieurs clones
  du même repo ont coexisté sur la machine de développement à un moment
  (`update/projet/pepilline` vs `update/1/projetdonnee2/pepilline`), créant de
  la confusion sur quel dossier était réellement synchronisé avec GitHub.
  Résolu en identifiant le clone à jour via `git status` et en supprimant les
  doublons.
- **Interruption prématurée de `python3 -m venv`** : une interruption manuelle
  (Ctrl+C) pendant la création du venv laissait un environnement à moitié
  configuré (`.venv/bin/activate` absent). Résolu en laissant la commande
  s'exécuter jusqu'au bout sans interruption.

### 5.2 Configuration des secrets

- **`.gitignore` excluait `clean/` entièrement** : le fichier
  `clean/aqi_clean.csv`, pourtant un livrable obligatoire, n'était jamais
  suivi par git à cause d'une règle `.gitignore` trop large héritée de la
  structure initiale du repo. Corrigé en retirant `clean/` du `.gitignore`
  (seul `.env`, `.venv/`, `__pycache__/` etc. doivent rester ignorés) et en
  committant le fichier généré.
- **Format de connexion à la base de données** : Neon fournit une chaîne de
  connexion au format **JDBC**
  (`jdbc:postgresql://host/db?user=...&password=...&channelBinding=require`),
  incompatible telle quelle avec `psycopg2`/SQLAlchemy côté Python, qui
  attendent un format **URI standard**
  (`postgresql://user:password@host/db?sslmode=require`). Le paramètre
  `channelBinding`, spécifique au driver JDBC, faisait aussi planter
  `psycopg2` (`invalid connection option "channelBinding"`) — il a été retiré
  de l'URL, `sslmode=require` suffisant pour une connexion chiffrée.

### 5.3 Orchestration Airflow

- **`AIRFLOW_HOME` non persistant** : défini via `export` dans un terminal, la
  variable ne survivait pas à l'ouverture d'un nouveau terminal ni à un
  redémarrage de la machine, faisant retomber Airflow sur son dossier de
  configuration par défaut (`~/airflow`) au lieu de celui du projet — source de
  confusion (le DAG semblait "invisible" alors qu'Airflow tournait simplement
  avec une autre configuration). Résolu en ajoutant `AIRFLOW_HOME` de façon
  permanente dans `~/.bashrc`.
- **DAG introuvable dans l'interface malgré une détection correcte en CLI** :
  un lien symbolique du DAG vers le dossier `airflow/dags/` par défaut cassait
  la résolution de `os.path.dirname(__file__)` utilisée dans le DAG pour
  localiser `scripts/` (le chemin résolu pointait vers l'emplacement du lien,
  pas vers le fichier réel dans le repo), provoquant une erreur
  `ModuleNotFoundError: No module named 'fetch_city'`. Résolu en configurant
  directement `dags_folder` dans `airflow.cfg` pour pointer vers le dossier
  `dags/` du repo, sans passer par un lien symbolique.
- **DAG invisible dans la liste malgré une détection sans erreur en CLI** : la
  recherche par mot-clé partiel ("pipeline") dans l'interface, combinée à des
  filtres d'état non réinitialisés (ex. "Échoué" + "En pause" activés
  simultanément), masquait le DAG malgré sa présence confirmée par
  `airflow dags list`. Résolu en réinitialisant les filtres sur "Tous" et en
  recherchant le nom complet du DAG.

### 5.4 Dépendances Python

- Ajout tardif de `sqlalchemy` et `psycopg2-binary`, absents de l'installation
  initiale mais nécessaires à `warehouse/load_warehouse.py`.

## 6. Cohérence des données

À la date de rédaction : 42 176 lignes chargées dans `fact_aqi`, pour 5 villes
et 8 594 tranches horaires distinctes — cohérent avec un backfill de 12 mois
découpé en tranches de 30 jours (≈ 360 jours de couverture au lieu de 365,
sans impact grâce à la déduplication stricte sur la clé (ville, date_heure)).

## 7. Preuves de fonctionnement en continu

Le DAG `dag_pipeline_complet` a été activé le 1er août 2026 et s'exécute
automatiquement toutes les heures (`@hourly`) sans intervention manuelle,
enchaînant collecte → transformation → chargement à chaque run. Voir capture
d'écran jointe (historique des exécutions dans l'interface Airflow).

**Limite connue** : le pipeline a été rendu pleinement automatique
tardivement dans la fenêtre du projet, ce qui n'a pas permis d'accumuler des
runs sur 5 jours calendaires distincts comme idéalement souhaité. Les runs
disponibles couvrent néanmoins plusieurs heures consécutives de
fonctionnement autonome, démontrant la fiabilité du pipeline complet
(collecte, transformation, chargement) sans erreur.

## 8. Choix techniques justifiés

Voir [ARCHITECTURE.md](ARCHITECTURE.md), section 2, pour le tableau complet
des choix (API, langage, orchestrateur, stockage, warehouse, modélisation,
gestion des secrets) et leurs justifications.