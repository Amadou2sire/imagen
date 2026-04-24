import React, { useState, useEffect } from 'react'

const API = "http://localhost:8000"
const TARGET_SITES = [
  "ceptunes.com",
  "boissonsdumonde.fr",
  "my-alco-shop.com",
  "geantdrive.tn",
  "boissonlacorniche.com",
  "ventealapropriete.com",
  "leclos-prive.com",
  "v2vin.com",
  "oenovinia.com",
  "showroomprive.com",
  "veepee.com",
  "vente-exclusive.com",
  "privalia.com",
  "eboutic.ch",
  "vinatis.com",
  "nicolas.com",
  "lavinia.com",
  "legroscaviste.com",
  "lilovino.com",
  "wineandco.com",
  "twil.fr",
  "sommelleriedefrance.com",
  "cave-spirituelle.com",
  "whisky.fr",
  "thecave.fr",
  "idealwine.com",
  "millesima.com",
  "1jour1vin.com",
  "winesearcher.com",
  "vivino.com",
  "bazarchic.com",
  "1clic1cave.fr",
]

const SITE_PARENT_GROUPS = {
  "nicolas.com": "Groupe Castel",
  "vinatis.com": "Groupe Castel",
  "veepee.com": "Groupe Veepee / Holding Oredis",
  "vente-exclusive.com": "Groupe Veepee / Holding Oredis",
  "privalia.com": "Groupe Veepee / Holding Oredis",
  "eboutic.ch": "Groupe Veepee / Holding Oredis",
  "showroomprive.com": "SRP Groupe",
  "wineandco.com": "COFEPP",
  "millesima.com": "Millesima",
  "lavinia.com": "Famille Servant",
  "ventealapropriete.com": "Indépendant",
  "leclos-prive.com": "Indépendant",
  "v2vin.com": "Indépendant",
  "oenovinia.com": "Indépendant",
  "legroscaviste.com": "Indépendant",
  "lilovino.com": "Indépendant",
  "twil.fr": "Indépendant",
  "sommelleriedefrance.com": "Indépendant",
  "cave-spirituelle.com": "Indépendant",
  "idealwine.com": "Indépendant",
  "1jour1vin.com": "Indépendant",
  "1clic1cave.fr": "Indépendant",
  "boissonlacorniche.com": "Indépendant",
  "boissonsdumonde.fr": "Indépendant",
  "my-alco-shop.com": "Indépendant",
  "geantdrive.tn": "Indépendant",
  "whisky.fr": "Indépendant",
  "thecave.fr": "Indépendant",
  "winesearcher.com": "Indépendant",
  "vivino.com": "Indépendant",
  "bazarchic.com": "Indépendant",
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const scoreColor = (s) => {
  if (s >= 85) return "#4a9e6a"
  if (s >= 65) return "#c9a84c"
  return "#c05050"
}

// ── Sub-components ───────────────────────────────────────────────────────────

function Toast({ msg, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [onClose])

  return (
    <div className={`fixed bottom-6 right-6 bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-[14px_18px] text-[11px] z-[9000] max-w-[320px] flex items-start gap-[10px] animate-[fadeUp_0.3s_ease] ${type === 'error' ? 'border-[#c05050]' : 'border-[#4a9e6a]'}`}>
      <span className="text-base">{type === "error" ? "⚠" : "✓"}</span>
      <span className="leading-[1.5]" style={{ color: type === "error" ? "var(--error-t)" : "var(--success-t)" }}>{msg}</span>
    </div>
  )
}

function ImageBox({ src, label, isEmpty }) {
  const [err, setErr] = useState(false)
  return (
    <div className="flex flex-col gap-[6px]">
      <div className="text-[8px] tracking-[0.2em] uppercase text-white font-mono">{label}</div>
      <div className="aspect-square bg-[#0f0e0d] border-1 border-[#2a2520] rounded-[2px] overflow-hidden flex items-center justify-center relative">
        {!isEmpty && src && !err ? (
          <img src={src} alt={label} className="object-contain w-full h-full p-2" onError={() => setErr(true)} />
        ) : (
          <div className="flex flex-col items-center gap-[4px] text-white">
            <div className="text-xl opacity-40">{isEmpty ? "—" : "✕"}</div>
            <div className="text-[8px] tracking-[0.1em] text-center leading-tight">{isEmpty ? "aucune\ncorrespondance" : "indisponible"}</div>
          </div>
        )}
      </div>
    </div>
  )
}

function MatchCard({ match }) {
  const isMatched = match.status === "matched"
  const sc = match.match_score

  return (
    <div className={`bg-[#181614] border-1 border-[#2a2520] rounded-[3px] overflow-hidden transition-colors hover:border-[#5a5248] animate-[fadeUp_0.4s_ease] ${isMatched ? 'hover:border-[#8a6c2a]' : ''}`}>
      <div className="p-[12px_14px] border-b-1 border-b-[#2a2520] flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] text-[#e8dcc8] leading-[1.4] truncate">{match.cave_product_name}</div>
          {match.cave_product_url && (
            <a href={match.cave_product_url} target="_blank" rel="noopener noreferrer"
               className="text-[9px] text-[#8a6c2a] no-underline tracking-[0.1em] hover:text-[#c9a84c] transition-colors">
              cave-privee ↗
            </a>
          )}
        </div>
        <span className={`text-[9px] tracking-[0.15em] uppercase p-[2px_8px] rounded-[2px] font-medium border-1 ${isMatched ? 'bg-[#2d5a3d] text-[#4a9e6a] border-[#3a7a50]' : 'bg-[#5a2020] text-[#c05050] border-[#7a3030]'}`}>
          {isMatched ? "matché" : "non trouvé"}
        </span>
      </div>

      <div className="grid grid-cols-[1fr_28px_1fr] items-center p-3.5 pt-4">
        <ImageBox src={match.cave_fake_img} label="Actuelle (fake)" isEmpty={false} />
        <div className="flex items-center justify-center text-white text-sm mt-3.5">→</div>
        <ImageBox
          src={isMatched ? `${API}${match.corniche_local_url}` : null}
          label={isMatched ? "Corniche" : "—"}
          isEmpty={!isMatched}
        />
      </div>

      {isMatched && (
        <div className="p-[8px_14px] border-t-1 border-t-[#2a2520] flex items-center justify-between gap-2">
          <div className="flex-1">
            <div className="h-[3px] bg-[#2a2520] rounded-[2px]">
              <div
                className="h-[3px] rounded-[2px] transition-all duration-700"
                style={{ width: `${sc}%`, background: scoreColor(sc) }}
              />
            </div>
          </div>
          <div className="text-[10px] tabular-nums text-right min-w-[44px]" style={{ color: scoreColor(sc) }}>
            {sc}%
          </div>
          <div className="text-[9px] text-white max-w-[120px] text-right truncate" title={match.corniche_product_name}>
            {match.corniche_product_name}
          </div>
        </div>
      )}
    </div>
  )
}

function StepCard({ num, title, desc, statusEl, actionEl, done }) {
  return (
    <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[4px] fade-up shadow-lg">
      <div className="p-[18px_24px] border-b-1 border-b-[#2a2520] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-7 h-7 rounded-[2px] flex items-center justify-center text-[11px] flex-shrink-0 transition-all ${done ? 'bg-[#2d5a3d] border-1 border-[#4a9e6a] text-[#4a9e6a]' : 'bg-transparent border-1 border-[#2a2520] text-white'}`}>
            {done ? "✓" : num}
          </div>
          <span className="font-serif text-sm text-[#e8dcc8]">{title}</span>
        </div>
        {statusEl}
      </div>
      <div className="p-6">
        <p className="text-[11px] text-white mb-4 leading-[1.7] font-mono">{desc}</p>
        {actionEl}
      </div>
    </div>
  )
}

function MultiSiteResultCard({ item }) {
  const product = item.product || {}
  const topCandidates = item.top_candidates || []

  return (
    <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] overflow-hidden">
      <div className="p-[12px_14px] border-b-1 border-b-[#2a2520]">
        <div className="text-[11px] text-[#e8dcc8] leading-[1.4]">{product.name}</div>
        <div className="mt-1 flex items-center gap-2 text-[9px] text-white font-mono">
          <span>ID #{product.id}</span>
          <span>•</span>
          <span>{item.candidates_count || 0} candidats</span>
          <span>•</span>
          <span>{item.timing_ms || 0} ms</span>
        </div>
      </div>

      <div className="p-3.5 flex flex-col gap-2.5">
        {topCandidates.length > 0 ? topCandidates.map((cand, idx) => (
          <div key={`${cand.site}-${idx}`} className="bg-[#141210] border-1 border-[#2a2520] rounded-[2px] p-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="text-[9px] tracking-[0.1em] uppercase text-[#8a6c2a] font-mono">{cand.site}</div>
              <div className="text-[10px] font-mono" style={{ color: scoreColor(cand.aggregated_score || 0) }}>
                {cand.aggregated_score || 0}%
              </div>
            </div>
            <div className="text-[10px] text-[#d4c9b8] mt-1 leading-[1.4]">{cand.found_name || "Nom indisponible"}</div>
            <div className="mt-2 flex flex-wrap gap-3 text-[9px] font-mono">
              {cand.page_url && (
                <a href={cand.page_url} target="_blank" rel="noopener noreferrer" className="text-[#c9a84c] hover:text-[#e8dcc8]">
                  page ↗
                </a>
              )}
              {cand.image_url && (
                <a href={cand.image_url} target="_blank" rel="noopener noreferrer" className="text-[#4a9e6a] hover:text-[#e8dcc8]">
                  image ↗
                </a>
              )}
              <span className="text-white">raw {cand.raw_score || 0}%</span>
            </div>
          </div>
        )) : (
          <div className="text-[10px] text-white font-mono">Aucun candidat trouvé</div>
        )}
      </div>
    </div>
  )
}

// ── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [fakeProducts, setFakeProducts]   = useState([])
  const [fakeScrapeStatus, setFakeScrapeStatus] = useState("idle")
  const [fakeScrapeCount, setFakeScrapeCount] = useState(0)
  const [stats, setStats]                 = useState(null)
  const [threshold, setThreshold]         = useState(70)
  const [filter, setFilter]               = useState("all") // all | matched | unmatched
  const [search, setSearch]               = useState("")
  const [loading, setLoading]             = useState({ fake: false, multi: false })
  const [toast, setToast]                 = useState(null)
  const [activeSection, setActiveSection] = useState("setup")
  const [multiStatus, setMultiStatus]     = useState("idle")
  const [multiProgress, setMultiProgress] = useState({ total_products: 0, processed_products: 0, with_candidates: 0, early_stopped: 0 })
  const [multiResults, setMultiResults]   = useState([])
  const [multiErrors, setMultiErrors]     = useState({})

  const showToast = (msg, type = "info") => setToast({ msg, type })

  // Polling fake scrape
  useEffect(() => {
    if (fakeScrapeStatus !== "running") return
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/fake-products-status`)
        const d = await r.json()
        setFakeScrapeStatus(d.status)
        setFakeScrapeCount(d.count || 0)
        if (d.status === "done") {
          clearInterval(iv)
          // On recharge les produits une fois fini
          const res = await fetch(`${API}/api/fake-products-get`)
          const data = await res.json()
          // Le backend renvoie directement la liste, on gère les deux cas par sécurité
          const products = Array.isArray(data) ? data : (data.products || [])
          setFakeProducts(products)
          
          showToast(`Analyse terminée — ${d.count} produits sans image trouvés`, "success")
        }
      } catch (err) {
        console.error("Polling error:", err)
      }
    }, 2000)
    return () => clearInterval(iv)
  }, [fakeScrapeStatus])

  // Polling multisite search
  useEffect(() => {
    if (multiStatus !== "running") return
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/multisite-search/status`)
        const d = await r.json()
        setMultiStatus(d.status || "idle")
        setMultiProgress(d.progress || { total_products: 0, processed_products: 0, with_candidates: 0, early_stopped: 0 })

        if (d.status === "done") {
          clearInterval(iv)
          const rr = await fetch(`${API}/api/multisite-search/results`)
          const rd = await rr.json()
          setMultiResults(rd.results || [])
          setMultiErrors(rd.site_errors || {})

          const total = (rd.results || []).length
          const withCand = (rd.results || []).filter(x => (x.candidates_count || 0) > 0).length
          setStats({ total, matched: withCand, unmatched: Math.max(0, total - withCand) })
          setActiveSection("results")
          showToast(`Recherche multi-sites terminée : ${withCand}/${total} produits avec candidats`, "success")
          setLoading(prev => ({ ...prev, multi: false }))
        }

        if (d.status === "error") {
          clearInterval(iv)
          setLoading(prev => ({ ...prev, multi: false }))
          showToast("Erreur sur la recherche multi-sites", "error")
        }
      } catch (err) {
        console.error("Polling multisite error:", err)
      }
    }, 2000)
    return () => clearInterval(iv)
  }, [multiStatus])

  const handleLoadFake = async () => {
    try {
      const r = await fetch(`${API}/api/fake-products`, { method: "POST" })
      if (!r.ok) throw new Error()
      setFakeScrapeStatus("running")
      showToast("Analyse des produits sans image en cours…", "info")
    } catch {
      showToast("Impossible de joindre le backend FastAPI (port 8000)", "error")
    }
  }

  const handleStartMultiSiteSearch = async () => {
    setLoading(prev => ({ ...prev, multi: true }))
    try {
      const q = new URLSearchParams({
        min_raw_score: String(Math.max(10, threshold - 45)),
        max_results_per_site: "10",
        max_product_concurrency: "60",
        max_http_concurrency: "400",
        max_site_query_concurrency: "60",
        confidence_threshold: String(Math.max(70, threshold)),
        stop_after_two_sites: "true",
      })
      const r = await fetch(`${API}/api/multisite-search/start?${q.toString()}`, { method: "POST" })
      if (!r.ok) throw new Error()
      const d = await r.json()
      if (d.status === "already_running") {
        setMultiStatus("running")
        showToast("Une recherche multi-sites est déjà en cours", "info")
      } else {
        setMultiResults([])
        setMultiErrors({})
        setMultiProgress({ total_products: 0, processed_products: 0, with_candidates: 0, early_stopped: 0 })
        setMultiStatus("running")
        showToast("Recherche multi-sites démarrée…", "info")
      }
    } catch {
      setLoading(prev => ({ ...prev, multi: false }))
      showToast("Erreur lors du lancement de la recherche multi-sites", "error")
    }
  }

  const handleExport = () => {
    if (!multiResults.length) {
      showToast("Veuillez d'abord lancer la recherche multi-sites", "error")
      return
    }
    window.open(`${API}/api/multisite-search/export-csv`, "_blank")
  }

  const handleDownloadTopImagesZip = () => {
    if (!multiResults.length) {
      showToast("Veuillez d'abord lancer la recherche multi-sites", "error")
      return
    }
    window.open(`${API}/api/multisite-search/export-top-images-zip`, "_blank")
  }

  const filteredMulti = multiResults.filter(item => {
    const productName = (item.product?.name || "").toLowerCase()
    if (search && !productName.includes(search.toLowerCase())) return false
    if (filter === "matched" && (item.candidates_count || 0) <= 0) return false
    if (filter === "unmatched" && (item.candidates_count || 0) > 0) return false
    return true
  })

  const siteRows = TARGET_SITES.map(site => {
    const foundProducts = multiResults.reduce((acc, item) => acc + ((item.per_site_counts?.[site] || 0) > 0 ? 1 : 0), 0)
    const foundCandidates = multiResults.reduce((acc, item) => acc + (item.per_site_counts?.[site] || 0), 0)
    const errorsCount = Array.isArray(multiErrors?.[site]) ? multiErrors[site].length : 0
    const parentGroup = SITE_PARENT_GROUPS[site] || "Indépendant"

    let label = "en attente"
    if (multiStatus === "running") label = "recherche…"
    if (multiResults.length > 0) label = foundProducts > 0 ? "trouvé" : "rien trouvé"
    if (errorsCount > 0 && foundProducts === 0) label = "avec erreurs"

    return { site, parentGroup, foundProducts, foundCandidates, errorsCount, label }
  })

  return (
    <div className="flex min-h-screen">
      
      {/* ── Sidebar ── */}
      <aside className="fixed left-0 top-0 bottom-0 w-[240px] bg-[#141210] border-r-1 border-r-[#2a2520] flex flex-col z-[100]">
        <div className="p-[32px_24px_24px] border-b-1 border-b-[#2a2520]">
          <div className="font-serif text-lg font-bold text-[#e8dcc8] tracking-[0.02em] leading-[1.2]">Image<br/>Matcher</div>
          <div className="text-[9px] tracking-[0.18em] uppercase text-[#8a6c2a] mt-1 font-mono">Cave Privée × Corniche</div>
        </div>

        {[
          { id: "setup",   num: "01", name: "Configuration", status: fakeScrapeStatus === "done" ? `${fakeScrapeCount} produits fake` : fakeScrapeStatus === "running" ? "En cours…" : "En attente" },
          { id: "match",   num: "02", name: "Recherche Multi-sites", status: multiStatus === "running" ? `${multiProgress.processed_products}/${multiProgress.total_products} en cours` : multiResults.length ? `${multiResults.length} traités` : "En attente" },
          { id: "results", num: "03", name: "Rapports & CSV",  status: stats ? `${stats.matched}/${stats.total} avec candidats` : "—" },
        ].map(s => (
          <div
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`p-[16px_24px] border-b-1 border-b-[#2a2520] cursor-pointer transition-colors relative hover:bg-[rgba(201,168,76,0.04)] ${activeSection === s.id ? 'bg-[rgba(201,168,76,0.07)] before:content-[""] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[2px] before:bg-[#c9a84c]' : ''}`}
          >
            <div className="text-[9px] tracking-[0.2em] uppercase text-white mb-1 font-mono">Étape {s.num}</div>
            <div className="text-xs text-[#e8dcc8] font-normal font-mono">{s.name}</div>
            <div className="text-[10px] mt-[3px] font-mono" style={{
              color: s.status === "En attente" ? "var(--muted)" :
                     s.status.includes("En cours") ? "var(--gold-dim)" : "var(--success-t)"
            }}>{s.status}</div>
          </div>
        ))}

        <div className="mt-auto p-[20px_24px] border-t-1 border-t-[#2a2520] text-[9px] tracking-[0.1em] uppercase text-white font-mono">
          v1.0.0 — FastAPI + React<br />
          <span className="text-[#2a2520]">──────────────</span><br />
          Seuil : <span className="text-[#c9a84c] font-bold">{threshold}%</span>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 ml-[240px] min-h-screen bg-[#0d0c0b]">
        
        {/* Topbar */}
        <div className="h-14 border-b-1 border-b-[#2a2520] flex items-center p-[0_32px] justify-between bg-[#141210] sticky top-0 z-50">
          <span className="font-serif text-[15px] text-[#e8dcc8] italic">
            {activeSection === "setup"   && "Configuration & Chargement des données"}
            {activeSection === "match"   && "Recherche Async Sur Sites Cibles"}
            {activeSection === "results" && "Analyse Verbose des Correspondances"}
          </span>
          <div className="flex items-center gap-4">
            {stats && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleExport}
                  className="bg-transparent border-1 border-[#c9a84c] text-[#c9a84c] text-[11px] tracking-[0.1em] uppercase p-[9px_16px] rounded-[2px] cursor-pointer transition-all hover:bg-[#c9a84c] hover:text-[#0d0c0b] disabled:opacity-30 font-mono"
                >
                  ↓ EXPORTER CSV
                </button>
                <button
                  onClick={handleDownloadTopImagesZip}
                  className="bg-transparent border-1 border-[#4a9e6a] text-[#4a9e6a] text-[11px] tracking-[0.1em] uppercase p-[9px_16px] rounded-[2px] cursor-pointer transition-all hover:bg-[#4a9e6a] hover:text-[#0d0c0b] disabled:opacity-30 font-mono"
                >
                  ↓ ZIP TOP IMAGES
                </button>
              </div>
            )}
            <div className="flex items-center gap-1.5 text-[10px] text-white tracking-[0.1em] font-mono">
              <div className={`w-1.5 h-1.5 rounded-full ${fakeScrapeStatus === 'done' ? 'bg-[#4a9e6a]' : (fakeScrapeStatus === 'running' || multiStatus === 'running') ? 'bg-[#c9a84c]' : 'bg-[#2a2520]'}`} />
              {fakeScrapeStatus === 'done' ? "backend connecté" : "en attente…"}
            </div>
          </div>
        </div>

        <div className="p-8 max-w-6xl mx-auto">
          
          {/* ───────────── SETUP ───────────── */}
          {activeSection === "setup" && (
            <div className="flex flex-col gap-8 fade-up">
              <div className="flex items-center gap-3 text-[#2a2520] text-[9px] tracking-[0.3em] uppercase after:content-[''] after:flex-1 after:h-[1px] after:bg-[#2a2520] font-mono">
                Étape 01 — Base de données
              </div>

              <StepCard
                num="1"
                title="Détection des images absentes"
                desc="Cette étape analyse 'la-cave-privee.com' pour identifier tous les produits affichant actuellement l'image fake (no-image.gif). Les données seront conservées en mémoire pour le processus de matching."
                done={fakeScrapeStatus === "done"}
                statusEl={fakeScrapeStatus === "running" ? (
                  <span className="bg-[rgba(201,168,76,0.1)] text-[#c9a84c] border-1 border-[#8a6c2a] text-[9px] tracking-[1.5px] uppercase p-[2px_8px] rounded-[2px] font-mono inline-flex items-center gap-2">
                    <span className="flex gap-1">
                      <span className="w-1 h-1 bg-[#c9a84c] rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <span className="w-1 h-1 bg-[#c9a84c] rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <span className="w-1 h-1 bg-[#c9a84c] rounded-full animate-bounce" />
                    </span>
                    {fakeScrapeCount} produits détectés…
                  </span>
                ) : fakeScrapeStatus === "done" && (
                  <span className="bg-[#2d5a3d] text-[#4a9e6a] border-1 border-[#3a7a50] text-[9px] tracking-[0.15em] uppercase p-[2px_8px] rounded-[2px] font-mono">
                    {fakeScrapeCount} produits identifiés
                  </span>
                )}
                actionEl={
                  <button
                    onClick={handleLoadFake}
                    disabled={fakeScrapeStatus === "running"}
                    className="bg-transparent border-1 border-[#c9a84c] text-[#c9a84c] text-[11px] tracking-[0.1em] uppercase p-[9px_20px] rounded-[2px] cursor-pointer transition-all hover:bg-[#c9a84c] hover:text-[#0d0c0b] disabled:opacity-30 disabled:cursor-not-allowed font-mono"
                  >
                    {fakeScrapeStatus === "running" ? "Analyse en cours…" : fakeScrapeStatus === "done" ? "Relancer l'analyse" : "Lancer la détection"}
                  </button>
                }
              />
            </div>
          )}

          {/* ───────────── MATCH ───────────── */}
          {activeSection === "match" && (
            <div className="flex flex-col gap-8 fade-up">
              <div className="flex items-center gap-3 text-[#2a2520] text-[9px] tracking-[0.3em] uppercase after:content-[''] after:flex-1 after:h-[1px] after:bg-[#2a2520] font-mono">
                Étape 02 — Recherche Multi-sites
              </div>

              <StepCard
                num="2"
                title="Recherche d'images sur 5 sites (async)"
                desc="Cette étape recherche uniquement les produits sans image sur plusieurs sites en parallèle. Faux positifs et résultats multiples sont autorisés, puis agrégés dans les résultats verbose. La recherche s'arrête tôt pour un produit dès que 2 images sont trouvées sur 2 sites différents."
                done={multiResults.length > 0}
                statusEl={loading.multi || multiStatus === "running" ? (
                  <span className="text-[10px] text-[#c9a84c] font-mono animate-pulse">{multiProgress.processed_products}/{multiProgress.total_products || "?"} produits analysés…</span>
                ) : null}
                actionEl={
                  <div className="flex flex-col gap-6">
                    <div className="max-w-[320px]">
                      <div className="flex justify-between text-[9px] mb-3 font-mono tracking-widest text-white uppercase">
                        <span>Seuil de confiance</span>
                        <span className="text-[#c9a84c] font-bold">{threshold}%</span>
                      </div>
                      <input
                        type="range" min="70" max="95" value={threshold}
                        onChange={e => setThreshold(Number(e.target.value))}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <button
                        onClick={handleStartMultiSiteSearch}
                        disabled={loading.multi || multiStatus === "running" || fakeProducts.length === 0}
                        className="bg-transparent border-1 border-[#c9a84c] text-[#c9a84c] text-[11px] tracking-[0.1em] uppercase p-[9px_20px] rounded-[2px] cursor-pointer transition-all hover:bg-[#c9a84c] hover:text-[#0d0c0b] disabled:opacity-30 disabled:cursor-not-allowed font-mono"
                      >
                        {loading.multi || multiStatus === "running" ? "Recherche en cours…" : "Lancer recherche multi-sites"}
                      </button>
                    </div>
                  </div>
                }
              />

              <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[4px] p-5">
                <div className="text-[10px] tracking-[0.15em] uppercase text-[#8a6c2a] font-mono mb-4">Sites analysés</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {siteRows.map((row) => (
                    <div key={row.site} className="bg-[#141210] border-1 border-[#2a2520] rounded-[2px] p-3 flex items-center justify-between gap-3">
                      <div>
                        <div className="text-[10px] text-[#e8dcc8] font-mono">{row.site}</div>
                        <div className="text-[9px] text-[#8a6c2a] font-mono mt-0.5">{row.parentGroup}</div>
                        <div className="text-[9px] text-white font-mono mt-1">{row.foundProducts} produits • {row.foundCandidates} candidats</div>
                      </div>
                      <span className={`text-[9px] tracking-[0.12em] uppercase border-1 rounded-[2px] p-[2px_8px] font-mono ${row.label === 'trouvé' ? 'bg-[#2d5a3d] text-[#4a9e6a] border-[#3a7a50]' : row.label === 'recherche…' ? 'bg-[rgba(201,168,76,0.1)] text-[#c9a84c] border-[#8a6c2a]' : row.label === 'avec erreurs' ? 'bg-[#5a2020] text-[#c05050] border-[#7a3030]' : 'bg-transparent text-white border-[#2a2520]'}`}>
                        {row.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ───────────── RESULTS ───────────── */}
          {activeSection === "results" && (
            <div className="flex flex-col gap-8 fade-up">
              <div className="flex items-center gap-3 text-[#2a2520] text-[9px] tracking-[0.3em] uppercase after:content-[''] after:flex-1 after:h-[1px] after:bg-[#2a2520] font-mono">
                Étape 03 — Revue des résultats
              </div>

              {/* Stats Bar */}
              {stats && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-5 flex flex-col gap-1">
                    <div className="font-serif text-3xl text-[#e8dcc8]">{stats.total}</div>
                    <div className="text-[9px] tracking-[0.2em] uppercase text-white font-mono">Produits Fake</div>
                  </div>
                  <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-5 flex flex-col gap-1">
                    <div className="font-serif text-3xl text-[#c9a84c]">{stats.matched}</div>
                    <div className="text-[9px] tracking-[0.2em] uppercase text-white font-mono">Produits Avec Candidats</div>
                    <div className="text-[10px] text-[#8a6c2a] mt-1 font-mono">{Math.round(stats.matched/stats.total*100)}% de réussite</div>
                  </div>
                  <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-5 flex flex-col gap-1">
                    <div className="font-serif text-3xl text-[#c05050]">{stats.unmatched}</div>
                    <div className="text-[9px] tracking-[0.2em] uppercase text-white font-mono">Sans correspondance</div>
                  </div>
                </div>
              )}

              {/* Filters */}
              {multiResults.length > 0 && (
                <div className="flex flex-col md:flex-row justify-between items-center bg-[#141210] p-3 rounded-[3px] border-1 border-[#2a2520] gap-4">
                  <div className="flex gap-2">
                    {[
                      { id: "all", label: "TOUS" },
                      { id: "matched", label: "MATCHÉS" },
                      { id: "unmatched", label: "NON TROUVÉS" }
                    ].map(t => (
                      <button
                        key={t.id}
                        onClick={() => setFilter(t.id)}
                        className={`text-[10px] tracking-[0.12em] uppercase p-[6px_14px] border-1 border-[#2a2520] bg-transparent transition-all rounded-[2px] font-mono ${filter === t.id ? 'bg-[#c9a84c] text-white border-[#c9a84c]' : 'text-white hover:text-[#d4c9b8] hover:border-[#5a5248]'}`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-4 w-full md:w-auto">
                    <input
                      type="text"
                      placeholder="Rechercher un produit…"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                      className="bg-[#181614] border-1 border-[#2a2520] rounded-[2px] p-[8px_14px] font-mono text-[11px] text-[#d4c9b8] outline-none transition-colors focus:border-[#8a6c2a] w-full md:w-[280px]"
                    />
                    <div className="text-[9px] text-white tabular-nums font-mono whitespace-nowrap">
                      {filteredMulti.length} ÉLÉMENTS
                    </div>
                  </div>
                </div>
              )}

              {/* Grid */}
              {multiResults.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {filteredMulti.map((item) => (
                    <MultiSiteResultCard key={item.product?.id} item={item} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-20 border-1 border-dashed border-[#2a2520] rounded-[4px] text-white">
                  <div className="text-2xl mb-2 opacity-30">🔍</div>
                  <div className="text-[10px] tracking-[0.1em] uppercase font-mono">Aucun résultat correspondant</div>
                </div>
              )}
              {multiResults.length > 0 && Object.keys(multiErrors).length > 0 && (
                <div className="bg-[#141210] border-1 border-[#2a2520] rounded-[3px] p-4">
                  <div className="text-[10px] tracking-[0.1em] uppercase text-[#c9a84c] font-mono mb-2">Erreurs collectées par site</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(multiErrors).map(([site, errs]) => (
                      <div key={site} className="text-[10px] text-white font-mono bg-[#181614] border-1 border-[#2a2520] rounded-[2px] p-2">
                        <span className="text-[#e8dcc8]">{site}</span> : {Array.isArray(errs) ? errs.length : 0}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty Global State */}
          {multiResults.length === 0 && !loading.multi && activeSection === "results" && (
            <div className="flex flex-col items-center justify-center py-32 text-center fade-up">
              <div className="w-20 h-20 bg-[#181614] rounded-full flex items-center justify-center mb-6 border-1 border-[#2a2520] text-3xl font-serif italic text-[#c9a84c] shadow-2xl pulse">
                ?
              </div>
              <h2 className="font-serif text-xl text-[#e8dcc8] mb-2 font-semibold">Aucune donnée de matching</h2>
              <p className="text-[11px] text-white max-w-[280px] font-mono leading-relaxed lowercase">
                veuillez compléter les étapes 01 à 02 pour générer le rapport des correspondances.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <Toast
          msg={toast.msg}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}
