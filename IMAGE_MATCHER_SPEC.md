# 🍷 Image Matcher — Spec Technique Complète
> Application de matching automatique d'images produits entre **la-cave-privee.com** et **boissonlacorniche.com**

---

## 🎯 Objectif

Identifier les produits de `la-cave-privee.com` qui ont une **image fake** (`no-image.gif`), les matcher avec les images correspondantes trouvées sur `boissonlacorniche.com` via correspondance de nom de produit, afficher les paires côte-à-côte, et exporter le résultat en CSV.

---

## 🏗️ Architecture

```
image-matcher/
├── backend/
│   ├── main.py                  # FastAPI app + tous les endpoints
│   ├── scraper.py               # Logique de scraping (cave + corniche)
│   ├── matcher.py               # Algorithme de matching par nom
│   ├── requirements.txt
│   └── corniche_images/         # Dossier images téléchargées (auto-créé)
│       └── [nom_produit.ext]
├── frontend/
│   └── index.html               # React via CDN + Tailwind CDN
└── README.md
```

---

## ⚙️ Stack Technique

| Couche     | Technologie                          |
|------------|--------------------------------------|
| Backend    | Python 3.11+, FastAPI, Uvicorn       |
| Scraping   | httpx, BeautifulSoup4, Playwright (optionnel) |
| Matching   | rapidfuzz (fuzzy string matching)    |
| Frontend   | React 18 (CDN), Babel (CDN), Tailwind CSS v4 (CDN) |
| Export     | csv (stdlib Python)                  |
| CORS       | fastapi-cors middleware              |

---

## 📦 `requirements.txt`

```txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
httpx==0.27.0
beautifulsoup4==4.12.3
lxml==5.2.1
rapidfuzz==3.9.3
python-multipart==0.0.9
aiofiles==23.2.1
Pillow==10.3.0
```

---

## 🔵 Backend — `backend/main.py`

### Endpoints

| Méthode | Route                        | Description                                          |
|---------|------------------------------|------------------------------------------------------|
| `GET`   | `/api/fake-products`         | Liste des produits avec image fake sur la-cave-privee |
| `POST`  | `/api/scrape-corniche`       | Lance le scraping de boissonlacorniche.com + télécharge images |
| `GET`   | `/api/match`                 | Lance l'algo de matching nom → image                 |
| `GET`   | `/api/results`               | Retourne les paires matchées avec scores             |
| `GET`   | `/api/export-csv`            | Télécharge le CSV des résultats                      |
| `GET`   | `/corniche_images/{filename}`| Sert les images locales téléchargées                 |

---

### Implémentation complète — `backend/main.py`

```python
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import httpx
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process
import os, re, csv, asyncio, aiofiles
from pathlib import Path
import unicodedata

app = FastAPI(title="Image Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

IMAGES_DIR = Path("corniche_images")
IMAGES_DIR.mkdir(exist_ok=True)
app.mount("/corniche_images", StaticFiles(directory=str(IMAGES_DIR)), name="corniche_images")

FAKE_IMAGE_URL = "https://www.la-cave-privee.com/assets/img/no-image.gif"
CAVE_BASE = "https://www.la-cave-privee.com"

# ─── Stockage en mémoire (remplace DB pour ce projet) ───────────────────────
state = {
    "fake_products": [],       # [{id, name, url, fake_img_url}]
    "corniche_images": [],     # [{filename, product_name, local_path, url}]
    "matches": [],             # [{cave_product, corniche_image, score}]
    "scrape_status": "idle",   # idle | running | done | error
}

# ─── Utilitaires ─────────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Normalise un nom produit pour le matching : lowercase, sans accent, sans ponctuation."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def safe_filename(name: str, ext: str = ".jpg") -> str:
    """Transforme un nom produit en nom de fichier sûr."""
    name = normalize_name(name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w_]", "", name)
    return f"{name}{ext}"

# ─── Endpoint 1 : Produits avec image fake ───────────────────────────────────

@app.get("/api/fake-products")
async def get_fake_products():
    """
    Scrape la-cave-privee.com et retourne les produits avec no-image.gif
    Adapte le sélecteur CSS selon la structure réelle du site.
    """
    fake_products = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ImageMatcher/1.0)"}
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        page = 1
        while True:
            # ⚠️ Adapte l'URL de pagination à ton site
            url = f"{CAVE_BASE}/produits?page={page}"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "lxml")
                
                # ⚠️ Adapte ces sélecteurs à la structure HTML de la-cave-privee.com
                products = soup.select(".product-item, .product-card, article.product")
                if not products:
                    break
                
                for p in products:
                    img_tag = p.select_one("img")
                    name_tag = p.select_one(".product-name, .product-title, h2, h3")
                    link_tag = p.select_one("a[href]")
                    
                    if not img_tag or not name_tag:
                        continue
                    
                    img_src = img_tag.get("src", "") or img_tag.get("data-src", "")
                    
                    if "no-image.gif" in img_src or img_src == FAKE_IMAGE_URL:
                        fake_products.append({
                            "id": len(fake_products) + 1,
                            "name": name_tag.get_text(strip=True),
                            "url": CAVE_BASE + link_tag["href"] if link_tag else "",
                            "fake_img_url": FAKE_IMAGE_URL,
                        })
                
                page += 1
                await asyncio.sleep(0.5)  # politeness delay
                
            except Exception as e:
                print(f"Erreur page {page}: {e}")
                break
    
    state["fake_products"] = fake_products
    return {"count": len(fake_products), "products": fake_products}


# ─── Endpoint 2 : Scraping Corniche ──────────────────────────────────────────

CORNICHE_IMAGE_PATHS = [
    "https://boissonlacorniche.com/wp-content/uploads/2023/",
    "https://boissonlacorniche.com/wp-content/uploads/2025/",
    "https://boissonlacorniche.com/wp-content/uploads/2026/",
]

async def _download_image(client: httpx.AsyncClient, img_url: str, dest_path: Path) -> bool:
    try:
        r = await client.get(img_url, timeout=20)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(r.content)
            return True
    except Exception as e:
        print(f"Erreur téléchargement {img_url}: {e}")
    return False

async def _scrape_corniche_task():
    state["scrape_status"] = "running"
    corniche_images = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ImageMatcher/1.0)"}
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        # Méthode 1 : Parcourir les pages catalogue de boissonlacorniche.com
        base_url = "https://boissonlacorniche.com"
        
        # Scrape les pages produits du site
        for page_num in range(1, 20):  # max 20 pages
            try:
                page_url = f"{base_url}/shop/page/{page_num}/" if page_num > 1 else f"{base_url}/shop/"
                resp = await client.get(page_url)
                if resp.status_code == 404:
                    break
                    
                soup = BeautifulSoup(resp.text, "lxml")
                
                # WooCommerce produits
                products = soup.select(".product, .wc-block-grid__product, li.product")
                if not products and page_num > 1:
                    break
                
                for prod in products:
                    name_tag = prod.select_one(".woocommerce-loop-product__title, h2.woocommerce-loop-product__title, .product-title, h2, h3")
                    img_tag = prod.select_one("img.wp-post-image, img.attachment-woocommerce_thumbnail, img")
                    
                    if not name_tag or not img_tag:
                        continue
                    
                    product_name = name_tag.get_text(strip=True)
                    img_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src", "")
                    
                    if not img_url or "placeholder" in img_url:
                        continue
                    
                    # Déterminer l'extension
                    ext = Path(img_url.split("?")[0]).suffix or ".jpg"
                    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                        ext = ".jpg"
                    
                    filename = safe_filename(product_name, ext)
                    dest_path = IMAGES_DIR / filename
                    
                    # Télécharger si pas déjà présent
                    if not dest_path.exists():
                        success = await _download_image(client, img_url, dest_path)
                        if not success:
                            continue
                    
                    corniche_images.append({
                        "filename": filename,
                        "product_name": product_name,
                        "normalized_name": normalize_name(product_name),
                        "local_path": str(dest_path),
                        "original_url": img_url,
                    })
                    
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Erreur scraping page {page_num}: {e}")
                continue
    
    state["corniche_images"] = corniche_images
    state["scrape_status"] = "done"
    print(f"✅ Scraping terminé : {len(corniche_images)} images téléchargées")

@app.post("/api/scrape-corniche")
async def scrape_corniche(background_tasks: BackgroundTasks):
    if state["scrape_status"] == "running":
        return {"status": "already_running"}
    background_tasks.add_task(_scrape_corniche_task)
    return {"status": "started"}

@app.get("/api/scrape-status")
async def scrape_status():
    return {
        "status": state["scrape_status"],
        "images_count": len(state["corniche_images"]),
    }


# ─── Endpoint 3 : Matching ───────────────────────────────────────────────────

@app.get("/api/match")
async def match_products(threshold: int = 60):
    """
    Match les produits fake avec les images corniche via fuzzy matching.
    threshold : score minimum de similarité (0-100), défaut 60.
    """
    if not state["fake_products"]:
        return JSONResponse(status_code=400, content={"error": "Lance d'abord /api/fake-products"})
    if not state["corniche_images"]:
        return JSONResponse(status_code=400, content={"error": "Lance d'abord /api/scrape-corniche"})
    
    corniche_names = [img["normalized_name"] for img in state["corniche_images"]]
    matches = []
    
    for product in state["fake_products"]:
        norm_cave = normalize_name(product["name"])
        
        # Fuzzy matching avec rapidfuzz
        result = process.extractOne(
            norm_cave,
            corniche_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold
        )
        
        if result:
            matched_name, score, idx = result
            corniche_img = state["corniche_images"][idx]
            matches.append({
                "cave_product_id": product["id"],
                "cave_product_name": product["name"],
                "cave_fake_img": product["fake_img_url"],
                "cave_product_url": product["url"],
                "corniche_product_name": corniche_img["product_name"],
                "corniche_filename": corniche_img["filename"],
                "corniche_local_url": f"/corniche_images/{corniche_img['filename']}",
                "corniche_original_url": corniche_img["original_url"],
                "match_score": round(score, 1),
                "status": "matched",
            })
        else:
            matches.append({
                "cave_product_id": product["id"],
                "cave_product_name": product["name"],
                "cave_fake_img": product["fake_img_url"],
                "cave_product_url": product["url"],
                "corniche_product_name": None,
                "corniche_filename": None,
                "corniche_local_url": None,
                "corniche_original_url": None,
                "match_score": 0,
                "status": "no_match",
            })
    
    state["matches"] = matches
    matched_count = sum(1 for m in matches if m["status"] == "matched")
    
    return {
        "total": len(matches),
        "matched": matched_count,
        "unmatched": len(matches) - matched_count,
        "matches": matches,
    }


# ─── Endpoint 4 : Export CSV ─────────────────────────────────────────────────

@app.get("/api/export-csv")
async def export_csv():
    if not state["matches"]:
        return JSONResponse(status_code=400, content={"error": "Lance d'abord /api/match"})
    
    csv_path = Path("export_image_matches.csv")
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "ID Produit Cave",
            "Nom Produit (la-cave-privee)",
            "URL Produit Cave",
            "Statut",
            "Score Matching (%)",
            "Nom Produit Corniche",
            "Fichier Image Local",
            "URL Image Corniche (originale)",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for m in state["matches"]:
            writer.writerow({
                "ID Produit Cave": m["cave_product_id"],
                "Nom Produit (la-cave-privee)": m["cave_product_name"],
                "URL Produit Cave": m["cave_product_url"],
                "Statut": "✅ Matché" if m["status"] == "matched" else "❌ Non trouvé",
                "Score Matching (%)": m["match_score"] if m["match_score"] else "",
                "Nom Produit Corniche": m["corniche_product_name"] or "",
                "Fichier Image Local": m["corniche_filename"] or "",
                "URL Image Corniche (originale)": m["corniche_original_url"] or "",
            })
    
    return FileResponse(
        path=str(csv_path),
        media_type="text/csv",
        filename="image_matches.csv",
    )
```

---

### `backend/scraper.py` (module auxiliaire optionnel)

```python
"""
Module optionnel : si le site la-cave-privee.com nécessite du JavaScript
pour afficher ses produits, utilise Playwright ici.
"""
# pip install playwright && playwright install chromium

# from playwright.async_api import async_playwright
# async def scrape_with_js(url):
#     async with async_playwright() as p:
#         browser = await p.chromium.launch()
#         page = await browser.new_page()
#         await page.goto(url, wait_until="networkidle")
#         content = await page.content()
#         await browser.close()
#         return content
```

---

## 🔴 Frontend — `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>🍷 Image Matcher</title>
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
  <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen">

<div id="root"></div>

<script type="text/babel">
const { useState, useEffect, useCallback } = React;

const API = "http://localhost:8000";

// ── Composants UI ──────────────────────────────────────────────────────────

const Badge = ({ children, color }) => {
  const colors = {
    green:  "bg-green-900 text-green-300 border border-green-700",
    red:    "bg-red-900 text-red-300 border border-red-700",
    yellow: "bg-yellow-900 text-yellow-300 border border-yellow-700",
    gray:   "bg-gray-800 text-gray-400 border border-gray-600",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[color] || colors.gray}`}>
      {children}
    </span>
  );
};

const Stat = ({ label, value, sub }) => (
  <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 text-center">
    <div className="text-3xl font-bold text-white">{value}</div>
    <div className="text-sm text-gray-400 mt-1">{label}</div>
    {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
  </div>
);

const ImageBox = ({ src, label, fallback, tag }) => {
  const [error, setError] = useState(false);
  return (
    <div className="flex flex-col items-center gap-2 flex-1">
      <div className="text-xs text-gray-500 uppercase tracking-widest">{label}</div>
      <div className="w-full aspect-square bg-gray-800 rounded-lg overflow-hidden flex items-center justify-center border border-gray-700 relative group">
        {!error && src ? (
          <img
            src={src}
            alt={label}
            className="object-contain w-full h-full p-2"
            onError={() => setError(true)}
          />
        ) : (
          <div className="text-gray-600 text-center p-4">
            <div className="text-3xl mb-2">🚫</div>
            <div className="text-xs">{fallback || "Image indisponible"}</div>
          </div>
        )}
        {tag && (
          <div className="absolute top-2 left-2">
            <Badge color={tag.color}>{tag.label}</Badge>
          </div>
        )}
      </div>
    </div>
  );
};

const MatchCard = ({ match, index }) => {
  const isMatched = match.status === "matched";
  const scoreColor = match.match_score >= 80 ? "green" : match.match_score >= 60 ? "yellow" : "red";

  return (
    <div className={`bg-gray-900 rounded-xl border p-4 ${isMatched ? "border-gray-700" : "border-gray-800"}`}>
      <div className="flex items-start justify-between mb-3 gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-white truncate" title={match.cave_product_name}>
            {match.cave_product_name}
          </div>
          {match.cave_product_url && (
            <a href={match.cave_product_url} target="_blank" rel="noopener"
               className="text-xs text-blue-400 hover:underline truncate block">
              Voir le produit →
            </a>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <Badge color={isMatched ? "green" : "red"}>
            {isMatched ? "✅ Matché" : "❌ Non trouvé"}
          </Badge>
          {isMatched && (
            <Badge color={scoreColor}>{match.match_score}% similaire</Badge>
          )}
        </div>
      </div>

      <div className="flex gap-3">
        {/* Image fake actuelle */}
        <ImageBox
          src={match.cave_fake_img}
          label="Image actuelle (fake)"
          fallback="no-image.gif"
          tag={{ label: "FAKE", color: "red" }}
        />

        {/* Flèche */}
        <div className="flex items-center text-gray-600 flex-shrink-0 pt-6">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </div>

        {/* Image corniche */}
        <ImageBox
          src={isMatched ? `${API}${match.corniche_local_url}` : null}
          label={isMatched ? match.corniche_product_name : "Aucune correspondance"}
          fallback="Aucune image trouvée"
          tag={isMatched ? { label: "CORNICHE", color: "green" } : null}
        />
      </div>
    </div>
  );
};

// ── App principale ─────────────────────────────────────────────────────────

export default function App() {
  const [step, setStep] = useState("idle"); // idle | loading_fake | loading_corniche | matching | done
  const [fakeProducts, setFakeProducts] = useState([]);
  const [scrapeStatus, setScrapeStatus] = useState("idle");
  const [matches, setMatches] = useState([]);
  const [stats, setStats] = useState(null);
  const [threshold, setThreshold] = useState(60);
  const [filter, setFilter] = useState("all"); // all | matched | unmatched
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);

  // Polling scrape status
  useEffect(() => {
    if (scrapeStatus !== "running") return;
    const interval = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/scrape-status`);
        const data = await r.json();
        setScrapeStatus(data.status);
        if (data.status === "done") {
          clearInterval(interval);
          setStep("ready_to_match");
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [scrapeStatus]);

  const handleLoadFakeProducts = async () => {
    setStep("loading_fake");
    setError(null);
    try {
      const r = await fetch(`${API}/api/fake-products`);
      const data = await r.json();
      setFakeProducts(data.products);
      setStep("fake_loaded");
    } catch (e) {
      setError("Erreur lors du chargement des produits fake. Le backend est-il lancé ?");
      setStep("idle");
    }
  };

  const handleScrapeCorniche = async () => {
    setError(null);
    try {
      await fetch(`${API}/api/scrape-corniche`, { method: "POST" });
      setScrapeStatus("running");
    } catch (e) {
      setError("Erreur lors du lancement du scraping.");
    }
  };

  const handleMatch = async () => {
    setStep("matching");
    setError(null);
    try {
      const r = await fetch(`${API}/api/match?threshold=${threshold}`);
      const data = await r.json();
      setMatches(data.matches);
      setStats({ total: data.total, matched: data.matched, unmatched: data.unmatched });
      setStep("done");
    } catch (e) {
      setError("Erreur lors du matching.");
      setStep("ready_to_match");
    }
  };

  const handleExportCSV = () => {
    window.open(`${API}/api/export-csv`, "_blank");
  };

  const filteredMatches = matches.filter(m => {
    if (filter === "matched" && m.status !== "matched") return false;
    if (filter === "unmatched" && m.status !== "no_match") return false;
    if (search && !m.cave_product_name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-1">🍷 Image Matcher</h1>
        <p className="text-gray-400 text-sm">
          Relier les produits avec image fake de <span className="text-blue-400">la-cave-privee.com</span> aux images de{" "}
          <span className="text-green-400">boissonlacorniche.com</span>
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 bg-red-900/40 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Étapes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* Étape 1 */}
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">1️⃣</span>
            <span className="font-semibold">Charger les produits fake</span>
          </div>
          <p className="text-gray-400 text-xs mb-4">
            Scrape <code className="bg-gray-800 px-1 rounded">la-cave-privee.com</code> et identifie tous les produits avec <code className="bg-gray-800 px-1 rounded">no-image.gif</code>
          </p>
          <button
            onClick={handleLoadFakeProducts}
            disabled={step === "loading_fake"}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
          >
            {step === "loading_fake" ? "⏳ Chargement..." : `🔍 Charger les produits${fakeProducts.length ? ` (${fakeProducts.length})` : ""}`}
          </button>
        </div>

        {/* Étape 2 */}
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">2️⃣</span>
            <span className="font-semibold">Scraper Corniche</span>
          </div>
          <p className="text-gray-400 text-xs mb-4">
            Parcourt <code className="bg-gray-800 px-1 rounded">boissonlacorniche.com</code>, télécharge toutes les images dans <code className="bg-gray-800 px-1 rounded">corniche_images/</code>
          </p>
          <button
            onClick={handleScrapeCorniche}
            disabled={scrapeStatus === "running"}
            className="w-full bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
          >
            {scrapeStatus === "running"
              ? "⏳ Scraping en cours..."
              : scrapeStatus === "done"
              ? "✅ Scraping terminé"
              : "📸 Lancer le scraping"}
          </button>
          {scrapeStatus === "running" && (
            <p className="text-yellow-400 text-xs mt-2 text-center animate-pulse">
              Téléchargement des images en arrière-plan…
            </p>
          )}
        </div>

        {/* Étape 3 */}
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">3️⃣</span>
            <span className="font-semibold">Lancer le matching</span>
          </div>
          <div className="mb-3">
            <label className="text-xs text-gray-400 block mb-1">
              Seuil de similarité : <span className="text-white font-bold">{threshold}%</span>
            </label>
            <input
              type="range" min="40" max="95" value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              className="w-full accent-purple-500"
            />
          </div>
          <button
            onClick={handleMatch}
            disabled={step === "matching" || fakeProducts.length === 0 || scrapeStatus !== "done"}
            className="w-full bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
          >
            {step === "matching" ? "⏳ Matching..." : "🔗 Relier les produits"}
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Stat label="Produits fake" value={fakeProducts.length} />
          <Stat label="Matchés" value={stats.matched} sub={`${Math.round(stats.matched/stats.total*100)}%`} />
          <Stat label="Non trouvés" value={stats.unmatched} />
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex items-center justify-center">
            <button
              onClick={handleExportCSV}
              className="bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors w-full"
            >
              📥 Exporter CSV
            </button>
          </div>
        </div>
      )}

      {/* Filtres */}
      {matches.length > 0 && (
        <div className="flex flex-wrap gap-3 mb-6 items-center">
          <div className="flex gap-2">
            {["all", "matched", "unmatched"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === f
                    ? "bg-white text-gray-900"
                    : "bg-gray-800 text-gray-400 hover:text-white"
                }`}
              >
                {f === "all" ? "Tous" : f === "matched" ? "✅ Matchés" : "❌ Non trouvés"}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="🔍 Rechercher un produit..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 flex-1 min-w-48 focus:outline-none focus:border-blue-500"
          />
          <span className="text-gray-500 text-sm">{filteredMatches.length} résultat(s)</span>
        </div>
      )}

      {/* Grille de résultats */}
      {filteredMatches.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredMatches.map((match, i) => (
            <MatchCard key={match.cave_product_id} match={match} index={i} />
          ))}
        </div>
      ) : matches.length > 0 ? (
        <div className="text-center py-16 text-gray-600">
          <div className="text-4xl mb-3">🔍</div>
          <div>Aucun résultat pour ce filtre</div>
        </div>
      ) : step !== "done" && (
        <div className="text-center py-16 text-gray-700">
          <div className="text-5xl mb-4">🍷</div>
          <div className="text-lg">Suis les étapes ci-dessus pour commencer</div>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
</script>
</body>
</html>
```

---

## 🚀 Installation & Lancement

### Prérequis
- Python 3.11+
- Node.js non requis (tout en CDN)

### Setup

```bash
# 1. Créer le projet
mkdir image-matcher && cd image-matcher
mkdir backend frontend

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt

# 3. Lancer FastAPI
uvicorn main:app --reload --port 8000
```

### Ouvrir le frontend

```bash
# Option simple : ouvrir index.html dans le navigateur
# Option serveur local (recommandé pour éviter les CORS) :
cd frontend
python -m http.server 3000
# puis ouvrir http://localhost:3000
```

---

## 📋 Flux d'utilisation

```
1. Ouvrir http://localhost:3000 (frontend)
2. Cliquer "Charger les produits fake"
   → Backend scrape la-cave-privee.com, filtre no-image.gif
3. Cliquer "Lancer le scraping Corniche"
   → Backend parcourt boissonlacorniche.com
   → Télécharge images dans corniche_images/
   → Renomme chaque image avec le nom du produit
4. Ajuster le seuil de similarité (60% par défaut)
5. Cliquer "Relier les produits"
   → Fuzzy matching par nom
   → Affiche paires côte-à-côte
6. Filtrer / rechercher dans les résultats
7. Cliquer "Exporter CSV" → download image_matches.csv
```

---

## ⚠️ Points d'attention (adaptation nécessaire)

### Sélecteurs CSS à adapter

Le scraper utilise des sélecteurs CSS génériques. Si le site ne retourne pas de résultats :

```python
# Dans main.py — endpoint /api/fake-products
# Inspecte la page avec F12 → DevTools → Inspecter les produits

# Exemple possible pour la-cave-privee.com :
products = soup.select(".product-item")          # ou ".card", ".item", etc.
name_tag = p.select_one(".product-name")         # ou "h2", ".title", etc.
img_tag = p.select_one("img.product-image")      # ou "img[data-src]", etc.
```

### Pagination

```python
# Adapte l'URL selon le système de pagination du site :
url = f"{CAVE_BASE}/produits?page={page}"        # query param
url = f"{CAVE_BASE}/produits/page/{page}/"       # WooCommerce-style
url = f"{CAVE_BASE}/catalogue/{page}"            # slug-style
```

### Sites avec JavaScript (SPA)

Si les produits sont chargés via JS, utilise Playwright :

```bash
pip install playwright
playwright install chromium
```

Puis décommente le module `scraper.py`.

---

## 📊 Format du CSV exporté

| ID Produit Cave | Nom Produit (la-cave-privee) | URL Produit Cave | Statut | Score Matching (%) | Nom Produit Corniche | Fichier Image Local | URL Image Corniche (originale) |
|---|---|---|---|---|---|---|---|
| 1 | Château Margaux 2018 | https://... | ✅ Matché | 92.5 | Chateau Margaux 2018 | chateau_margaux_2018.jpg | https://boissonlacorniche.com/... |
| 2 | Moët & Chandon Brut | https://... | ❌ Non trouvé | | | | |

---

## 🔧 Améliorations futures

- [ ] Matching manuel dans l'UI (drag & drop ou dropdown)
- [ ] Prévisualisation de l'image avant confirmation
- [ ] Upload direct vers la-cave-privee.com via leur API/FTP
- [ ] Persistance SQLite pour sauvegarder les matchs entre sessions
- [ ] Support multi-threads pour scraping plus rapide
- [ ] Export JSON en plus du CSV
