# AI-Powered Government Schemes Advisor

> Personalized scheme discovery for Indian citizens. Ask in English, Hindi, Kannada, get matches in seconds.

---

## What it does

Millions of Indian citizens miss out on crucial government benefits simply because they don't know what they qualify for or find the eligibility rules too complex to parse. This platform solves this by allowing users to describe their situation in their native language (English, Hindi, or Kannada) and instantly receive personalized, reasoning-backed scheme matches from a curated database of state and central programs.

## Demo

*(See `demo/` folder for screenshots and sample profiles)*

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│              AI-POWERED GOVERNMENT SCHEMES ADVISOR                  │
└─────────────────────────────────────────────────────────────────────┘

  USER INPUT
  ──────────
  "I'm a 35-year-old OBC farmer in Karnataka with 2 acres"
  (English / हिंदी / ಕನ್ನಡ)
           │
           ▼
  ┌─────────────────────────────────────────────────────┐
  │              Next.js 15 Frontend                    │
  │  ┌──────────┐  ┌─────────────┐  ┌───────────────┐   │
  │  │ Profile  │  │   Results   │  │     Chat      │   │
  │  │ Wizard   │  │   Page +    │  │  Interface    │   │
  │  │ (4-step) │  │ Explanation │  │  (SSE stream) │   │
  │  └──────────┘  └─────────────┘  └───────────────┘   │
  │  Zustand · TanStack Query · next-intl (EN/HI/KN)    │
  └────────────────────────┬────────────────────────────┘
                           │ REST + SSE
                           ▼
  ┌─────────────────────────────────────────────────────┐
  │              FastAPI Backend                        │
  │                                                     │
  │  POST /match          GET /match/stream             │
  │  POST /profiles       GET /schemes/{slug}           │
  │                                                     │
  │  ┌──────────────────────────────────────────────┐   │
  │  │           3-Stage Matching Pipeline          │   │
  │  │                                              │   │
  │  │  Stage 1: SQL Eligibility Filter             │   │
  │  │  ├─ Hard rules: age, income, state, caste    │   │
  │  │  ├─ AND/OR rule tree evaluation              │   │
  │  │  └─ PASS / FAIL / UNKNOWN per rule           │   │
  │  │              ↓ ~50ms, ~75% filtered          │   │
  │  │                                              │   │
  │  │  Stage 2: pgvector Semantic Search           │   │
  │  │  ├─ Gemini text-embedding-004 (768-dim)      │   │
  │  │  ├─ Cosine similarity on search_text         │   │
  │  │  └─ Combined score: 0.5×rule + 0.5×semantic  │   │
  │  │              ↓ ~100ms total                  │   │
  │  │                                              │   │
  │  │  Stage 3: Gemini 2.5 Flash Reasoning         │   │
  │  │  ├─ Re-ranks top 15 candidates               │   │
  │  │  ├─ Reads raw_eligibility_text               │   │
  │  │  ├─ Generates personalized explanations      │   │
  │  │  └─ Responds in user's language              │   │
  │  │              ↓ ~45s (streamed via SSE)       │   │
  │  └──────────────────────────────────────────────┘   │
  │                                                     │
  │  ┌─────────────────┐  ┌──────────────────────────┐  │
  │  │  Multilingual   │  │    Eligibility Extractor │  │
  │  │  Layer          │  │    (offline pipeline)    │  │
  │  │  ├─ Unicode     │  │    ├─ Gemini + Instructor│  │
  │  │  │  detection   │  │    ├─ Structured rules   │  │
  │  │  └─ Query       │  │    └─ Confidence scores  │  │
  │  │    translation  │  └──────────────────────────┘  │
  │  └─────────────────┘                                │
  └────────────────────┬────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  ┌──────────────────┐    ┌──────────────────────┐
  │   PostgreSQL 16  │    │    Gemini API        │
  │   + pgvector     │    │                      │
  │                  │    │  • gemini-2.5-flash  │
  │  334 schemes     │    │    (reasoning)       │
  │  1,763 rules     │    │  • text-embedding-   │
  │  768-dim embeds  │    │    004 (retrieval)   │
  │                  │    │                      │
  │  5 tables:       │    │  Instructor library  │
  │  schemes         │    │  for guaranteed      │
  │  eligibility_    │    │  structured output   │
  │  rules           │    └──────────────────────┘
  │  user_profiles   │
  │  scheme_matches  │
  │  translations    │
  └──────────────────┘

  DATA PIPELINE (one-time + weekly refresh)
  ─────────────────────────────────────────
  myScheme.gov.in API ──┐
  Karnataka Portal ─────┤──▶ Raw JSONL ──▶ Gemini Extractor ──▶ PostgreSQL
  (300 + 53 schemes)    │                  (eligibility rules)
                        └──▶ Gemini Embedder ──▶ pgvector index
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 15 + React 19 | App Router, SSR, SSE streaming |
| UI | Tailwind CSS + shadcn/ui | Design system |
| State | Zustand + TanStack Query | Client state + server state |
| i18n | next-intl | English / Hindi / Kannada |
| Backend | FastAPI + Python 3.12 | Async REST API + SSE |
| ORM | SQLAlchemy 2.0 async | Type-safe DB access |
| Migrations | Alembic | Schema versioning |
| Database | PostgreSQL 16 + pgvector | Schemes + vector embeddings |
| LLM | Gemini 2.5 Flash | Reasoning + extraction + translation |
| Embeddings | Gemini text-embedding-004 | 768-dim semantic vectors |
| Structured Output | Instructor | Guaranteed Pydantic from LLM |
| Package Manager | uv | Fast Python dependency management |
| Deploy (BE) | Render | Docker-based web service |
| Deploy (FE) | Vercel | Next.js native deployment |
| Deploy (DB) | Supabase | Managed PostgreSQL + pgvector |

---

## Key Engineering Highlights

**1. Three-Stage Hybrid Retrieval Pipeline**
Custom-built matching engine combining SQL rule evaluation (deterministic, fast), pgvector cosine similarity (semantic), and Gemini reasoning (nuanced). Each stage has a distinct role: Stage 1 eliminates 75%+ of schemes via hard eligibility rules in ~50ms. Stage 2 re-ranks survivors using 768-dim embeddings. Stage 3 generates personalized explanations by reasoning over raw eligibility text — recovering signal from the ~43% of rules that couldn't be structured.

**2. LLM-Powered Eligibility Extraction**
Government scheme eligibility is written in unstructured bureaucratic prose ("applicants must be small or marginal farmers belonging to SC/ST/OBC categories with annual income not exceeding ₹3,00,000"). Built a Gemini + Instructor pipeline that extracts structured rules with typed operators (eq/lte/between/in), confidence scores, and AND/OR logic groups. Validation layer catches hallucinations deterministically.

**3. UNKNOWN-Aware Rule Evaluation**
Most eligibility engines are binary (eligible/not eligible). This engine has three outcomes: PASS, FAIL, UNKNOWN. A scheme requiring caste_category isn't eliminated when the user hasn't provided that field — it's marked LIKELY_ELIGIBLE with the missing field surfaced to the user. This dramatically improves recall for users with incomplete profiles.

**4. SSE Streaming for Progressive UX**
Stage 3 reasoning takes ~45 seconds for 15 schemes. Instead of blocking, the SSE endpoint streams results in stages: scheme cards appear within 500ms (Stage 1), re-ranked within 1s (Stage 2), explanations populate progressively as Gemini generates each one. Both the Results page and Chat interface consume this stream.

**5. Multilingual Retrieval-Augmented Pipeline**
A user typing in Hindi ("किसानों के लिए योजनाएं") gets: Unicode script detection → English translation for retrieval (embeddings are English) → matching pipeline runs in English → Gemini generates explanations directly in Hindi. Zero extra API calls for English users.

---

## Project Structure

```
ai-powered-govt-schemes-advisor/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── api/           # route handlers
│   │   ├── core/          # config, settings, logging
│   │   ├── db/            # SQLAlchemy models, session
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   └── services/      # business logic (matching, llm, embeddings)
│   ├── alembic/           # DB migrations
│   ├── tests/             # pytest test suite
│   ├── Dockerfile         # Production backend container
│   └── pyproject.toml     # uv-managed deps + tool config
├── frontend/              # Next.js app
│   ├── src/
│   │   ├── app/           # App router, pages, API routes
│   │   ├── components/    # Reusable React components (shadcn/ui)
│   │   ├── hooks/         # Custom React hooks
│   │   ├── i18n/          # next-intl translations and config
│   │   └── lib/           # Utility functions, API clients, state
│   ├── public/            # Static assets
│   ├── package.json       # Node dependencies
│   ├── next.config.ts     # Next.js configuration
│   └── vercel.json        # Vercel deployment configuration
├── scripts/               # One-off scraping, ingestion, seeding scripts
├── data/                  # Raw and processed scheme data
├── docs/                  # Architecture & design docs
├── demo/                  # Sample profiles and screenshots
└── render.yaml            # Render deployment configuration
```

---

## Local Development

```bash
# 1. Clone and enter repo
git clone <repo-url>
cd ai-powered-govt-schemes-advisor

# 2. Copy env template and fill in values
cp .env.example backend/.env

# 3. Install backend deps
cd backend
uv sync

# 4. Start local Postgres (pgvector/pgvector:pg16)
docker compose up -d postgres

# 5. Apply DB migrations
uv run alembic upgrade head

# 6. Verify schema
uv run python ../scripts/verify_db.py

# 7. Start the API server
uv run uvicorn app.main:app --reload
# → http://localhost:8000/health
# → http://localhost:8000/docs
```

---

## Deployment

### Prerequisites
- Supabase account (free) — for PostgreSQL + pgvector
- Render account (free) — for backend
- Vercel account (free) — for frontend
- Gemini API key with billing enabled

### Step 1: Database (Supabase)
1. Create project at supabase.com
2. Copy the connection string from Settings → Database
3. Connection string format: `postgresql+asyncpg://postgres:[password]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres` (replace `aws-0-eu-central-1` with your actual host)
4. pgvector is pre-enabled on Supabase — no action needed
5. Run migrations: `cd backend && DATABASE_URL=<url> uv run alembic upgrade head`
6. Run data ingestion: `cd backend && DATABASE_URL=<url> uv run python ../scripts/ingest.py --input ../data/raw/myscheme/schemes.jsonl ../data/raw/myscheme_karnataka/schemes.jsonl`
7. Run embeddings: `cd backend && DATABASE_URL=<url> uv run python ../scripts/embed.py populate`

### Step 2: Backend (Render)
1. Connect GitHub repo to Render
2. New Web Service → select repo → Render detects `render.yaml` automatically
3. Set environment variables in Render dashboard:
   - `GEMINI_API_KEY` = your key
   - `DATABASE_URL` = Supabase connection string
4. Deploy — first deploy runs migrations automatically
5. Note your backend service URL for the frontend configuration.

### Step 3: Frontend (Vercel)
1. Import repo at vercel.com
2. Framework: Next.js (auto-detected)
3. Root directory: `frontend`
4. Environment variable: `NEXT_PUBLIC_API_URL` = `<your-backend-url>/api/v1`
5. Deploy

### Step 4: Update CORS
After getting your Vercel URL, update `CORS_ORIGINS` in Render environment variables:
`["https://<your-frontend-domain>.vercel.app", "http://localhost:3000"]`

---

## Data Pipeline

The project relies on a robust data ingestion pipeline designed to extract structured semantic data from messy government documents:

1. **Scraping:** Custom `httpx` + `selectolax` scrapers fetch raw HTML and JSON data from portals like `myScheme.gov.in`. The data is saved locally in JSONL format for reproducibility.
2. **Extraction:** A rigorous, offline pipeline utilizes Gemini via the `instructor` library to perform Named Entity Recognition. It maps the raw, unstructured eligibility criteria into strict Pydantic structures (e.g. `AgeRule`, `IncomeRule`).
3. **Embedding:** The `embed.py` script leverages Gemini's `text-embedding-004` to create dense vector representations of the scheme descriptions and rules.
4. **Ingestion:** Final clean JSON objects are parsed into SQLAlchemy ORM models and efficiently pushed into PostgreSQL using bulk inserts, readying them for hybrid retrieval.

---

## API Reference

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `/docs`

### Match schemes to a profile

```bash
curl -X POST http://localhost:8000/api/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "profile": {
      "age": 35,
      "state": "Karnataka",
      "is_farmer": true,
      "land_holding_acres": 2,
      "annual_income": 150000,
      "caste_category": "OBC"
    },
    "query": "agricultural subsidies",
    "explain": false
  }'
```

### Stream results with explanations

```bash
curl -N "http://localhost:8000/api/v1/match/stream\
?profile_id=<uuid>&query=farming+schemes&explain=true"
```

### Get scheme details

```bash
curl http://localhost:8000/api/v1/schemes/pm-kisan
```

---

## Known Limitations & Future Work

**Current limitations:**
- ~43% of eligibility rules are `custom` type (opaque criteria the LLM couldn't structure). Stage 3 partially compensates via raw text reasoning, but structured matching is more reliable.
- Stage 3 latency (~45s) is mitigated by SSE streaming but still noticeable in the chat interface.
- Semantic search recall is moderate (Recall @10 ~0.50) — limited by dataset size (334 schemes) and search_text content quality.
- Only 53 Karnataka state-specific schemes (limited public data availability).

**Future work:**
- Expand scheme coverage to 3,000+ schemes across all states
- Fine-tune embeddings on Indian government scheme domain
- Add scheme application status tracking
- Weekly re-scrape cron job (Phase 6.3)
- HNSW vector index when scheme count exceeds 1,000
- Expand multilingual support to Tamil, Telugu, Bengali
