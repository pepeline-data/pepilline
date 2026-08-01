cat > ARCHITECTURE.md << 'MDEOF'
# ARCHITECTURE.md

## Pipeline de collecte et d'analyse de la qualité de l'air (AQI)

**Projet** : DONNEES2 — Data Engineering
**Équipe** : 5 membres
**Période couverte** : 12 mois (backfill) + collecte continue horaire

---

## 1. Résumé de l'architecture

Le pipeline a pour objectif de collecter automatiquement, à une fréquence horaire, les données de qualité de l'air (AQI) pour cinq villes réparties sur quatre continents. Ces données sont ensuite transformées en un format propre, cohérent et normalisé, avant d'être chargées dans un entrepôt de données (data warehouse) modélisé selon un schéma en étoile.

Ce système permet de produire un dataset fiable, directement exploitable dans le cadre du cours IA1.
