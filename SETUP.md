# SETUP.md — Installation & premiers pas

Ce document explique comment préparer votre environnement pour travailler sur le projet, quel que soit votre OS.

## 1. Cloner le repo

```bash
git clone <url-du-repo>
cd donnee2
```

## 2. Créer et activer l'environnement virtuel Python

### Linux (Ubuntu/Kubuntu/Debian)

```bash
# Vérifier que Python est installé
python3 --version

# Installer les outils nécessaires si besoin
sudo apt update
sudo apt install python3-full python3-venv python3-pip

# Créer le venv
python3 -m venv .venv

# Vérifier que pip est bien présent dedans
ls .venv/bin/

# Activer le venv (à refaire à chaque nouveau terminal)
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
# Vérifier que Python est installé
python --version
# Si erreur : installer Python depuis python.org
# Important : cocher "Add Python to PATH" pendant l'installation

# Créer le venv
python -m venv .venv

# Vérifier que pip est bien présent dedans
dir .venv\Scripts

# Activer le venv (à refaire à chaque nouveau terminal)
.venv\Scripts\Activate.ps1

# Si erreur "l'exécution de scripts est désactivée" :
# Ouvrir PowerShell en Administrateur et lancer :
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Puis refaire l'activation
```

Le terminal doit afficher `(.venv)` devant votre prompt une fois activé.

## 3. Installer les librairies du projet

```bash
pip install --timeout 60 requests pandas python-dotenv apache-airflow
```

Vérifier :
```bash
pip list
```

## 4. Configurer la clé API

Créer un fichier `.env` à la racine du projet (jamais commité) :

```
OPENWEATHER_API_KEY=votre_cle_ici
```

La clé vous est communiquée en message privé par le chef de projet — jamais dans le repo, jamais dans un canal public.

**Avant tout commit**, vérifier que `.env` n'apparaît pas :
```bash
git status
```
S'il apparaît, ne pas commit — vérifier le `.gitignore`.

## 5. Convention de travail Git

- Une branche par tâche : `feature/nom-de-la-tache`
- Jamais de commit direct sur `master`/`main`
- Message de commit : `feat(scope): description` (ex: `feat(collecte): script backfill 12 mois`)
- Pull Request + review par un autre membre avant de merger

## 6. Règles à respecter

- `raw/` : jamais d'édition manuelle, uniquement en écriture via les scripts
- `clean/` : reconstruit à chaque run, jamais édité à la main
- Ne jamais committer `.venv/` ni `.env`

## 7. Structure du projet

```
donnee2/
├── .env                    # clé API (jamais commité)
├── .gitignore
├── README.md
├── ARCHITECTURE.md
├── raw/                     # fichiers bruts par ville
├── clean/                   # CSV unique reconstruit
├── dags/                    # DAGs Airflow
├── warehouse/                # schéma SQL + script de chargement
├── scripts/                  # fetch_city.py, build_clean.py
└── notebooks/                 # prototypes Colab
```

## 8. En cas de blocage

Contacter le chef de groupe avant de committer quoi que ce soit de douteux (clé API visible, doublons dans raw/, etc.). Mieux vaut demander que de devoir nettoyer l'historique Git après coup.