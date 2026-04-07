# 🍷 Image Matcher

Application de matching automatique d'images produits entre **la-cave-privee.com** et **boissonlacorniche.com**.

## 🚀 Installation & Lancement

### 1. Backend (FastAPI)

Assurez-vous d'avoir Python 3.11+ installé.

```bash
# Se déplacer dans le dossier backend
cd backend

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn main:app --reload
```

Le serveur sera accessible sur `http://localhost:8000`.

### 2. Frontend (React)

Le frontend est une page HTML simple utilisant des CDNs. Il n'y a pas d'étape de build nécessaire.

Ouvrez simplement le fichier `frontend/index.html` dans votre navigateur.

## 🛠️ Utilisation

1.  **Charger les produits fake** : Scrape `la-cave-privee.com` pour trouver les produits sans image.
2.  **Scraper Corniche** : Scrape `boissonlacorniche.com` pour récupérer les images correspondantes.
3.  **Lancer le matching** : Aligne les produits des deux sites et affiche les résultats.
4.  **Exporter CSV** : Télécharge le résultat final au format CSV.
