# 🍷 Image Matcher

Application SaaS de matching automatique d'images produits entre **la-cave-privee.com** et **boissonlacorniche.com** avec interface Luxury Dark.

## 🚀 Installation & Lancement

## 🖥️ Lancement rapide avec IMEG (CLI)

Un petit launcher est disponible à la racine pour démarrer le projet avec un menu CLI et une bannière ASCII "IMEG".

```bash
# Depuis la racine du projet
./imeg
```

Modes directs :

```bash
./imeg all       # backend + frontend
./imeg backend   # backend uniquement
./imeg frontend  # frontend uniquement
```

Option alternative :

```bash
python3 imeg.py
```

### 1. Backend (FastAPI)

Le backend gère le scraping, la persistance des données et l'algorithme de matching.

```bash
# Se déplacer dans le dossier backend
cd backend

# Créer l'environnement virtuel (une seule fois)
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn main:app --reload
```
Le serveur sera accessible sur `http://localhost:8000`.

### 2. Frontend (React + Vite)

L'interface utilisateur est construite avec React et Tailwind CSS.

```bash
# Se déplacer dans le dossier frontend
cd frontend

# Installer les dépendances
npm install

# Lancer l'application en mode développement
npm run dev
```
L'application sera accessible sur `http://localhost:5173`.

## 🛠️ Fonctionnement

1.  **Détection (Étape 01)** : Scrape les catégories de La Cave Privée pour identifier les produits sans image.
2.  **Scraping (Étape 02)** : Récupère la bibliothèque d'images réelles de Boisson La Corniche.
3.  **Matching (Étape 03)** : Aligne les produits via un algorithme de similarité textuelle avec validation stricte des années (millésimes).
4.  **Exportation** : Génère un rapport CSV prêt à l'emploi.

## 📂 Structure du projet
- `/backend` : API Python, scripts de scraping et stockage `data.json`.
- `/frontend` : Application React (Vite).
- `/corniche_images` : Stockage local des images téléchargées.
