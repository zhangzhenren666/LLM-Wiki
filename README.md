# Wiki Knowledge Management System

A Markdown-based knowledge management system inspired by the LLM-Wiki concept. It supports managing knowledge pages, directories, tags, page relationships, a knowledge graph, and basic search.

> Phase 1 focuses exclusively on Wiki knowledge management. Agent workflows are out of scope.

## Technology Stack

| Module | Technology |
| --- | --- |
| Frontend | Next.js + React + TypeScript + App Router + Tailwind CSS |
| Frontend Engineering | Monorepo (pnpm workspace) |
| Backend | Python + FastAPI + Uvicorn + Pydantic |
| Database | SQLite in Phase 1, with the option to migrate to PostgreSQL later |
| Knowledge Content | Markdown |
| Deployment | Docker Compose |

## Directory Structure

```text
llm-wiki/
├── frontend/                 # Frontend monorepo
│   ├── apps/wiki-web/        # Next.js application
│   ├── packages/ui/          # UI component library
│   ├── packages/types/       # Shared types
│   ├── packages/config/      # Shared configuration
│   ├── package.json
│   └── pnpm-workspace.yaml
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
└── dev-prompts/              # Development-stage prompts
```

## Requirements

- Node.js 22.x
- Python 3.11.x
- pnpm 9.x

## Getting Started

> Install dependencies the first time you set up the project, and whenever `requirements.txt` or `package.json` changes. See the relevant sections below.

### Backend

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 2. Install backend dependencies (including packages such as cryptography)
pip install -r requirements.txt

# 3. Copy the configuration template and configure the API key encryption secret
cp .env.example .env
# On Windows: copy .env.example .env

# Edit .env and set MODEL_API_KEY_SECRET=<a-long-random-string>

# 4. Create/update the database schema by running migrations
# Run this on first startup and after pulling code that includes new migrations.
# If you already have wiki.db, make sure it is migrated to the latest revision.
# Otherwise, newly added tables (such as model_config and document_task) may be missing.
alembic upgrade head

# 5. Start the backend
uvicorn app.main:app --reload --port 9001
```

- Health check: http://localhost:9001/health
- API documentation: http://localhost:9001/docs

### Frontend

```bash
cd frontend

# 1. Install frontend dependencies
pnpm install

# 2. Copy the frontend configuration template
cp apps/wiki-web/.env.example apps/wiki-web/.env.local
# On Windows, use: copy apps\wiki-web\.env.example apps\wiki-web\.env.local

# 3. Start the development server
pnpm dev
# Equivalent to: pnpm --filter @wiki/web dev
```

- Application URL: http://localhost:3000
- The frontend uses `NEXT_PUBLIC_API_BASE_URL` to connect to the backend. The default is `http://localhost:8000`. If the backend is running on port `9001`, set this variable to `http://localhost:9001` in `.env.local`.

## Configuration

Copy the environment-variable template files and update them as needed:

```bash
cp backend/.env.example backend/.env
cp frontend/apps/wiki-web/.env.example frontend/apps/wiki-web/.env.local
```

Key settings:

| File | Setting | Description |
| --- | --- | --- |
| Backend `.env` | `DATABASE_URL` | Database connection URL. Defaults to `sqlite:///./wiki.db`. |
| Backend `.env` | `MODEL_API_KEY_SECRET` | **Encryption secret for model API keys.** Must be set to a sufficiently random, long value in production. If omitted, the backend derives a value from `JWT_SECRET` for development and testing convenience only. |
| Frontend `.env.local` | `NEXT_PUBLIC_API_BASE_URL` | Base URL of the backend API. Defaults to `http://localhost:8000`. |

> Model settings—including API Base URL, API Key, model name, timeout, enabled/disabled status, and default configuration—can be managed from **Settings → Model Configuration** in the application. API keys are encrypted at rest; API responses and logs do not expose plaintext keys.

## Tests

### Backend

```bash
cd backend
python -m pytest
```

### Frontend (Type Checking and Build)

```bash
cd frontend
pnpm typecheck   # Type-check all packages
pnpm build       # Production build; equivalent to pnpm --filter @wiki/web build
pnpm lint        # ESLint
```

## Development Progress

- [x] Phase 1: Project initialization
- [x] Phase 2: Engineering conventions
- [x] Phase 3: Database and data models
- [x] Phase 4: Backend CRUD for knowledge management
- [ ] Subsequent phases: proceed in the order defined in `dev-prompts`
