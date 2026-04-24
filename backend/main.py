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
import time
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs, urlencode, urlunparse
import zipfile

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
FAKE_SCRAPE_CONCURRENCY = 12
MULTISITE_DEFAULT_MIN_RAW_SCORE = 25
MULTISITE_DEFAULT_MAX_RESULTS_PER_SITE = 8
MULTISITE_DEFAULT_MAX_PRODUCT_CONCURRENCY = 30
MULTISITE_DEFAULT_MAX_HTTP_CONCURRENCY = 220
MULTISITE_DEFAULT_MAX_SITE_QUERY_CONCURRENCY = 30
DATA_FILE = "data.json"

# ─── Stockage et Persistance ────────────────────────────────────────────────
state = {
    "fake_products": [],
    "corniche_images": [],
    "matches": [],
    "fake_scrape_status": "idle",
    "fake_scrape_count": 0,
    "fake_scrape_errors": [],
    "fake_scrape_run_id": None,
    "scrape_status": "idle",
    "match_status": "idle",
    "multi_site": {
        "status": "idle",
        "run_id": None,
        "started_at": None,
        "finished_at": None,
        "progress": {
            "total_products": 0,
            "processed_products": 0,
            "with_candidates": 0,
            "early_stopped": 0,
        },
        "options": {},
        "site_errors": {},
        "results": [],
    }
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
    run_id = f"fake-{int(time.time())}"
    state["fake_scrape_run_id"] = run_id
    state["fake_scrape_status"] = "running"
    state["fake_scrape_count"] = 0
    state["fake_scrape_errors"] = []
    fake_products = []
    seen_urls = set() # Pour éviter les doublons entre catégories
    state_lock = asyncio.Lock()
    category_sem = asyncio.Semaphore(FAKE_SCRAPE_CONCURRENCY)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    def _pick_first(node, selectors):
        for sel in selectors:
            found = node.select_one(sel)
            if found:
                return found
        return None

    def _normalize_product_url(raw_href: str) -> str:
        if not raw_href:
            return ""
        full = raw_href if raw_href.startswith("http") else urljoin(CAVE_BASE, raw_href)
        parsed = urlparse(full)
        if parsed.netloc and "la-cave-privee.com" not in parsed.netloc:
            return ""
        return urlunparse((
            parsed.scheme or "https",
            parsed.netloc or urlparse(CAVE_BASE).netloc,
            parsed.path.rstrip("/") or parsed.path or "/",
            "",
            "",
            "",
        ))

    def _normalize_listing_url(raw_href: str, current_url: str) -> str:
        if not raw_href:
            return ""
        full = raw_href if raw_href.startswith("http") else urljoin(current_url, raw_href)
        parsed = urlparse(full)
        if parsed.netloc and "la-cave-privee.com" not in parsed.netloc:
            return ""
        query = parse_qs(parsed.query)
        filtered_query = {}
        if query.get("page"):
            filtered_query["page"] = [query["page"][0]]
        return urlunparse((
            parsed.scheme or "https",
            parsed.netloc or urlparse(CAVE_BASE).netloc,
            parsed.path,
            "",
            urlencode(filtered_query, doseq=True),
            "",
        ))

    def _extract_category_slug_from_url(raw_href: str) -> str:
        if not raw_href:
            return ""
        full = raw_href if raw_href.startswith("http") else urljoin(CAVE_BASE, raw_href)
        parsed = urlparse(full)
        if parsed.netloc and "la-cave-privee.com" not in parsed.netloc:
            return ""
        segments = [seg for seg in parsed.path.split("/") if seg]
        if "products" not in segments:
            return ""
        product_idx = segments.index("products")
        if product_idx <= 0:
            return ""
        slug = segments[product_idx - 1]
        if slug in {"fr", "en", "products"}:
            return ""
        if not re.match(r"^[a-z0-9-]+$", slug):
            return ""
        return slug

    def _extract_next_page_url(soup: BeautifulSoup, current_url: str, current_page: int) -> str:
        next_link_selectors = [
            "a[rel='next']",
            ".pagination a.next",
            ".pagination .next a",
            "li.next a",
            "a[aria-label*='Next']",
            "a[aria-label*='Suivant']",
            "a[title*='Next']",
            "a[title*='Suivant']",
            "a:-soup-contains('Suivant')",
            "a:-soup-contains('Next')",
        ]
        for selector in next_link_selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            href = node.get("href", "")
            candidate = _normalize_listing_url(href, current_url)
            if candidate:
                return candidate

        expected_next = current_page + 1
        for node in soup.select("a[href]"):
            label = node.get_text(" ", strip=True)
            if label.isdigit() and int(label) == expected_next:
                href = node.get("href", "")
                candidate = _normalize_listing_url(href, current_url)
                if candidate:
                    return candidate

        parsed = urlparse(current_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(expected_next)]
        return urlunparse((
            parsed.scheme or "https",
            parsed.netloc or urlparse(CAVE_BASE).netloc,
            parsed.path,
            "",
            urlencode(query, doseq=True),
            "",
        ))

    async def _discover_cave_categories(client: httpx.AsyncClient):
        discovered = set(CAVE_CATEGORIES)
        discovery_sources = [f"{CAVE_BASE}/sitemap.xml", f"{CAVE_BASE}/fr/", CAVE_BASE]

        for source_url in discovery_sources:
            try:
                async with category_sem:
                    resp = await client.get(source_url)
                if resp.status_code != 200:
                    continue
                parser = "xml" if source_url.endswith(".xml") else "lxml"
                soup = BeautifulSoup(resp.text, parser)
                if parser == "xml":
                    raw_links = [loc.get_text(strip=True) for loc in soup.select("loc")]
                else:
                    raw_links = [a.get("href", "") for a in soup.select("a[href]")]
                for href in raw_links:
                    slug = _extract_category_slug_from_url(href)
                    if slug:
                        discovered.add(slug)
            except Exception as e:
                async with state_lock:
                    state["fake_scrape_errors"].append(f"category_discovery {source_url}: {e}")

        return sorted(discovered)

    async def scrape_one_category(client: httpx.AsyncClient, cat_name: str):
        async def get_with_retry(url: str, retries: int = 3):
            last_err = None
            for attempt in range(1, retries + 1):
                try:
                    async with category_sem:
                        resp = await client.get(url)
                    # Retry transient HTTP statuses often seen with anti-bot or temporary overload.
                    if resp.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                        await asyncio.sleep(0.4 * attempt)
                        continue
                    return resp
                except Exception as e:
                    last_err = e
                    if attempt < retries:
                        await asyncio.sleep(0.4 * attempt)
                        continue
            raise last_err if last_err else RuntimeError(f"Echec requête {url}")

        page = 1
        pages_scanned = 0
        max_pages = 250
        next_page_url = f"{CAVE_BASE}/fr/{cat_name}/products?page=1"
        visited_page_urls = set()
        seen_page_signatures = set()

        while next_page_url and pages_scanned < max_pages:
            url = _normalize_listing_url(next_page_url, next_page_url)
            if not url or url in visited_page_urls:
                break
            visited_page_urls.add(url)

            try:
                resp = await get_with_retry(url)

                if resp.status_code != 200:
                    async with state_lock:
                        state["fake_scrape_errors"].append(f"{cat_name} page {page}: HTTP {resp.status_code}")
                    break

                soup = BeautifulSoup(resp.text, "lxml")

                # Sélecteurs basés sur l'HTML fourni par l'utilisateur
                products = soup.select(".item")
                if not products:
                    products = soup.select("article.product, li.product, .product-item")
                if not products:
                    break

                signature_tokens = []

                for p in products:
                    img_tag = _pick_first(p, [".img_pdt img", "img"])
                    name_tag = _pick_first(p, [".titre_pdt", ".product-name", "h2", "h3", "a[title]", "a"])
                    link_tag = _pick_first(p, [".img_pdt a", "a[href]"])

                    if not name_tag:
                        continue

                    product_name = name_tag.get_text(strip=True)
                    raw_product_url = link_tag.get("href", "") if link_tag else ""
                    full_product_url = _normalize_product_url(raw_product_url)
                    if full_product_url:
                        signature_tokens.append(f"{product_name}|{full_product_url}")

                    if not img_tag:
                        continue

                    img_src = img_tag.get("src", "") or img_tag.get("data-src", "")

                    # Extraction des images "fake"
                    # Le site semble utiliser : assets/img/no-image.gif
                    if "no-image.gif" not in img_src:
                        continue

                    if not full_product_url:
                        continue

                    full_fake_img_url = img_src if img_src.startswith("http") else CAVE_BASE + img_src

                    async with state_lock:
                        # Déduplication partagée entre catégories concurrentes
                        if full_product_url in seen_urls:
                            continue
                        seen_urls.add(full_product_url)

                        fake_products.append({
                            "id": len(fake_products) + 1,
                            "name": product_name,
                            "category": cat_name,
                            "url": full_product_url,
                            "fake_img_url": full_fake_img_url,
                        })
                        state["fake_scrape_count"] = len(fake_products)

                # Détection de pagination défaillante: certaines pages reviennent identiques.
                signature = f"{len(products)}::" + "|".join(sorted(signature_tokens)[:12])
                if signature in seen_page_signatures:
                    break
                seen_page_signatures.add(signature)

                pages_scanned += 1

                next_candidate = _extract_next_page_url(soup, url, page)
                if not next_candidate or next_candidate in visited_page_urls:
                    break

                next_page_url = next_candidate
                page += 1
                await asyncio.sleep(0.3)  # politeness delay

            except Exception as e:
                print(f"Erreur catégorie {cat_name} page {page}: {e}")
                async with state_lock:
                    state["fake_scrape_errors"].append(f"{cat_name} page {page}: {e}")
                break

        if pages_scanned >= max_pages:
            async with state_lock:
                state["fake_scrape_errors"].append(f"{cat_name}: max_pages atteint ({max_pages})")

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        categories_to_scan = await _discover_cave_categories(client)
        if not categories_to_scan:
            categories_to_scan = CAVE_CATEGORIES
        await asyncio.gather(
            *(scrape_one_category(client, cat_name) for cat_name in categories_to_scan),
            return_exceptions=True,
        )
    
    state["fake_products"] = fake_products
    state["fake_scrape_status"] = "done" if fake_products else "error"
    save_state()
    print(f"✅ Détection terminée : {len(fake_products)} produits sans image identifiés")

@app.post("/api/fake-products")
async def start_fake_products_scrape(background_tasks: BackgroundTasks):
    if state["fake_scrape_status"] == "running":
        return {"status": "already_running", "run_id": state.get("fake_scrape_run_id")}
    background_tasks.add_task(_scrape_fake_products_task)
    return {"status": "started", "run_id": state.get("fake_scrape_run_id")}

@app.get("/api/fake-products-status")
async def get_fake_products_status():
    return {
        "status": state["fake_scrape_status"],
        "count": state["fake_scrape_count"],
        "run_id": state.get("fake_scrape_run_id"),
        "errors_count": len(state.get("fake_scrape_errors", [])),
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
        "count": len(state["corniche_images"]),
        "images_count": len(state["corniche_images"]),
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


# ─── Multi-site Async Search (Verbose) ──────────────────────────────────────

DEFAULT_SITE_SEARCH_PATHS = [
    "/?s={q}",
    "/search?q={q}",
    "/search/{q}",
    "/recherche?q={q}",
]

SITE_CONNECTORS = {
    "ceptunes.com": {
        "base": "https://ceptunes.com",
        "search_paths": [
            "/?s={q}",
            "/search?q={q}",
        ],
    },
    "boissonsdumonde.fr": {
        "base": "https://boissonsdumonde.fr",
        "search_paths": [
            "/?s={q}",
            "/search?q={q}",
            "/catalogsearch/result/?q={q}",
        ],
    },
    "my-alco-shop.com": {
        "base": "https://my-alco-shop.com",
        "search_paths": [
            "/?s={q}",
            "/search?q={q}",
            "/boutique/?s={q}",
        ],
    },
    "geantdrive.tn": {
        "base": "https://geantdrive.tn",
        "search_paths": [
            "/?s={q}",
            "/search?q={q}",
        ],
    },
    "boissonlacorniche.com": {
        "base": "https://boissonlacorniche.com",
        "search_paths": [
            "/?s={q}",
            "/search/{q}",
            "/boutique/?s={q}",
        ],
    },
    "ventealapropriete.com": {
        "base": "https://www.ventealapropriete.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "leclos-prive.com": {
        "base": "https://www.leclos-prive.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "v2vin.com": {
        "base": "https://www.v2vin.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "oenovinia.com": {
        "base": "https://www.oenovinia.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "showroomprive.com": {
        "base": "https://www.showroomprive.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "veepee.com": {
        "base": "https://www.veepee.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "vinatis.com": {
        "base": "https://www.vinatis.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "nicolas.com": {
        "base": "https://www.nicolas.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "lavinia.com": {
        "base": "https://www.lavinia.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "legroscaviste.com": {
        "base": "https://www.legroscaviste.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "lilovino.com": {
        "base": "https://www.lilovino.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "wineandco.com": {
        "base": "https://www.wineandco.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "twil.fr": {
        "base": "https://www.twil.fr",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "sommelleriedefrance.com": {
        "base": "https://www.sommelleriedefrance.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "cave-spirituelle.com": {
        "base": "https://www.cave-spirituelle.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "whisky.fr": {
        "base": "https://www.whisky.fr",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "thecave.fr": {
        "base": "https://www.thecave.fr",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "idealwine.com": {
        "base": "https://www.idealwine.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "millesima.com": {
        "base": "https://www.millesima.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "1jour1vin.com": {
        "base": "https://www.1jour1vin.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "winesearcher.com": {
        "base": "https://www.winesearcher.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "vivino.com": {
        "base": "https://www.vivino.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "bazarchic.com": {
        "base": "https://www.bazarchic.com",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
    "1clic1cave.fr": {
        "base": "https://www.1clic1cave.fr",
        "search_paths": DEFAULT_SITE_SEARCH_PATHS,
    },
}

PRODUCT_CARD_SELECTORS = [
    "li.product",
    ".product",
    ".product-item",
    "article.product",
    ".products .item",
    ".grid-product__content",
]

LINK_SELECTORS = [
    "a.woocommerce-LoopProduct-link",
    "a.product-item-link",
    "a[href]",
]

NAME_SELECTORS = [
    ".woocommerce-loop-product__title",
    ".product-title",
    "h2",
    "h3",
    "a[title]",
]

IMAGE_SELECTORS = [
    "img.wp-post-image",
    "img.product-image-photo",
    "img.attachment-woocommerce_thumbnail",
    "img",
]


def _build_query_variants(product_name: str):
    variants = []
    base = product_name.strip()
    norm = normalize_name(product_name)
    no_year = re.sub(r"\b(19\d{2}|20[0-2]\d|2030)\b", " ", base)
    no_year = re.sub(r"\s+", " ", no_year).strip()

    for value in [base, no_year, norm]:
        if value and value not in variants:
            variants.append(value)

    return variants[:3]


def _safe_text(node):
    if not node:
        return ""
    return node.get_text(" ", strip=True)


def _extract_candidates_from_html(site_name: str, base_url: str, html: str, source_url: str, query_text: str, product: dict):
    soup = BeautifulSoup(html, "lxml")
    product_norm = normalize_name(product.get("name", ""))
    candidates = []
    seen = set()

    cards = []
    for sel in PRODUCT_CARD_SELECTORS:
        cards = soup.select(sel)
        if cards:
            break

    if not cards:
        cards = soup.select("a[href]")

    for card in cards:
        link_node = None
        for sel in LINK_SELECTORS:
            link_node = card.select_one(sel)
            if link_node:
                break

        name_node = None
        for sel in NAME_SELECTORS:
            name_node = card.select_one(sel)
            if name_node:
                break

        img_node = None
        for sel in IMAGE_SELECTORS:
            img_node = card.select_one(sel)
            if img_node:
                break

        href = ""
        if link_node:
            href = link_node.get("href", "")
        elif card.name == "a":
            href = card.get("href", "")

        page_url = urljoin(base_url, href) if href else source_url
        found_name = _safe_text(name_node) or _safe_text(link_node) or _safe_text(card)
        found_name = found_name[:220]

        if not found_name:
            continue

        img_url = ""
        if img_node:
            img_url = (
                img_node.get("src")
                or img_node.get("data-src")
                or img_node.get("data-lazy-src")
                or img_node.get("data-original")
                or ""
            )
            img_url = urljoin(base_url, img_url) if img_url else ""

        if "placeholder" in img_url or "no-image" in img_url:
            img_url = ""

        norm_found = normalize_name(found_name)
        raw_score = fuzz.token_set_ratio(product_norm, norm_found) if norm_found else 0

        dedup_key = (page_url, img_url, found_name)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        candidates.append({
            "site": site_name,
            "query": query_text,
            "search_url": source_url,
            "page_url": page_url,
            "image_url": img_url,
            "found_name": found_name,
            "found_name_normalized": norm_found,
            "raw_score": round(float(raw_score), 2),
            "detected_via": "html_selectors",
            "has_image": bool(img_url),
        })

    return candidates


def _compute_aggregated_score(product: dict, candidate: dict):
    base = float(candidate.get("raw_score", 0.0))
    score = base
    reasons = []

    cave_name = product.get("name", "")
    cave_cat = product.get("category", "")
    found_name = candidate.get("found_name", "")

    year_cave = extract_year(cave_name)
    year_found = extract_year(found_name)
    if year_cave and year_found:
        if year_cave == year_found:
            score += 10
            reasons.append("year_match:+10")
        else:
            score -= 15
            reasons.append("year_conflict:-15")

    is_cave_wine = "vin" in cave_cat or "champagne" in cave_cat
    is_found_spirit = any(tag in found_name.lower() for tag in SPIRIT_TAGS)
    if is_cave_wine and is_found_spirit:
        score -= 10
        reasons.append("wine_vs_spirit_mismatch:-10")

    if candidate.get("has_image"):
        score += 5
        reasons.append("has_image:+5")

    score = max(0, min(100, score))
    return round(score, 2), reasons


async def _site_search_for_product(
    client: httpx.AsyncClient,
    http_sem: asyncio.Semaphore,
    site_name: str,
    site_conf: dict,
    product: dict,
    min_raw_score: int,
    max_results_per_site: int,
    max_site_query_concurrency: int,
):
    variants = _build_query_variants(product.get("name", ""))
    all_candidates = []
    errors = []
    site_sem = asyncio.Semaphore(max_site_query_concurrency)

    async def fetch_search_page(query: str, path_tpl: str):
        q = quote_plus(query)
        search_url = site_conf["base"] + path_tpl.format(q=q)
        try:
            async with site_sem:
                async with http_sem:
                    resp = await client.get(search_url, timeout=18)
            if resp.status_code != 200:
                return [], None

            candidates = _extract_candidates_from_html(
                site_name=site_name,
                base_url=site_conf["base"],
                html=resp.text,
                source_url=search_url,
                query_text=query,
                product=product,
            )
            return candidates, None
        except Exception as exc:
            return [], f"{search_url} -> {exc}"

    jobs = [
        asyncio.create_task(fetch_search_page(query, path_tpl))
        for query in variants
        for path_tpl in site_conf.get("search_paths", [])
    ]

    for task in asyncio.as_completed(jobs):
        candidates, err = await task
        if err:
            errors.append(err)
            continue
        if candidates:
            all_candidates.extend(candidates)

    filtered = [c for c in all_candidates if c.get("raw_score", 0) >= min_raw_score]
    filtered.sort(key=lambda x: (x.get("has_image", False), x.get("raw_score", 0)), reverse=True)
    return filtered[:max_results_per_site], errors


async def _search_product_across_sites(
    client: httpx.AsyncClient,
    http_sem: asyncio.Semaphore,
    product: dict,
    min_raw_score: int,
    max_results_per_site: int,
    stop_after_two_sites: bool,
    max_site_query_concurrency: int,
    confidence_threshold: int,
):
    start = time.time()

    tasks = {
        site_name: asyncio.create_task(
            _site_search_for_product(
                client=client,
                http_sem=http_sem,
                site_name=site_name,
                site_conf=site_conf,
                product=product,
                min_raw_score=min_raw_score,
                max_results_per_site=max_results_per_site,
                max_site_query_concurrency=max_site_query_concurrency,
            )
        )
        for site_name, site_conf in SITE_CONNECTORS.items()
    }

    results = []
    site_errors = {}
    sites_with_images = set()
    stop_reason = "completed_all_sites"

    pending = set(tasks.values())
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for completed in done:
            site_name = next((k for k, v in tasks.items() if v is completed), "unknown")
            try:
                candidates, errors = await completed
            except Exception as exc:
                candidates, errors = [], [str(exc)]

            if errors:
                site_errors[site_name] = errors[:5]

            for cand in candidates:
                agg, reasons = _compute_aggregated_score(product, cand)
                cand["aggregated_score"] = agg
                cand["aggregated_reasons"] = reasons
                cand["is_confident"] = agg >= confidence_threshold
                results.append(cand)
                if cand.get("has_image") and cand.get("is_confident"):
                    sites_with_images.add(cand.get("site"))

            image_count = sum(1 for c in results if c.get("has_image") and c.get("is_confident"))
            if stop_after_two_sites and len(sites_with_images) >= 2 and image_count >= 2:
                stop_reason = "enough_cross_site_evidence"
                for p in pending:
                    p.cancel()
                pending = set()
                break

    # Ignore cancellation exceptions from tasks stopped by early-stop condition.
    await asyncio.gather(*tasks.values(), return_exceptions=True)

    # Deduplicate and rank final candidates.
    dedup = {}
    for c in results:
        key = (c.get("site"), c.get("page_url"), c.get("image_url"), c.get("found_name"))
        prev = dedup.get(key)
        if not prev or c.get("aggregated_score", 0) > prev.get("aggregated_score", 0):
            dedup[key] = c

    candidates = list(dedup.values())
    candidates.sort(key=lambda x: (x.get("has_image", False), x.get("aggregated_score", 0), x.get("raw_score", 0)), reverse=True)

    confident_candidates = [
        c for c in candidates
        if c.get("is_confident") and c.get("has_image")
    ]

    per_site = {}
    for c in confident_candidates:
        per_site.setdefault(c["site"], 0)
        per_site[c["site"]] += 1

    per_site_all = {}
    for c in candidates:
        per_site_all.setdefault(c["site"], 0)
        per_site_all[c["site"]] += 1

    return {
        "product": {
            "id": product.get("id"),
            "name": product.get("name"),
            "category": product.get("category"),
            "source_url": product.get("url"),
            "fake_img_url": product.get("fake_img_url"),
            "normalized_name": normalize_name(product.get("name", "")),
        },
        "timing_ms": int((time.time() - start) * 1000),
        "stop_reason": stop_reason,
        "confidence_threshold": confidence_threshold,
        "searched_sites": list(SITE_CONNECTORS.keys()),
        "sites_with_images": sorted(list(sites_with_images)),
        "candidates_count": len(confident_candidates),
        "all_candidates_count": len(candidates),
        "per_site_counts": per_site,
        "per_site_all_counts": per_site_all,
        "candidates": candidates,
        "top_candidates": confident_candidates[:3],
        "site_errors": site_errors,
    }


async def _run_multisite_search_task(options: dict):
    state["multi_site"] = {
        "status": "running",
        "run_id": f"run-{int(time.time())}",
        "started_at": int(time.time()),
        "finished_at": None,
        "progress": {
            "total_products": 0,
            "processed_products": 0,
            "with_candidates": 0,
            "early_stopped": 0,
        },
        "options": options,
        "site_errors": {},
        "results": [],
    }

    if not state["fake_products"]:
        state["multi_site"]["status"] = "error"
        state["multi_site"]["finished_at"] = int(time.time())
        state["multi_site"]["site_errors"] = {"global": ["Aucun produit fake disponible"]}
        return

    products = list(state["fake_products"])
    max_products = options.get("max_products")
    if max_products and max_products > 0:
        products = products[:max_products]

    state["multi_site"]["progress"]["total_products"] = len(products)

    http_sem = asyncio.Semaphore(options["max_http_concurrency"])
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ImageMatcher/2.0; +https://localhost)",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20) as client:
        queue = asyncio.Queue()
        for product in products:
            queue.put_nowait(product)

        async def worker():
            while True:
                product = await queue.get()
                if product is None:
                    queue.task_done()
                    break

                result = await _search_product_across_sites(
                    client=client,
                    http_sem=http_sem,
                    product=product,
                    min_raw_score=options["min_raw_score"],
                    max_results_per_site=options["max_results_per_site"],
                    stop_after_two_sites=options["stop_after_two_sites"],
                    max_site_query_concurrency=options["max_site_query_concurrency"],
                    confidence_threshold=options["confidence_threshold"],
                )

                state["multi_site"]["results"].append(result)
                state["multi_site"]["progress"]["processed_products"] += 1
                if result["candidates_count"] > 0:
                    state["multi_site"]["progress"]["with_candidates"] += 1
                if result["stop_reason"] == "enough_cross_site_evidence":
                    state["multi_site"]["progress"]["early_stopped"] += 1

                for site_name, errs in result["site_errors"].items():
                    state["multi_site"]["site_errors"].setdefault(site_name, [])
                    state["multi_site"]["site_errors"][site_name].extend(errs[:2])

                queue.task_done()

        workers = [
            asyncio.create_task(worker())
            for _ in range(options["max_product_concurrency"])
        ]

        await queue.join()
        for _ in workers:
            queue.put_nowait(None)
        await asyncio.gather(*workers, return_exceptions=False)

    state["multi_site"]["results"].sort(key=lambda item: item["product"].get("id", 0))
    state["multi_site"]["status"] = "done"
    state["multi_site"]["finished_at"] = int(time.time())


@app.post("/api/multisite-search/start")
async def start_multisite_search(
    background_tasks: BackgroundTasks,
    min_raw_score: int = MULTISITE_DEFAULT_MIN_RAW_SCORE,
    max_results_per_site: int = MULTISITE_DEFAULT_MAX_RESULTS_PER_SITE,
    max_product_concurrency: int = MULTISITE_DEFAULT_MAX_PRODUCT_CONCURRENCY,
    max_http_concurrency: int = MULTISITE_DEFAULT_MAX_HTTP_CONCURRENCY,
    max_site_query_concurrency: int = MULTISITE_DEFAULT_MAX_SITE_QUERY_CONCURRENCY,
    confidence_threshold: int = 70,
    max_products: int = 0,
    stop_after_two_sites: bool = True,
):
    if state["multi_site"].get("status") == "running":
        return {"status": "already_running", "run_id": state["multi_site"].get("run_id")}

    options = {
        "min_raw_score": max(0, min(100, min_raw_score)),
        "max_results_per_site": max(1, min(20, max_results_per_site)),
        "max_product_concurrency": max(1, min(120, max_product_concurrency)),
        "max_http_concurrency": max(1, min(500, max_http_concurrency)),
        "max_site_query_concurrency": max(1, min(60, max_site_query_concurrency)),
        "confidence_threshold": max(70, min(100, confidence_threshold)),
        "max_products": max_products if max_products > 0 else None,
        "stop_after_two_sites": bool(stop_after_two_sites),
    }
    background_tasks.add_task(_run_multisite_search_task, options)
    return {"status": "started", "options": options}


@app.get("/api/multisite-search/status")
async def get_multisite_status():
    ms = state["multi_site"]
    return {
        "status": ms.get("status"),
        "run_id": ms.get("run_id"),
        "started_at": ms.get("started_at"),
        "finished_at": ms.get("finished_at"),
        "progress": ms.get("progress", {}),
        "options": ms.get("options", {}),
        "site_errors_count": {k: len(v) for k, v in ms.get("site_errors", {}).items()},
        "results_count": len(ms.get("results", [])),
    }


@app.get("/api/multisite-search/results")
async def get_multisite_results():
    ms = state["multi_site"]
    if ms.get("status") == "idle":
        return JSONResponse(status_code=400, content={"error": "Lance d'abord /api/multisite-search/start"})

    return {
        "status": ms.get("status"),
        "run_id": ms.get("run_id"),
        "progress": ms.get("progress", {}),
        "results": ms.get("results", []),
        "site_errors": ms.get("site_errors", {}),
    }


@app.get("/api/multisite-search/export-csv")
async def export_multisite_csv():
    ms = state["multi_site"]
    if not ms.get("results"):
        return JSONResponse(status_code=400, content={"error": "Aucun résultat multi-site à exporter"})

    csv_path = Path("export_multisite_candidates.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "ID Produit Cave",
            "Nom Produit Cave",
            "URL Produit Cave",
            "Site",
            "Nom Trouvé",
            "URL Page Trouvée",
            "URL Image",
            "Requête",
            "Score Brut",
            "Score Agrégé",
            "Confiant",
            "Seuil Confiance",
            "Raisons Agrégation",
            "Stop Reason Produit",
            "Durée Produit (ms)",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in ms["results"]:
            product = item.get("product", {})
            candidates = item.get("candidates", [])
            if not candidates:
                writer.writerow({
                    "ID Produit Cave": product.get("id"),
                    "Nom Produit Cave": product.get("name"),
                    "URL Produit Cave": product.get("source_url"),
                    "Site": "",
                    "Nom Trouvé": "",
                    "URL Page Trouvée": "",
                    "URL Image": "",
                    "Requête": "",
                    "Score Brut": "",
                    "Score Agrégé": "",
                    "Confiant": "",
                    "Seuil Confiance": item.get("confidence_threshold"),
                    "Raisons Agrégation": "",
                    "Stop Reason Produit": item.get("stop_reason"),
                    "Durée Produit (ms)": item.get("timing_ms"),
                })
                continue

            for cand in candidates:
                writer.writerow({
                    "ID Produit Cave": product.get("id"),
                    "Nom Produit Cave": product.get("name"),
                    "URL Produit Cave": product.get("source_url"),
                    "Site": cand.get("site"),
                    "Nom Trouvé": cand.get("found_name"),
                    "URL Page Trouvée": cand.get("page_url"),
                    "URL Image": cand.get("image_url"),
                    "Requête": cand.get("query"),
                    "Score Brut": cand.get("raw_score"),
                    "Score Agrégé": cand.get("aggregated_score"),
                    "Confiant": "oui" if cand.get("is_confident") else "non",
                    "Seuil Confiance": item.get("confidence_threshold"),
                    "Raisons Agrégation": " | ".join(cand.get("aggregated_reasons", [])),
                    "Stop Reason Produit": item.get("stop_reason"),
                    "Durée Produit (ms)": item.get("timing_ms"),
                })

    return FileResponse(
        path=str(csv_path),
        media_type="text/csv",
        filename="multisite_candidates.csv",
    )


@app.get("/api/multisite-search/export-top-images-zip")
async def export_multisite_top_images_zip():
    ms = state["multi_site"]
    if not ms.get("results"):
        return JSONResponse(status_code=400, content={"error": "Aucun résultat multi-site disponible"})

    zip_path = Path("export_multisite_top_images.zip")
    used_names = {}
    downloaded = 0

    def infer_ext(image_url: str, content_type: str) -> str:
        ext = Path(image_url.split("?")[0]).suffix.lower()
        allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if ext in allowed:
            return ".jpg" if ext == ".jpeg" else ext

        ct = (content_type or "").lower()
        if "png" in ct:
            return ".png"
        if "webp" in ct:
            return ".webp"
        if "gif" in ct:
            return ".gif"
        return ".jpg"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ImageMatcher/2.0; +https://localhost)",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=25) as client:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for item in ms["results"]:
                product = item.get("product", {})
                product_name = product.get("name") or "produit"

                candidates = item.get("candidates", [])
                candidates_sorted = sorted(
                    candidates,
                    key=lambda c: (c.get("has_image", False), c.get("aggregated_score", 0), c.get("raw_score", 0)),
                    reverse=True,
                )
                threshold = item.get("confidence_threshold", 70)
                best = next((
                    c for c in candidates_sorted
                    if c.get("image_url") and c.get("aggregated_score", 0) >= threshold and c.get("is_confident")
                ), None)
                if not best:
                    continue

                image_url = best.get("image_url")
                if not image_url:
                    continue

                try:
                    resp = await client.get(image_url)
                    if resp.status_code != 200 or not resp.content:
                        continue

                    ext = infer_ext(image_url, resp.headers.get("content-type", ""))
                    base_name = safe_filename(product_name, "") or "produit"

                    if base_name in used_names:
                        used_names[base_name] += 1
                        final_name = f"{base_name}_{used_names[base_name]}{ext}"
                    else:
                        used_names[base_name] = 1
                        final_name = f"{base_name}{ext}"

                    zip_file.writestr(final_name, resp.content)
                    downloaded += 1

                except Exception as e:
                    print(f"Erreur ZIP image {image_url}: {e}")
                    continue

    if downloaded == 0:
        return JSONResponse(status_code=400, content={"error": "Aucune image téléchargeable trouvée"})

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename="top_images_lacave.zip",
    )
