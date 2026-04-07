import React, { useState, useEffect } from 'react'

const API = "http://localhost:8000"

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
      <div className="text-[8px] tracking-[0.2em] uppercase text-[#5a5248] font-mono">{label}</div>
      <div className="aspect-square bg-[#0f0e0d] border-1 border-[#2a2520] rounded-[2px] overflow-hidden flex items-center justify-center relative">
        {!isEmpty && src && !err ? (
          <img src={src} alt={label} className="object-contain w-full h-full p-2" onError={() => setErr(true)} />
        ) : (
          <div className="flex flex-col items-center gap-[4px] text-[#5a5248]">
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
        <div className="flex items-center justify-center text-[#5a5248] text-sm mt-3.5">→</div>
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
          <div className="text-[9px] text-[#5a5248] max-w-[120px] text-right truncate" title={match.corniche_product_name}>
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
          <div className={`w-7 h-7 rounded-[2px] flex items-center justify-center text-[11px] flex-shrink-0 transition-all ${done ? 'bg-[#2d5a3d] border-1 border-[#4a9e6a] text-[#4a9e6a]' : 'bg-transparent border-1 border-[#2a2520] text-[#5a5248]'}`}>
            {done ? "✓" : num}
          </div>
          <span className="font-serif text-sm text-[#e8dcc8]">{title}</span>
        </div>
        {statusEl}
      </div>
      <div className="p-6">
        <p className="text-[11px] text-[#5a5248] mb-4 leading-[1.7] font-mono">{desc}</p>
        {actionEl}
      </div>
    </div>
  )
}

// ── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [fakeProducts, setFakeProducts]   = useState([])
  const [fakeScrapeStatus, setFakeScrapeStatus] = useState("idle")
  const [fakeScrapeCount, setFakeScrapeCount] = useState(0)
  const [scrapeStatus, setScrapeStatus]   = useState("idle")
  const [scrapeCount, setScrapeCount]     = useState(0)
  const [matches, setMatches]             = useState([])
  const [stats, setStats]                 = useState(null)
  const [threshold, setThreshold]         = useState(60)
  const [filter, setFilter]               = useState("all") // all | matched | unmatched
  const [search, setSearch]               = useState("")
  const [loading, setLoading]             = useState({ fake: false, match: false })
  const [toast, setToast]                 = useState(null)
  const [activeSection, setActiveSection] = useState("setup")

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
          setFakeProducts(data.products || [])
          showToast(`Analyse terminée — ${d.count} produits sans image trouvés`, "success")
        }
      } catch (err) {
        console.error("Polling error:", err)
      }
    }, 2000)
    return () => clearInterval(iv)
  }, [fakeScrapeStatus])

  // Polling scrape corniche
  useEffect(() => {
    if (scrapeStatus !== "running") return
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/scrape-status`)
        const d = await r.json()
        setScrapeStatus(d.status)
        setScrapeCount(d.images_count || 0)
        if (d.status === "done") {
          clearInterval(iv)
          showToast(`Scraping terminé — ${d.images_count} images téléchargées`, "success")
        }
      } catch (err) {
        console.error("Polling error:", err)
      }
    }, 2000)
    return () => clearInterval(iv)
  }, [scrapeStatus])

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

  const handleScrape = async () => {
    try {
      const r = await fetch(`${API}/api/scrape-corniche`, { method: "POST" })
      if (!r.ok) throw new Error()
      setScrapeStatus("running")
      showToast("Scraping en cours en arrière-plan…", "info")
    } catch {
      showToast("Erreur lors du lancement du scraping", "error")
    }
  }

  const handleMatch = async () => {
    setLoading(prev => ({ ...prev, match: true }))
    try {
      const r = await fetch(`${API}/api/match?threshold=${threshold}`)
      if (!r.ok) throw new Error()
      const d = await r.json()
      setMatches(d.matches || [])
      setStats({ total: d.total, matched: d.matched, unmatched: d.unmatched })
      setActiveSection("results")
      showToast(`Matching terminé : ${d.matched}/${d.total} produits reliés`, "success")
    } catch {
      showToast("Erreur lors du matching", "error")
    }
    setLoading(prev => ({ ...prev, match: false }))
  }

  const handleExport = () => {
    if (!matches.length) {
      showToast("Veuillez d'abord lancer le matching", "error")
      return
    }
    window.open(`${API}/api/export-csv`, "_blank")
  }

  const filtered = matches.filter(m => {
    if (filter === "matched" && m.status !== "matched") return false
    if (filter === "unmatched" && m.status !== "no_match") return false
    if (search && !m.cave_product_name.toLowerCase().includes(search.toLowerCase())) return false
    return true
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
          { id: "scrape",  num: "02", name: "Scraping Corniche", status: scrapeStatus === "done" ? `${scrapeCount} images` : scrapeStatus === "running" ? "En cours…" : "En attente" },
          { id: "match",   num: "03", name: "Matching & Seuil", status: matches.length ? `${matches.length} reliés` : "En attente" },
          { id: "results", num: "04", name: "Rapports & CSV",  status: stats ? `${stats.matched}/${stats.total} matchés` : "—" },
        ].map(s => (
          <div
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`p-[16px_24px] border-b-1 border-b-[#2a2520] cursor-pointer transition-colors relative hover:bg-[rgba(201,168,76,0.04)] ${activeSection === s.id ? 'bg-[rgba(201,168,76,0.07)] before:content-[""] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[2px] before:bg-[#c9a84c]' : ''}`}
          >
            <div className="text-[9px] tracking-[0.2em] uppercase text-[#5a5248] mb-1 font-mono">Étape {s.num}</div>
            <div className="text-xs text-[#e8dcc8] font-normal font-mono">{s.name}</div>
            <div className="text-[10px] mt-[3px] font-mono" style={{
              color: s.status === "En attente" ? "var(--muted)" :
                     s.status.includes("En cours") ? "var(--gold-dim)" : "var(--success-t)"
            }}>{s.status}</div>
          </div>
        ))}

        <div className="mt-auto p-[20px_24px] border-t-1 border-t-[#2a2520] text-[9px] tracking-[0.1em] uppercase text-[#5a5248] font-mono">
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
            {activeSection === "scrape"  && "Scraping du catalogue Corniche"}
            {activeSection === "match"   && "Algorithme de Matching Fuzzy"}
            {activeSection === "results" && "Analyse des Correspondances"}
          </span>
          <div className="flex items-center gap-4">
            {stats && (
              <button
                onClick={handleExport}
                className="bg-transparent border-1 border-[#c9a84c] text-[#c9a84c] text-[11px] tracking-[0.1em] uppercase p-[9px_20px] rounded-[2px] cursor-pointer transition-all hover:bg-[#c9a84c] hover:text-[#0d0c0b] disabled:opacity-30 font-mono"
              >
                ↓ EXPORTER CSV
              </button>
            )}
            <div className="flex items-center gap-1.5 text-[10px] text-[#5a5248] tracking-[0.1em] font-mono">
              <div className={`w-1.5 h-1.5 rounded-full ${fakeScrapeStatus === 'done' ? 'bg-[#4a9e6a]' : (fakeScrapeStatus === 'running' || scrapeStatus === 'running') ? '#c9a84c' : 'bg-[#2a2520]'}`} />
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

          {/* ───────────── SCRAPE ───────────── */}
          {activeSection === "scrape" && (
            <div className="flex flex-col gap-8 fade-up">
              <div className="flex items-center gap-3 text-[#2a2520] text-[9px] tracking-[0.3em] uppercase after:content-[''] after:flex-1 after:h-[1px] after:bg-[#2a2520] font-mono">
                Étape 02 — Collecte Corniche
              </div>

              <StepCard
                num="2"
                title="Extraction du catalogue d'images"
                desc="Le système va parcourir le site 'boissonlacorniche.com' pour récupérer les URLs des images et les titres des produits. Chaque image sera téléchargée localement pour un affichage plus fluide lors du matching."
                done={scrapeStatus === "done"}
                statusEl={scrapeStatus === "running" ? (
                  <span className="bg-[rgba(201,168,76,0.1)] text-[#c9a84c] border-1 border-[#8a6c2a] text-[9px] tracking-[1.5px] uppercase p-[2px_8px] rounded-[2px] font-mono inline-flex items-center gap-2">
                    <span className="flex gap-1">
                      <span className="w-1 h-1 bg-[#c9a84c] rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <span className="w-1 h-1 bg-[#c9a84c] rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <span className="w-1 h-1 bg-[#c9a84c] rounded-full animate-bounce" />
                    </span>
                    {scrapeCount} images capturées…
                  </span>
                ) : scrapeStatus === "done" && (
                  <span className="bg-[#2d5a3d] text-[#4a9e6a] border-1 border-[#3a7a50] text-[9px] tracking-[0.15em] uppercase p-[2px_8px] rounded-[2px] font-mono">
                    {scrapeCount} images en cache
                  </span>
                )}
                actionEl={
                  <button
                    onClick={handleScrape}
                    disabled={scrapeStatus === "running" || fakeProducts.length === 0}
                    className="bg-transparent border-1 border-[#c9a84c] text-[#c9a84c] text-[11px] tracking-[0.1em] uppercase p-[9px_20px] rounded-[2px] cursor-pointer transition-all hover:bg-[#c9a84c] hover:text-[#0d0c0b] disabled:opacity-30 disabled:cursor-not-allowed font-mono"
                  >
                    {scrapeStatus === "running" ? "Scraping actif" : scrapeStatus === "done" ? "Relancer le scraping" : "Lancer l'extraction"}
                  </button>
                }
              />
            </div>
          )}

          {/* ───────────── MATCH ───────────── */}
          {activeSection === "match" && (
            <div className="flex flex-col gap-8 fade-up">
              <div className="flex items-center gap-3 text-[#2a2520] text-[9px] tracking-[0.3em] uppercase after:content-[''] after:flex-1 after:h-[1px] after:bg-[#2a2520] font-mono">
                Étape 03 — Algorithme de Liaison
              </div>

              <StepCard
                num="3"
                title="Matching par similarité textuelle"
                desc="L'algorithme compare les noms des produits 'Cave Privée' avec ceux de 'Corniche'. Plus le seuil est élevé, plus le matching est strict. Un seuil de 65-70% est généralement idéal pour pallier les différences mineures de naming."
                done={matches.length > 0}
                statusEl={loading.match ? (
                  <span className="text-[10px] text-[#c9a84c] font-mono animate-pulse">Calcul des similarités…</span>
                ) : null}
                actionEl={
                  <div className="flex flex-col gap-6">
                    <div className="max-w-[320px]">
                      <div className="flex justify-between text-[9px] mb-3 font-mono tracking-widest text-[#5a5248] uppercase">
                        <span>Seuil de confiance</span>
                        <span className="text-[#c9a84c] font-bold">{threshold}%</span>
                      </div>
                      <input
                        type="range" min="40" max="95" value={threshold}
                        onChange={e => setThreshold(Number(e.target.value))}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <button
                        onClick={handleMatch}
                        disabled={loading.match || fakeProducts.length === 0 || scrapeStatus !== "done"}
                        className="bg-transparent border-1 border-[#c9a84c] text-[#c9a84c] text-[11px] tracking-[0.1em] uppercase p-[9px_20px] rounded-[2px] cursor-pointer transition-all hover:bg-[#c9a84c] hover:text-[#0d0c0b] disabled:opacity-30 disabled:cursor-not-allowed font-mono"
                      >
                        {loading.match ? "Calcul en cours…" : "Exécuter le matching"}
                      </button>
                    </div>
                  </div>
                }
              />
            </div>
          )}

          {/* ───────────── RESULTS ───────────── */}
          {activeSection === "results" && (
            <div className="flex flex-col gap-8 fade-up">
              <div className="flex items-center gap-3 text-[#2a2520] text-[9px] tracking-[0.3em] uppercase after:content-[''] after:flex-1 after:h-[1px] after:bg-[#2a2520] font-mono">
                Étape 04 — Revue des résultats
              </div>

              {/* Stats Bar */}
              {stats && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-5 flex flex-col gap-1">
                    <div className="font-serif text-3xl text-[#e8dcc8]">{stats.total}</div>
                    <div className="text-[9px] tracking-[0.2em] uppercase text-[#5a5248] font-mono">Produits Fake</div>
                  </div>
                  <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-5 flex flex-col gap-1">
                    <div className="font-serif text-3xl text-[#c9a84c]">{stats.matched}</div>
                    <div className="text-[9px] tracking-[0.2em] uppercase text-[#5a5248] font-mono">Matchs Trouvés</div>
                    <div className="text-[10px] text-[#8a6c2a] mt-1 font-mono">{Math.round(stats.matched/stats.total*100)}% de réussite</div>
                  </div>
                  <div className="bg-[#181614] border-1 border-[#2a2520] rounded-[3px] p-5 flex flex-col gap-1">
                    <div className="font-serif text-3xl text-[#c05050]">{stats.unmatched}</div>
                    <div className="text-[9px] tracking-[0.2em] uppercase text-[#5a5248] font-mono">Sans correspondance</div>
                  </div>
                </div>
              )}

              {/* Filters */}
              {matches.length > 0 && (
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
                        className={`text-[10px] tracking-[0.12em] uppercase p-[6px_14px] border-1 border-[#2a2520] bg-transparent transition-all rounded-[2px] font-mono ${filter === t.id ? 'bg-[#c9a84c] text-[#0d0c0b] border-[#c9a84c]' : 'text-[#5a5248] hover:text-[#d4c9b8] hover:border-[#5a5248]'}`}
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
                    <div className="text-[9px] text-[#5a5248] tabular-nums font-mono whitespace-nowrap">
                      {filtered.length} ÉLÉMENTS
                    </div>
                  </div>
                </div>
              )}

              {/* Grid */}
              {filtered.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {filtered.map((m) => (
                    <MatchCard key={m.cave_product_id} match={m} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-20 border-1 border-dashed border-[#2a2520] rounded-[4px] text-[#5a5248]">
                  <div className="text-2xl mb-2 opacity-30">🔍</div>
                  <div className="text-[10px] tracking-[0.1em] uppercase font-mono">Aucun résultat correspondant</div>
                </div>
              )}
            </div>
          )}

          {/* Empty Global State */}
          {matches.length === 0 && !loading.match && activeSection === "results" && (
            <div className="flex flex-col items-center justify-center py-32 text-center fade-up">
              <div className="w-20 h-20 bg-[#181614] rounded-full flex items-center justify-center mb-6 border-1 border-[#2a2520] text-3xl font-serif italic text-[#c9a84c] shadow-2xl pulse">
                ?
              </div>
              <h2 className="font-serif text-xl text-[#e8dcc8] mb-2 font-semibold">Aucune donnée de matching</h2>
              <p className="text-[11px] text-[#5a5248] max-w-[280px] font-mono leading-relaxed lowercase">
                veuillez compléter les étapes 01 à 03 pour générer le rapport des correspondances.
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
