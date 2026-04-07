from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import httpx
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process
import os, re, csv, asyncio, aiofiles, json
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
CAVE_CATEGORIES = ["vins-importes", "spiritueux-importes", "vins-locaux", "champagnes", "vins-effervescents"]
DATA_FILE = "data.json"

# ─── Stockage et Persistance ────────────────────────────────────────────────
state = {
    "fake_products": [],
    "corniche_images": [],
    "matches": [],
    "fake_scrape_status": "idle",
    "fake_scrape_count": 0,
    "scrape_status": "idle",
    "match_status": "idle"
}

def save_state():
    try:
        data = {
            "fake_products": state["fake_products"],
            "corniche_images": state["corniche_images"],
            "matches": state["matches"]
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")

def load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                state["fake_products"] = data.get("fake_products", [])
                state["corniche_images"] = data.get("corniche_images", [])
                state["matches"] = data.get("matches", [])
                state["fake_scrape_count"] = len(state["fake_products"])
                print(f"📦 Données chargées : {len(state['fake_products'])} fakes, {len(state['corniche_images'])} images")
        except Exception as e:
            print(f"Erreur lors du chargement : {e}")

# Charger l'état au démarrage
load_state()

# ─── Utilitaires ─────────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Normalise un nom produit : lowercase, sans accent, sans ponctuation, et sans mots 'bruit'."""
    if not name: return ""
    # Dé-accents
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower()
    # Remplacement ponctuation par espace
    name = re.sub(r"[^\w\s]", " ", name)
    
    # Suppression des mots parasites (noise/stopwords)
    noise = {
        "cl", "75cl", "37", "5cl", "375cl", "50cl", "1l", "70cl", "150cl", "magnum",
        "rouge", "blanc", "rose", "gris", "vin", "vins", "cru", "1er", "classe", "grand", "chateau",
        "de", "du", "le", "la", "les", "et", "un", "une", "des", "au", "aux", "pour", "caise", "caisse"
    }
    
    tokens = name.split()
    filtered = [t for t in tokens if t not in noise]
    
    return " ".join(filtered).strip()

def extract_year(name: str) -> str:
    """Extrait une année (4 chiffres consécutifs entre 1900 et 2030) d'une chaîne."""
    match = re.search(r"\b(19\d{2}|20[0-2]\d|2030)\b", name)
    return match.group(1) if match else None

def safe_filename(name: str, ext: str = ".jpg") -> str:
    """Transforme un nom produit en nom de fichier sûr."""
    n = unicodedata.normalize("NFD", name)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    n = re.sub(r"[^\w\s]", "", n)
    n = re.sub(r"\s+", "_", n)
    return f"{n}{ext}"

# ─── Endpoint 1 : Produits avec image fake ───────────────────────────────────

async def _scrape_fake_products_task():
    state["fake_scrape_status"] = "running"
    state["fake_scrape_count"] = 0
    fake_products = []
    seen_urls = set() # Pour éviter les doublons entre catégories
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        for cat_name in CAVE_CATEGORIES:
            page = 1
            while True:
                # URL structure: https://www.la-cave-privee.com/fr/{category}/products?page={page}
                url = f"{CAVE_BASE}/fr/{cat_name}/products?page={page}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break
                    soup = BeautifulSoup(resp.text, "lxml")
                    
                    # Sélecteurs basés sur l'HTML fourni par l'utilisateur
                    products = soup.select(".item")
                    if not products:
                        break
                    
                    # On évite les boucles infinies de pagination si le site renvoie toujours la même page
                    if page > 100: break 
                    
                    for p in products:
                        img_tag = p.select_one(".img_pdt img")
                        name_tag = p.select_one(".titre_pdt")
                        link_tag = p.select_one(".img_pdt a")
                        
                        if not img_tag or not name_tag:
                            continue
                        
                        product_name = name_tag.get_text(strip=True)
                        product_url = link_tag["href"] if link_tag else ""
                        
                        # Déduplication
                        if product_url in seen_urls:
                            continue
                        
                        # Déduction de la catégorie via l'URL (sm=...)
                        category = "unknown"
                        if "sm=" in product_url:
                            category = product_url.split("sm=")[-1].split("&")[0]
                        elif cat_name:
                            category = cat_name
                        
                        img_src = img_tag.get("src", "") or img_tag.get("data-src", "")
                        
                        # Extraction des images "fake"
                        # Le site semble utiliser : assets/img/no-image.gif
                        if "no-image.gif" in img_src:
                            fake_products.append({
                                "id": len(fake_products) + 1,
                                "name": product_name,
                                "category": category,
                                "url": product_url if product_url.startswith("http") else CAVE_BASE + product_url,
                                "fake_img_url": img_src if img_src.startswith("http") else CAVE_BASE + img_src,
                            })
                            seen_urls.add(product_url)
                            state["fake_scrape_count"] = len(fake_products)
                    
                    page += 1
                    await asyncio.sleep(0.3)  # politeness delay
                    
                except Exception as e:
                    print(f"Erreur catégorie {cat_name} page {page}: {e}")
                    break
    
    state["fake_products"] = fake_products
    state["fake_scrape_status"] = "done"
    save_state()
    print(f"✅ Détection terminée : {len(fake_products)} produits sans image identifiés")

@app.post("/api/fake-products")
async def start_fake_products_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(_scrape_fake_products_task)
    return {"status": "started"}

@app.get("/api/fake-products-status")
async def get_fake_products_status():
    return {
        "status": state["fake_scrape_status"],
        "count": state["fake_scrape_count"]
    }

@app.get("/api/fake-products-get")
async def get_fake_products():
    return state["fake_products"]


# ─── Endpoint 2 : Scraping Corniche ──────────────────────────────────────────

async def _download_image(client, url, dest_path):
    try:
        r = await client.get(url, timeout=10)
        if r.status_code == 200:
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(r.content)
            return True
    except Exception as e:
        print(f"Erreur téléchargement {url}: {e}")
    return False

async def _scrape_corniche_task():
    state["scrape_status"] = "running"
    corniche_images = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    base_url = "https://boissonlacorniche.com"
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        # On parcourt les pages de la boutique (pagination WooCommerce standard)
        for page_num in range(1, 40):
            try:
                if page_num == 1:
                    page_url = f"{base_url}/boutique/"
                else:
                    page_url = f"{base_url}/boutique/page/{page_num}/"
                    
                resp = await client.get(page_url)
                if resp.status_code != 200:
                    break
                    
                soup = BeautifulSoup(resp.text, "lxml")
                
                # WooCommerce Selectors
                products = soup.select("li.product")
                if not products:
                    break
                
                for prod in products:
                    name_tag = prod.select_one(".woocommerce-loop-product__title")
                    img_tag = prod.select_one("img")
                    
                    if not name_tag or not img_tag:
                        continue
                    
                    product_name = name_tag.get_text(strip=True)
                    # Supporte src (standard) et data-src (lazy load)
                    img_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src", "")
                    
                    # Ignorer les placeholders
                    if not img_url or "placeholder" in img_url or "no-image.gif" in img_url:
                        continue
                    
                    # Ensure absolute URL
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    elif img_url.startswith("/"):
                        img_url = base_url + img_url
                    elif not img_url.startswith("http"):
                        img_url = base_url + "/" + img_url
                    
                    # Déterminer l'extension
                    ext = Path(img_url.split("?")[0]).suffix or ".jpg"
                    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
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
                    
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"Erreur scraping Corniche page {page_num}: {e}")
                continue
    
    state["corniche_images"] = corniche_images
    state["scrape_status"] = "done"
    save_state()
    print(f"✅ Scraping Corniche terminé : {len(corniche_images)} images téléchargées")

@app.post("/api/scrape-corniche")
async def scrape_corniche(background_tasks: BackgroundTasks):
    background_tasks.add_task(_scrape_corniche_task)
    return {"status": "started"}

@app.get("/api/scrape-status")
async def get_scrape_status():
    return {
        "status": state["scrape_status"],
        "count": len(state["corniche_images"])
    }


# ─── Endpoint 3 : Matching ───────────────────────────────────────────────────

# Mots-clés identifiant les spiritueux
SPIRIT_TAGS = {"pastis", "vodka", "rhum", "whisky", "brandy", "calvados", "liqueur", "gin", "tequila", "cognac", "anise", "kentucky", "tennessee", "single malt"}

@app.get("/api/match")
async def match_products(threshold: int = 70):
    if not state["fake_products"]:
        return JSONResponse(status_code=400, content={"error": "Lance d'abord /api/fake-products"})
    if not state["corniche_images"]:
        return JSONResponse(status_code=400, content={"error": "Lance d'abord /api/scrape-corniche"})
    
    corniche_names_norm = [img["normalized_name"] for img in state["corniche_images"]]
    matches = []
    
    for product in state["fake_products"]:
        product_name = product["name"]
        product_cat = product.get("category", "")
        norm_cave = normalize_name(product_name)
        year_cave = extract_year(product_name)
        
        # Fuzzy matching
        result = process.extractOne(
            norm_cave,
            corniche_names_norm,
            scorer=fuzz.token_set_ratio, # Plus robuste que token_sort_ratio
            score_cutoff=threshold
        )
        
        best_match = None
        if result:
            matched_name_norm, score, idx = result
            corniche_img = state["corniche_images"][idx]
            match_name = corniche_img["product_name"]
            year_corniche = extract_year(match_name)
            
            # --- FILTRES DE SÉCURITÉ ---
            
            # 1. Filtre Année (Vintage)
            # Si Cave a une année mais pas Corniche -> Rejet (On ne matche pas un vin millésimé avec un spiritueux sans année)
            if year_cave and not year_corniche:
                score = 0
            # Si les deux ont des années différentes -> Rejet
            elif year_cave and year_corniche and year_cave != year_corniche:
                score = 0
            
            # 2. Filtre Catégorie / Spiritueux
            # Si le produit Cave est un vin mais que le match est un spiritueux (via mot-clé) -> Rejet
            is_cave_wine = "vin" in product_cat or "champagne" in product_cat
            is_match_spirit = any(tag in match_name.lower() for tag in SPIRIT_TAGS)
            
            if is_cave_wine and is_match_spirit:
                score = 0
            
            if score >= threshold:
                best_match = {
                    "cave_product_id": product["id"],
                    "cave_product_name": product_name,
                    "cave_fake_img": product["fake_img_url"],
                    "cave_product_url": product["url"],
                    "corniche_product_name": match_name,
                    "corniche_filename": corniche_img["filename"],
                    "corniche_local_url": f"/corniche_images/{corniche_img['filename']}",
                    "corniche_original_url": corniche_img["original_url"],
                    "match_score": round(score, 1),
                    "status": "matched",
                }
        
        if not best_match:
            best_match = {
                "cave_product_id": product["id"],
                "cave_product_name": product_name,
                "cave_fake_img": product["fake_img_url"],
                "cave_product_url": product["url"],
                "corniche_product_name": None,
                "corniche_filename": None,
                "corniche_local_url": None,
                "corniche_original_url": None,
                "match_score": 0,
                "status": "no_match",
            }
        
        matches.append(best_match)
    
    state["matches"] = matches
    save_state()
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
