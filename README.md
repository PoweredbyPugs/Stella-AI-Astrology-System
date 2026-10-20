# Stella — Unified Astrology & Divination MCP Server 🌙

**Repo:** [PoweredbyPugs/Stella-Astrological-System](https://github.com/PoweredbyPugs/Stella-Astrological-System)

Stella is a single Python MCP server that gives an AI assistant a complete astrological
practice: **89 tools** spanning ephemeris computation, Hellenistic and Vedic timing
techniques, cosmobiology, 9 Star Ki, the I Ching, a Neo4j knowledge graph built from
38 source texts, a three-axis chart reading generator, and a learning memory system
that gets smarter with every validated reading.

It is the reasoning layer of a three-part system:

```
┌──────────────────────────────────────────────────────────────┐
│  STELLA (this repo) — Python MCP server, stdio transport     │
│                                                              │
│  Timing: ZR · profections · Vimshottari dasha · transits     │
│  Ki: 9 Star Ki · Convergence Ki · Ki Changes · I Ching       │
│  Cosmobiology: midpoints · solar arcs · 90° dial             │
│  Synthesis: chart_reading · discover/reflect/recall          │
│  Autopoietic: self-creating readings                         │
└───────┬──────────────────┬──────────────────┬────────────────┘
        │ REST             │ Bolt             │ in-process
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌────────────────────┐
│ HELIOS        │  │ NEO4J         │  │ pyswisseph         │
│ Swiss Ephem.  │  │ knowledge     │  │ local Swiss        │
│ REST API      │  │ graph         │  │ Ephemeris calcs    │
│ (port 3000)   │  │ (bolt :7687)  │  │ (returns, VOC,     │
│ Node/Express  │  │ 10,741 nodes  │  │  elections, Ki)    │
└───────────────┘  └───────────────┘  └────────────────────┘
```

- **[Helios](https://github.com/PoweredbyPugs/Helios)** (private) — a stateless
  Node.js/Express server wrapping the Swiss Ephemeris (`sweph` npm). It computes natal
  charts (planets, houses, aspects, essential dignities, sect, depositor chains, lots),
  current sky data, profections, ZR, and transits, and stores charts as JSON. Stella
  bridges its endpoints as MCP tools and auto-discovers new ones via `/api-info`.
- **Neo4j** (optional) — the interpretation corpus: 10,741 nodes and 93,183
  relationships built from 38 astrological, hermetic, and divinatory texts. Stella
  degrades gracefully without it.
- **pyswisseph** — local ephemeris math for everything that doesn't need Helios:
  returns, progressions, eclipses, elections, VOC moons, ingresses, planetary hours,
  and the entire Ki stack.

## Quick Start

```bash
git clone https://github.com/PoweredbyPugs/Stella-Astrological-System.git stella
cd stella
bash setup.sh
```

`setup.sh` creates the venv, installs dependencies, optionally starts Neo4j
(`docker compose up -d`), and emits an MCP client config. Run
`./.venv/bin/python stella_doctor.py` any time to health-check Helios, Neo4j, and
API keys. See [SETUP.md](SETUP.md) for the manual path and troubleshooting.

Requires Python 3.11+. Helios must be reachable at `SWEPH_API_BASE` for chart
generation and current-sky tools; the native pyswisseph tools work without it.

---

## Tool Domains (89 tools)

The full catalog with per-tool descriptions lives in [TOOLS.md](TOOLS.md).

| Domain | Tools | What it covers |
|--------|-------|----------------|
| **Helios Bridge** | 8 | Current sky (moon, planets, aspects), natal chart generation, chart storage on Helios |
| **pyswisseph Native** | 10 | Transit timing/search, lunar & solar returns, progressions, elections, eclipses, ingresses, planetary hours, VOC moons |
| **Timing Techniques** | 7 | Profections, Zodiacal Releasing (L1–L5) + Brennan-style ZR reports, transits, essential dignity scoring |
| **Dasha & Timing Stack** | 3 | 5-level Vimshottari dasha, live nakshatra transit, and `get_timing_stack` — dasha + ZR + nakshatra + Ki in one call with cross-system resonance detection |
| **9 Star Ki & I Ching** | 6 | Natal Ki profile, cycles, narrative readings, hexagram casting (coins/yarrow), wisdom-text search |
| **Convergence Ki** | 3 | Experimental 5-level astronomical Ki: Jupiter synodic gate → year → month → day → hour, built on 15° gates and the −3 cascade |
| **Ki Changes** | 7 | "Mercury's reading" — Ki transitions rendered as I Ching hexagrams with changing lines and Wu Xing phase analysis, at every level from hour to the ~12-year synodic |
| **Midpoints & Cosmobiology** | 4 | Ebertin 90° dial: natal midpoint pictures, COSI interpretations, midpoint transits, solar arc directions |
| **Chart Reading** | 1 | `chart_reading` — the three-axis generator (see below) |
| **Knowledge Graph** | 4 | Semantic search and multi-layer placement interpretation over Neo4j |
| **Graph Traversal** | 14 | Depositor chains, receptions, aspect networks, rulership webs, synastry comparison, raw Cypher, narrative synthesis scaffolds |
| **Chart Storage** | 4 | Local chart persistence in `charts/` (with Helios fallback) |
| **Emergent Triad** | 5 | `discover` / `reflect` / `recall` / `validate` / `chart_memory_stats` |
| **Autopoietic** | 4 | Self-creating reading sessions (diverge/converge protocol) |
| **Sweph Passthroughs** | 9+ | Direct Helios endpoints: retrogrades, stations, ingresses, daily transits, moon-for-date — plus auto-discovery of anything new Helios exposes |

---

## The Emergent System ⚡

The heart of Stella: a self-organizing learning cycle.

- **`discover(name)`** — throws *all* techniques at a chart simultaneously (midpoint
  transits, solar arcs, tight transit aspects) and returns ranked findings with
  **convergence zones** — degree bins where multiple techniques pile up. Instead of
  asking "what are the midpoints?", let the chart tell you what's happening.
- **`reflect(name, content, ...)`** — stores a validated insight, prediction, or life
  event, tagged with the techniques and placements that produced it and a 1–5
  resonance rating.
- **`recall(name, ...)`** — searches the chart's accumulated insights before a new
  reading. Filter by type, technique, tag, rating, or text.
- **`validate(name, insight_id, confirmed)`** — confirms or invalidates predictions,
  adjusting per-technique weights. Reinforcement learning for astrology.
- **`chart_memory_stats(name)`** — the dashboard: technique rankings by average
  resonance, most-referenced placements, validation rates, tag cloud.

```
discover() → surfaces signal → reading generated
     ↓                              ↓
  reflect() ← stores what worked ← feedback
     ↓
  recall() → informs next reading → discover()
     ↓
  validate() → adjusts technique weights
```

Each reading starts smarter than the last. Memory lives in
`charts/memory/{name}.json` (gitignored — local to each instance).

---

## Chart Reading System

Every reading is a point in a three-axis space — **Type × Framework × Size** — and
every combination runs the full computation pipeline. See
[CHART_WORKFLOW.md](CHART_WORKFLOW.md) for the complete guide.

**Type** (the medium): `technical` · `narrative` · `poem` · `ki` · `cosmobiogram` · `autopoietic`

**Framework** (the lens): `psychological` · `deterministic` (GTEI) · `hellenistic` ·
`stoic` · `mythological` · `cosmobiological` · `ki` — mixable.

**Size**: `xs` (3–5 sentences) → `xl` (5–10+ pages), plus a temperature dial (1–10).

**Add-ons**: `+Midpoints`, `+Solar Arcs`, `+Sabian`, `+ZR`, `+Transits`, `+Ki`

Every reading computes: natal chart with lots, depositors, and sect → whole sign
houses → essential dignities → derivative houses (Pelletier) → profections → ZR
(Spirit + Fortune, peak periods) → transits → knowledge graph grounding.

**Key principle:** dignity score drives narrative weight. The strongest planet
dominates; a peregrine chart ruler means the ASC archetype is conditional.

**Narrative standard:** Oliver Sacks meets James Hillman, in a Joan Didion voice.
Clinical precision, archetypal depth, shadow named directly. Every paragraph
specific to THIS chart. No Hallmark cards.

### Autopoietic Readings

The `autopoietic` type is a self-creating reading: multiple biographically-blind
diverge passes across maximally distant frameworks, followed by converge passes that
extract only the claims that independently recur — repeating with descending
temperature until convergence produces nothing new. Protocol and lessons learned in
[AUTOPOIETIC.md](AUTOPOIETIC.md).

---

## The Timing Stack

`get_timing_stack` layers four independent timing systems over one moment and flags
where they agree:

1. **Vimshottari Dasha** — 5 levels (maha → prana) seeded from the natal Moon's
   nakshatra, 120-year lord cycle
2. **Zodiacal Releasing** — Spirit and Fortune, L1–L5, with peak periods and
   loosing-of-the-bond detection
3. **Nakshatra transit** — live Moon nakshatra, lord, and pada
4. **9 Star Ki** — all five levels of the current Ki cascade

When the same planetary signature surfaces in multiple systems at once, the stack
reports the resonance. Quick references: [docs/ZR_REFERENCE.md](docs/ZR_REFERENCE.md),
[docs/KI_REFERENCE.md](docs/KI_REFERENCE.md).

---

## The Ki Family

Three related systems, from traditional to experimental:

- **9 Star Ki** (`get_ki`, `get_ki_cycle`, `get_ki_reading`, `get_daily_ki`) — the
  traditional Lo Shu cascade. Year Ki turns at Lichun (~Feb 4), months at solar
  terms. The three numbers: **Essence** (invisible to self), **Emotion** (internal
  processing), **Life Path** (how the world sees you). `get_daily_ki` is the
  **authoritative** daily number.
- **Convergence Ki** (`get_convergence_ki_now`, `get_synodic_gate_now`,
  `get_natal_gates`) — an experimental astronomical reformulation: five nested
  levels driven by real bodies crossing the 15° mid-sign gates, from Jupiter's
  ~12-year synodic gate down to the Chinese double-hour, each level starting at its
  parent minus 3. Theory in `research/convergence-sockets.md`.
- **Ki Changes** (`get_ki_changes` and the `ki_change_*` family) — reads the
  *transitions* between Ki states as I Ching hexagrams with changing lines and
  Wu Xing phase relationships. The state is the trigram; the change is the reading.

---

## Cosmobiology

Ebertin's 90° dial, implemented natively: `get_midpoint_pictures` (natal pictures),
`get_midpoint_interpretation` (COSI delineations for 78 pairs),
`get_midpoint_transits` (transiting planets on natal midpoints), and
`get_solar_arcs` (directed midpoint contacts for timing). The `cosmobiogram` chart
type builds a full midpoint-centered analysis. Details in
[COSMOBIOLOGY.md](COSMOBIOLOGY.md).

---

## Knowledge Graph (38 texts, 10,741 nodes, 93,183 relationships)

Built by `build_graph.py` and the `graph/` ingestion scripts into Neo4j
(`docker compose up -d` starts a local instance). Sources span five layers:

- **Technical** — Brennan, Lehman, Hand, Ebertin
- **Psychological** — Sasportas, Pelletier, Greene
- **Archetypal** — Tarnas, Hillman, Moore, Coppock
- **Philosophical / Hermetic** — Agrippa's Three Books (1,356 chunks), Crowley's
  777 (plus `data/777-correspondences.json`, fully structured), Cosmos & Psyche
- **Divinatory** — Gnostic Book of Changes, Waite's Pictorial Key, Tao Te Ching

Query it with `knowledge_search` / `interpret_placement`, or traverse it
structurally with the 14 `graph_*` tools (depositor chains, receptions, rulership
webs, synastry, raw Cypher). Neo4j is optional — Stella runs without it, minus the
knowledge and graph tools.

---

## For AI Assistants (VA Guide)

1. **Generate the chart first:**
   `generate_chart name="person" date="YYYY-MM-DD" time="HH:MM" lat=.. lon=..`
2. **For a reading:** `chart_reading name="person" size="l" report_type="narrative" framework="psychological"`
3. **Before transit work, run `discover`** — it tells you where the signal is
   (tightest orbs, convergence zones) so you don't read everything with equal weight.
4. **Before any reading, run `recall`** — build on what's already been learned.
5. **After an insight lands, `reflect` it; when life confirms it, `validate` it.**

Key principles: dignity drives narrative · whole sign houses always · no cookbook
readings · shadow included · synthesis over summary · astrology is invisible
scaffolding — only the human portrait shows.

---

## File Structure

```
stella/
├── stella_server.py        # MCP server — all 89 tools (FastMCP, stdio)
├── stella_config.py        # Env/config resolution (.env aware)
├── stella_doctor.py        # Health checks + MCP client config output
├── ephemeris.py            # pyswisseph: returns, progressions, elections, eclipses…
├── ki.py / ki_reading.py   # 9 Star Ki calculation + narrative readings
├── ki_changes.py           # Ki transitions as hexagrams ("Mercury's reading")
├── convergence_ki.py       # Experimental astronomical Ki (15° gates)
├── dasha.py                # Vimshottari dasha + nakshatra transit
├── zr.py / zr_report.py    # Zodiacal Releasing + Brennan-style reports
├── voc.py                  # Void-of-course moon
├── midpoints.py            # 90° dial: pictures, transits, solar arcs
├── build_graph.py          # Neo4j knowledge graph builder
├── graph/                  # Ingestion, seeding, traversal, synthesis scripts
├── autopoietic/            # Self-creating reading framework config + sessions
├── charts/                 # Chart JSON + memory + readings (gitignored)
├── data/                   # Structured reference (777 correspondences, …)
├── texts/                  # Source texts (Waite tarot)
├── research/               # Theory: convergence sockets, Lo Shu harmonics, …
├── elections/              # 2026 electional data
├── synodic-cycles/         # Per-planet synodic cycle references
├── docs/                   # KI_REFERENCE.md, ZR_REFERENCE.md
├── setup.sh                # Automated setup
└── docker-compose.yml      # Neo4j container (optional)
```

Docs: [SETUP.md](SETUP.md) · [TOOLS.md](TOOLS.md) ·
[CHART_WORKFLOW.md](CHART_WORKFLOW.md) · [AUTOPOIETIC.md](AUTOPOIETIC.md) ·
[COSMOBIOLOGY.md](COSMOBIOLOGY.md) · [CHANGELOG.md](CHANGELOG.md)

---

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `SWEPH_API_BASE` | For chart/sky tools | `http://baratie:3000` | Helios REST API |
| `NEO4J_URI` | No | `bolt://localhost:7687` | Knowledge graph (optional) |
| `NEO4J_USER` | No | `neo4j` | Neo4j auth |
| `NEO4J_PASS` | No | `[REDACTED]` | Neo4j auth |
| `OPENAI_API_KEY` | No | — | Only for graph-ingestion embeddings |

Set them in a `.env` at the repo root (see `.env.example`) — `stella_config.py`
loads it at startup.

---

## Known Issues

- **ChromaDB broken on Python 3.14** — pydantic v1 incompatible. The `.ingest-venv`
  (Python 3.13) works for ingestion; all runtime queries route through Neo4j.
- **Poneglyph cron uses `convergence_ki` for day Ki** — should use `get_daily_ki`
  (traditional cascade). Pending update.

## Roadmap

- [x] Emergent pattern detection + learning memory (`discover`/`reflect`/`recall`/`validate`)
- [x] Vimshottari dasha + unified timing stack with resonance detection
- [x] Ki Changes — transitions as hexagrams, all five levels
- [x] Standalone midpoint pictures, midpoint transits, and solar arc tools
- [x] Autopoietic (self-creating) readings
- [x] Agrippa + Crowley 777 ingested (structured correspondences in `data/`)
- [ ] 777 correspondence lookup tool (reverse lookups by planet/tarot/colour)
- [ ] Sabian symbol lookup tool (automated, not manual)
- [ ] `discover` reads chart memory to weight findings
- [ ] Cross-chart pattern detection
- [ ] Temporal tracking (log predictions, check against events)
- [ ] Evolutionary Astrology framework
- [ ] Framework auto-detection from chart signatures
- [ ] Geomancy casting tool (rapid-tap or manual count)
- [ ] Seven Strings seed moment calculator (tiered election system)
- [ ] Ki boundaries by instant, not day — `ki_calendar` gives the whole boundary day to the
      period it opens; the strict rule is the Lichun / jie instant itself (e.g. Lichun 2026 is
      Feb 3, 3:01 pm New York, so a 9 am birth that day is still Ki 2025). Add an optional
      time-of-day to `ki_year_of` / `ki_month_of` and thread it through natal calculations
      when a birth time is known. Mirror the same in the octave app (`lib/ki/kimonths.ts`).

## Remote access (claude.ai from any device)

Stella's tools are also served over Streamable HTTP so claude.ai can use them as a
custom connector without the desktop app.

```
claude.ai ──HTTPS :443──▶ Tailscale Funnel (path mounts) ──▶ 127.0.0.1:8811  stella_http.py (fastmcp proxy, GitHub OAuth)
                                                        │ stdio, persistent child
                                                        ▼
                                                 stella_server.py  (unchanged; Hermes still spawns it directly)
```

- **Single source of truth.** `stella_http.py` is a *proxy*: it spawns `stella_server.py`
  and discovers its tools at runtime, so new tools appear automatically after a restart
  of the service. The stdio server and the Hermes/omi path are untouched.
- **Two venvs on purpose.** `stella_server.py` pins the official SDK (`mcp` 1.x) in
  `.venv`; the proxy needs `fastmcp` 4.x (`mcp` 2.x) and lives in `.venv-http`
  (`requirements-http.txt`). The proxy pins the backend to the classic handshake.
- **Auth.** `GitHubProvider` handles OAuth 2.1 + dynamic client registration (what
  claude.ai speaks); `stella_http_policy.LoginAllowlist` then admits only the GitHub
  logins in `STELLA_ALLOWED_GH_LOGINS`. The service refuses to start if any auth setting
  is missing. `STELLA_HTTP_DENY_TOOLS` (comma list, empty by default) hides/blocks named
  tools if you ever want fewer than all of them exposed.
- **Identity check.** Every `get_convergence_ki_now` payload carries a `build` block
  (git sha, code path, `loaded_at`); if a client ever shows stale behaviour, that block
  says which process answered.

Setup (once):
1. GitHub → Settings → Developer settings → OAuth Apps → New. Homepage
   `https://<magicdns>.ts.net`, callback `https://<magicdns>.ts.net/auth/callback`.
   Paste the client id/secret into `.env` (see `.env.example`).
2. `python3.14 -m venv .venv-http && .venv-http/bin/pip install -r requirements-http.txt`
3. Publish on **port 443** — claude.ai's connector fetcher never connected to a
   non-standard port (10000 was tried first and got "No server responded"). Port 443 can
   be shared with another site: mount only Stella's paths, each with the same path on the
   backend URL so Tailscale forwards it unstripped. Use `tailscale funnel`, not
   `tailscale serve` — `serve` on a Funnel port silently turns Funnel *off* for that port.
   ```
   for p in /mcp /.well-known/oauth-authorization-server /.well-known/oauth-protected-resource \
            /authorize /consent /register /token /auth/callback; do
     tailscale funnel --bg --https=443 --set-path $p http://127.0.0.1:8811$p
   done
   tailscale funnel status   # the 443 block must say "(Funnel on)"
   ```
   Persists across reboots. Remove one mount with `tailscale funnel --https=443 --set-path <path> off`.
4. `cp deploy/com.poweredbypugs.stella-http.plist ~/Library/LaunchAgents/ &&
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.poweredbypugs.stella-http.plist`
   Logs: `~/Library/Logs/stella-http.{log,err.log}`.
5. claude.ai → Settings → Connectors → Add custom connector → `https://<magicdns>.ts.net/mcp`.
   claude.ai seems to cache a failed probe per URL, so if a first attempt failed, change
   the URL rather than retrying it.

Operations: restart with `launchctl kickstart -k gui/$(id -u)/com.poweredbypugs.stella-http`
(also how new tools become visible). Rotate the GitHub secret by regenerating it in the
OAuth App, updating `.env`, and restarting. Tests: `.venv-http/bin/python -m pytest tests/test_stella_http.py`.

Local path note: the canonical checkout is `/Volumes/Shirahoshi/HermesNode/clawd/stella`;
`~/Documents/Projects/stella` is a symlink to it.
