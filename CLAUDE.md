# CLAUDE.md — Yojana AI

## Project Overview

Yojana AI is an AI-powered Government Schemes Advisor for Indian citizens. It uses hybrid retrieval (SQL filters + pgvector semantic search + Gemini reasoning) to match users with relevant government schemes from a curated database of ~300 schemes scraped from myScheme.gov.in and state portals. The system supports multilingual queries and structured eligibility matching.

---

## Tech Stack

| Layer       | Technology                                                                      |
|-------------|---------------------------------------------------------------------------------|
| Backend     | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, uv        |
| Database    | PostgreSQL 16 + pgvector extension                                              |
| LLM         | Google Gemini 2.5 Flash (`google-genai` SDK) + Instructor (structured output)  |
| Embeddings  | Gemini `gemini-embedding-001` (768-dim, Matryoshka truncation, L2-normalized)   |
| Frontend    | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, next-intl |
| Scraping    | httpx + selectolax (Playwright as fallback)                                     |
| Deploy      | Render (backend + DB), Vercel (frontend)                                        |

---

## Repo Structure

```
yojana-ai/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py        # FastAPI entrypoint
│   │   ├── core/          # config, settings, logging
│   │   ├── db/            # SQLAlchemy models, session
│   │   ├── api/           # route handlers
│   │   ├── services/      # business logic (matching, llm, embeddings)
│   │   └── schemas/       # Pydantic request/response schemas
│   ├── alembic/           # DB migrations
│   ├── tests/             # pytest test suite
│   └── pyproject.toml     # uv-managed deps + tool config
├── frontend/              # Next.js app (Phase 5)
├── scripts/               # one-off scraping, ingestion, seeding scripts
│   └── scrapers/
│       ├── schema.py      # RawScheme Pydantic model (shared)
│       ├── _common/       # Shared infrastructure (http, jsonl_writer, dump)
│       └── myscheme/      # myScheme.gov.in scraper
├── data/
│   ├── raw/               # raw scraped HTML/JSON (git-ignored)
│   └── processed/         # cleaned JSON ready for ingestion (git-ignored)
├── docs/                  # architecture & design docs
├── .env.example           # env var template
├── .gitignore
├── CLAUDE.md              # this file
└── README.md
```

---

## Conventions

**Python**
- Formatter: `black` (via `uv run black .`)
- Linter: `ruff` — selects E, F, I, UP, B, SIM; line-length 100
- Type checker: `mypy --strict`
- Async everywhere — all DB access, LLM calls, and service functions are `async`
- Type hints mandatory on all function signatures

**Naming**
- Python: `snake_case` for modules, functions, variables
- TypeScript: `camelCase` for variables/functions, `PascalCase` for components/types
- Files: `kebab-case`

**Secrets**
- All secrets via `.env` (loaded by pydantic-settings)
- Never commit `.env` — only `.env.example`

**Commits / PRs**
- N/A during active dev phase — no git commits or PRs until each phase is validated

---

## Phase Progress

- [x] **Phase 0** — Project Foundation (scaffolding, FastAPI health check, Alembic init) ✅
- [x] **Phase 1** — Database Schema & Migrations + Data Scraping (pgvector, scheme model, Alembic migrations, myScheme + Karnataka scraper) ✅
- [x] **Phase 2** — Embedding & Indexing ✅
  - [x] **Step 2.1** — LLM-powered eligibility rule extractor ✅
  - [x] **Step 2.2** — Batch ingestion pipeline (JSONL → Postgres) ✅
  - [x] **Step 2.3** — Gemini embeddings + pgvector + retrieval eval ✅
- [x] **Phase 3** — Hybrid Retrieval & LLM Matching (SQL + vector search + Gemini reasoning) ✅
- [x] **Phase 4** — API & Multilingual Backend ✅
  - [x] **Step 4.1** — Production-ready FastAPI skeleton (DI, middleware, logging, errors) ✅
  - [x] **Step 4.2** — Implement API endpoints (profiles, schemes, match) ✅
  - [x] **Step 4.3** — Multilingual support (detect, translate, localize) ✅
- [x] **Phase 5** — Deploy & Hardening (Render + Vercel deploy, rate limiting, observability) ✅
  - [x] **Step 5.1** — Next.js 15 + React 19 foundation ✅
  - [x] **Step 5.2** — Profile Wizard live ✅
  - [x] **Step 5.3** — Results scheme card layout ✅
  - [x] **Step 5.4** — Streaming Chat Interface ✅
  - [x] **Step 5.5** — i18n Polish ✅

---

## Phase 4 Summary ✅ (2026-05-13)

### Multilingual Support (Step 4.3)
- **Language Detection**: `detect_language` implemented using Unicode ranges (Devanagari for Hindi, Kannada block for Kannada) falling back to English. Accurate on test strings.
- **Query Translator**: `QueryTranslator` added to map native-language queries back to English for pgvector embedding lookup while leaving English queries unmolested via zero-call passthrough. 
- **Response Localization**: `LLMReranker` and `Match` pipelines altered to accept `language` parameters directly. `SYSTEM_PROMPT` instructs Gemini models to format final reasoning and explanation outputs natively into the target dialect.
- **Cost**: Zero additional costs for native English users. <$0.001 overhead for Hindi/Kannada queries (requires 1 extra minimal Gemini Flash translation prompt for the query, while the explanation prompt natively handles targeted outputs).
- **Tests**: 11 new tests added. Live testing against Gemini translated "किसानों के लिए योजनाएं" successfully.

---

## Phase 5 Summary ✅ (2026-05-13)

### Infrastructure & Aesthetics
- **Next.js 15 + React 19:** Fully updated frontend with standard-compliant TypeScript types.
- **shadcn/ui:** Core components installed (button, card, input, etc.) with default slate style.
- **next-intl:** Multilingual routing (en, hi, kn) configured with middleware and a robust i18n setup. All translations exist seamlessly.
- **Font Rendering:** `Noto Sans`, `Noto Sans Devanagari`, and `Noto Sans Kannada` fonts are correctly injected via Google Fonts in `layout.tsx` to handle scripts appropriately across routing.
- **SSE Streams:** Both the Chat Interface and `ExplanationPanel` heavily exploit backend `Match` stream capabilities via the `streamMatch` custom handler inside `frontend/src/lib/api/match.ts`.
- **Zustand State:** Complex profile states (Wizard + Query combinations) remain safe utilizing memory persisting.

### Known Limitations
- Stage-3 LLM explaining latency (~45s per query block) remains. Mitigated by allowing the user to read Stage 1 and Stage 2 matches quickly (~500ms load), letting explanations render asynchronously.

---

## Current State

Phase 6.1 complete. Docker image builds. render.yaml and vercel.json ready. Deployment guide in README. Steps 6.2 (demo seeding + README polish) and 6.3 (optional cron) remain.

---

## Post-deploy debt & Verification Issues
- **Resolved**: Backend match API crashes (500) due to missing scheme metadata on `SchemeResultItem`; match responses now hydrate metadata before schema validation.
- **Resolved**: Backend scheme list/detail API crashes (500) due to Pydantic v2 ORM validation; response schemas now use `from_attributes=True` and endpoints validate ORM objects explicitly.
- **Resolved**: Pytest integration tests failed with `asyncpg` concurrency `InterfaceError`s due to unsafe DB session/connection reuse; DB tests now use isolated connection-backed sessions with rollback.
- **Non-blocking**: `mypy` type checking fails with 20 errors regarding mismatched types and missing return annotations across backend services.
- **Non-blocking**: Frontend `tsc --noEmit` fails on generated `.next/types/**/*.ts` resolution, though the Next.js production build completes and type-checks successfully.
---

## How to Run

```bash
# Install dependencies
cd backend
uv sync

# Start local Postgres (from repo root)
docker compose up -d postgres

# Apply migrations
uv run alembic upgrade head

# Smoke-test schema
uv run python ../scripts/verify_db.py

# Run the development server
uv run uvicorn app.main:app --reload
# → http://localhost:8000/health  {"status": "ok"}
# → http://localhost:8000/docs    (Swagger UI)

# Match and explain (requires GEMINI_API_KEY)
uv run python ../scripts/match.py --profile-file ../data/test_profiles/farmer_karnataka.json --query "agricultural subsidy" --explain

# Benchmarking
uv run python ../scripts/bench_matching.py
uv run python ../scripts/eval_reranking.py
```
