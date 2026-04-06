# AGENTS.md

## Cursor Cloud specific instructions

### Architecture overview

This is a full-stack generative agents simulation platform with three main components:

| Component | Path | Tech | Dev command |
|---|---|---|---|
| **Frontend (React SPA)** | `frontend/` | React 19, Vite 7, TypeScript, Phaser 3 | `npm run dev` (port 3000) |
| **Frontend Server (Django API)** | `frontend_server/` | Django 4.2, DRF, Channels, SQLite (dev) | `.venv/bin/python manage.py runserver 0.0.0.0:8000` |
| **Backend Server (Simulation engine)** | `backend_server/` | Python, Django 2.2, OpenAI/Ollama | `python reverie.py` (CLI-based) |

### Virtual environments

The `frontend_server` and `backend_server` use **incompatible Django versions** (4.2 vs 2.2) and must use separate virtual environments:
- `frontend_server/.venv/` — Django 4.2, DRF, Channels, allauth
- `backend_server/.venv/` — Django 2.2, simulation engine

### Prerequisites for running services

- **Redis** must be running on localhost:6379 (Django Channels requires it). The Django settings reference hostname `redis`, so `/etc/hosts` must contain `127.0.0.1 redis`.
- **SQLite** is the default dev database (no DATABASE_URL needed). PostgreSQL is only required for docker-compose / production.
- A `.env` file must exist in the repo root with at least `DJANGO_SECRET_KEY` set. Copy from `.env.example`.

### Running Django (frontend_server)

```bash
cd frontend_server
DJANGO_ENV=development .venv/bin/python manage.py runserver 0.0.0.0:8000
```

Migrations: `.venv/bin/python manage.py migrate`

### Running Vite (frontend)

```bash
cd frontend
npx vite --host 0.0.0.0
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

### Lint / Test commands

See `.github/workflows/ci.yml` for the canonical CI checks. Key commands:

- **Backend server lint**: `cd backend_server && .venv/bin/ruff check .`
- **Backend server typecheck**: `cd backend_server && .venv/bin/mypy .`
- **Backend server tests**: `cd backend_server && .venv/bin/python -m pytest` (must use `python -m pytest`, not bare `pytest`, for correct module resolution)
- **Frontend server Django check**: `cd frontend_server && DJANGO_SECRET_KEY=... DJANGO_ENV=development .venv/bin/python manage.py check`
- **Frontend server tests**: `cd frontend_server && DJANGO_SECRET_KEY=... DJANGO_ENV=development .venv/bin/python manage.py test translator.tests`
- **Frontend lint**: `cd frontend && npx eslint .`
- **Frontend typecheck**: `cd frontend && npx tsc --noEmit`

### Known issues (pre-existing in repo)

- `backend_server/requirements.txt` has a dependency conflict: `aiosignal==1.3.2` is incompatible with `aiohttp==3.13.3` (requires `>=1.4.0`). Use `pip install --no-deps -r requirements.txt` as a workaround.
- Some `frontend_server` Django tests fail (12 failures) due to JWT authentication requirements on endpoints that tests call unauthenticated. This is a pre-existing issue.
- `backend_server/` mypy reports 1 error in `utils/qdrant_utils.py` (pre-existing).
- CI is failing on `main` due to `scikit-learn==1.8.0` requiring Python >=3.11 but CI uses Python 3.10.

### Package manager

Frontend uses **npm** (`package-lock.json` is present). Use `npm ci` to install.
