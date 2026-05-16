# Yojana AI — Backend

FastAPI backend for the Yojana AI Government Schemes Advisor.

## Setup

```bash
# Install dependencies
uv sync

# Copy and fill in env vars
cp ../.env.example .env
```

## Database setup

```bash
# Start local Postgres with pgvector (from repo root)
docker compose up -d postgres

# Apply migrations
uv run alembic upgrade head

# Smoke-test schema (inserts a fake scheme and rolls back)
uv run python ../scripts/verify_db.py
```

## Data ingestion

```bash
# Ingest schemes (requires GEMINI_API_KEY + running Postgres)
uv run python ../scripts/ingest.py \
    --input ../data/raw/myscheme/schemes.jsonl \
           ../data/raw/myscheme_karnataka/schemes.jsonl \
    --rpm-limit 10 --concurrency 5

# Verify ingestion
uv run python ../scripts/verify_ingestion.py \
    --input ../data/raw/myscheme/schemes.jsonl \
           ../data/raw/myscheme_karnataka/schemes.jsonl
```

## Embedding pipeline

The embedding pipeline uses `gemini-embedding-001` with Matryoshka truncation to 768 dims. Stored vectors are L2-normalized so cosine similarity equals dot product.

**Index strategy**: at ≤1K rows, PostgreSQL sequential scan (~2ms) outperforms IVFFlat. The IVFFlat index was dropped in migration `9f6d52af2977`. When the scheme count exceeds ~1 000, rebuild as HNSW:
```sql
CREATE INDEX idx_schemes_embedding ON schemes
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

```bash
# Step 1: rebuild search_text to include eligibility summaries (no Gemini calls)
uv run python ../scripts/embed.py refresh-search-text

# Step 2: embed all schemes that are missing embeddings (idempotent)
uv run python ../scripts/embed.py populate

# Re-embed everything (e.g., after changing search_text format)
uv run python ../scripts/embed.py populate --force

# Semantic search smoke test
uv run python ../scripts/embed.py search "schemes for small farmers in Karnataka" --top-k 10
uv run python ../scripts/embed.py search "widow pension" --level state --state Karnataka

# Retrieval quality eval (requires populated DB + GEMINI_API_KEY)
RUN_LIVE_RETRIEVAL=1 uv run python ../scripts/eval_retrieval.py
# Targets: Recall@5≥0.70, Recall@10≥0.85, MRR≥0.50
# Actual:  Recall@5=1.00, Recall@10=1.00, MRR=0.93
```

## Development

```bash
# Run development server
uv run uvicorn app.main:app --reload

# Lint
uv run ruff check .

# Type check
uv run mypy app/

# Run tests
uv run pytest
```
