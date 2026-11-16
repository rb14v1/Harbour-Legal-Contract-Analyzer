# Legal Contract Analyzer

A full-stack demo application for legal teams to upload contracts, extract
clauses automatically, and ask natural-language questions answered from the
contract text via retrieval-augmented generation (RAG).

Stack: React (Vite + TypeScript) frontend, Django 5 + Django REST Framework
backend, PostgreSQL (or SQLite in dev/test), JWT auth, and a set of
Azure-service abstractions that run against real Azure resources in
production or deterministic local stubs in dev/CI.

## Architecture: what's real vs. stubbed

Every external service integration lives in `backend/apps/common/` as a
small dual-path module. Each one calls the real Azure/OpenAI SDK when its
credentials are configured in `.env`, and otherwise falls back to a
deterministic, local, network-free stub with the *same function signature*
— callers never need to know or care which path is active.

| Service | Module | Real (prod) | Stub (dev/CI, default) |
|---|---|---|---|
| File storage | `blob_store.py` | Azure Blob Storage (`azure-storage-blob`) | Files written to/read from `MEDIA_ROOT/blob_stub/` on local disk |
| Document extraction | `document_intelligence.py` | Azure AI Document Intelligence, `prebuilt-document` model | Reads the uploaded text, splits it into paragraphs, and classifies every other paragraph into a clause type (termination/indemnification/payment/confidentiality/governing_law/limitation_of_liability) and a risk flag using a SHA256 hash of the paragraph text, so results are reproducible |
| Chat + embeddings | `ai.py` | Azure OpenAI (`AzureOpenAI` client), chat model `gpt-5.6-sol`, embedding model `text-embedding-3-large` (1536 dims) | Deterministic SHA256-seeded chat replies and 1536-dim embedding vectors (same input text -> same output, always) |
| Vector/hybrid search | `search_store.py` | Azure AI Search (`azure-search-documents`), index `contract_chunks` | An in-process in-memory list of `{id, vector, payload}` per index, with plain-Python cosine-similarity top-k search (no external deps, no persistence across process restarts) |

`USE_SQLITE` (see `.env.example`) controls the database only: `True` (the
default) runs on local SQLite, `False` runs on real Postgres. The four
Azure services above are configured **independently** of `USE_SQLITE` —
each stays stubbed until its own specific env vars are filled in, even when
`USE_SQLITE=False`. Postgres itself is always plain relational storage: no
pgvector extension, no vector columns. All embeddings/vector search go
through the Azure AI Search abstraction above.

Because the in-memory search index doesn't persist across process
restarts, `apps/contracts/apps.py`'s `ContractsConfig.ready()` rebuilds it
from the `ContractChunk` rows already in the database every time
`manage.py runserver` starts (only when search is in stub mode). This works
because stub embeddings are deterministic — regenerating them from the
stored chunk text is equivalent to having persisted the vectors.

## Data model

- `Contract` — title, counterparty, contract_type, effective/expiry dates, uploader, blob_path, status (uploaded/processing/processed/failed)
- `ContractClause` — one extracted clause per row (clause_type, text, page number, is_risky), produced by `document_intelligence`
- `ContractChunk` — the unit that gets embedded and pushed into the `contract_chunks` search index
- `ContractQuery` — a question + synthesized answer + the chunk ids retrieved to answer it; `contract=null` means "search across all contracts"

## Pipelines

1. **Upload** — `POST /api/contracts/upload/` (multipart file + metadata) stores the file via `blob_store.upload_document` and creates a `Contract` row (`status=uploaded`).
2. **Process** — `POST /api/contracts/{id}/process/` runs synchronously (no Celery): `document_intelligence.extract_contract` → `ContractClause` rows → paragraph-based chunking → `ai.generate_embedding` per chunk → `search_store.upsert_chunks` into index `contract_chunks` → `Contract.status = processed`.
3. **Ask a question** — `POST /api/queries/` embeds the question, runs `search_store.search` (optionally filtered to one `contract_id`), builds a prompt from the retrieved chunks, and calls `ai.chat_completion` to synthesize a cited answer. Saves a `ContractQuery` row with the retrieved chunk ids.

## API surface

- `/api/auth/register/`, `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/me/`
- `/api/contracts/` (list/create/retrieve/update/delete), `/api/contracts/upload/`, `/api/contracts/{id}/process/`, `/api/contracts/{id}/clauses/`
- `/api/clauses/?contract={id}` (flat clause listing)
- `/api/queries/` (`GET` history, `POST` to ask a question)

### Permissions

- `legal_reviewer` and `admin` can both create contracts and ask questions.
- Only `admin` can delete a contract (`IsAdminOrReadOnlyDelete` permission class).
- Query history is scoped **at the queryset level**, not just hidden in the serializer: a `legal_reviewer` only ever sees the questions *they* asked; `admin` sees every query across all users (`ContractQueryViewSet.get_queryset`).

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # already provided pre-filled for local dev
python manage.py migrate       # applies schema + idempotent seed data migration
python manage.py runserver
```

Runs on SQLite with everything stubbed by default (`USE_SQLITE=True`). To
run against real Postgres, set `USE_SQLITE=False` in `.env` (Postgres
connection details are already filled in for a local
`legal_contract_analyzer`/`legal_contract_analyzer` role+database on
`localhost:5432` — create that role/database first if it doesn't exist:
`CREATE USER legal_contract_analyzer WITH PASSWORD 'legal_contract_analyzer'; CREATE DATABASE legal_contract_analyzer OWNER legal_contract_analyzer;`).
Azure services stay stubbed independently as long as their own env vars are
blank.

### Tests

```bash
python manage.py test
```

Runs entirely under `USE_SQLITE=True` / fully-stubbed mode — zero network
calls, zero cost, fully reproducible. Covers models, auth, contract CRUD +
permissions, each `apps/common` stub module, and a true end-to-end pipeline
test (upload → extract → chunk/embed → index → search → AI answer).

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Reads the backend base URL from `VITE_API_BASE_URL` (`frontend/.env`,
defaults to `http://localhost:8000/api`). Pages: login/register, contract
list + upload + process action, contract detail (clauses + ask-a-question),
and cross-contract query history.

## Demo logins

Seeded by the idempotent data migration (`apps/contracts/migrations/0003_seed_data.py`):

| Email | Password | Role |
|---|---|---|
| `reviewer@legalcontracts.demo` | `DemoPass123!` | legal_reviewer |
| `admin@legalcontracts.demo` | `DemoPass123!` | admin |

Seed data includes 8 contracts (NDA, MSA, employment, lease, licensing, and
two vendor agreements, plus one "other"), spanning `processed`, `uploaded`,
and `failed` statuses, with clauses and chunks already populated for every
processed contract, plus 3 sample question/answer history rows — so the app
has data to explore immediately without uploading anything first.
