# Cloud Agents Starter Skill (Run + Test)

Use this skill for first-pass setup and execution in this repo.

## 1) Fast environment bootstrap

From repo root:

- Ensure env file exists:
  - `cp .env.example .env` (only if `.env` is missing)
- Install Python deps for Django API (`frontend_server`):
  - `python3 -m venv frontend_server/.venv`
  - `source frontend_server/.venv/bin/activate`
  - `pip install -r frontend_server/requirements.txt`
- Install Python deps for simulation engine tests (`backend_server`):
  - `python3 -m venv backend_server/.venv`
  - `source backend_server/.venv/bin/activate`
  - `pip install -r backend_server/requirements.txt`
- Install frontend deps:
  - `cd frontend && npm install`

Notes:

- `DJANGO_SECRET_KEY` must be set in `.env`; Django will fail fast if missing.
- If you do not need OpenAI, keep `LLM_PROVIDER=ollama` (default in `.env.example`).
- `OPENAI_API_KEY` is still required by some legacy backend imports; for local test-only flows use a dummy value like `OPENAI_API_KEY=test-key`.

## 2) Start app services (common Cloud-agent workflow)

### Option A: local dev servers (fast for code iteration)

Terminal 1 (Django API + SPA):

- `source frontend_server/.venv/bin/activate`
- `cd frontend_server`
- `python3 manage.py migrate`
- `python3 manage.py runserver 0.0.0.0:8000`

Terminal 2 (Vite frontend with proxy):

- `cd frontend`
- `npm run dev -- --host 0.0.0.0 --port 3000`

Open:

- UI: `http://localhost:3000`
- API root path examples: `http://localhost:8000/api/v1/simulations/`

### Option B: docker-compose (use when Redis/Postgres/Qdrant parity matters)

- `docker compose up --build`

Use this when validating websocket/group-broadcast behavior or DB integrations that rely on `redis`, `db`, or `qdrant` service networking.

## 3) Auth/login flows Cloud agents need immediately

The frontend expects JWT auth APIs at `/api/v1/auth/*`.

### API-first login smoke flow (copy/paste)

1. Register:
   - `curl -s -X POST http://localhost:8000/api/v1/auth/register/ -H "Content-Type: application/json" -d '{"username":"agent1","email":"agent1@example.com","password":"pass12345","password_confirm":"pass12345"}'`
2. Login:
   - `curl -s -X POST http://localhost:8000/api/v1/auth/login/ -H "Content-Type: application/json" -d '{"username":"agent1","password":"pass12345"}'`
3. Use access token against protected endpoint:
   - `curl -s http://localhost:8000/api/v1/characters/ -H "Authorization: Bearer <ACCESS_TOKEN_FROM_LOGIN>"`

### UI login smoke flow

1. Open `http://localhost:3000/register` and create a user.
2. Sign in at `http://localhost:3000/login`.
3. Confirm redirect to `/dashboard`.

## 4) Feature flags / config toggles / mocks

There is no dedicated feature-flag framework in this repo right now. Use env-driven toggles instead:

- LLM provider switch:
  - `LLM_PROVIDER=ollama` (default)
  - `LLM_PROVIDER=openai` (requires valid `OPENAI_API_KEY`)
- Model selection:
  - `LLM_MODEL=...`
  - `EMBEDDING_PROVIDER=...`
  - `EMBEDDING_MODEL=...`

Practical mock strategy for Cloud agents:

- For `backend_server` pytest, a dummy key works because tests inject `MockLLMProvider`.
- For quick local Django checks, keep `OPENAI_API_KEY=test-key` unless code path explicitly calls OpenAI.

## 5) Testing workflows by codebase area

Run only the section matching your change area.

### A) `frontend/` (React + Vite)

Minimum checks:

- `cd frontend && npm run lint`
- `cd frontend && npm run build`

Manual verification:

- Run Vite + Django (Section 2A), then validate the changed page in browser.
- If auth-sensitive UI changed, log in first and verify protected routes (`/dashboard`, `/simulations/new`, `/explore`, `/invites`).

### B) `frontend_server/` (Django API + data + auth)

Minimum checks:

- `source frontend_server/.venv/bin/activate`
- `cd frontend_server`
- `python3 manage.py check`
- `python3 manage.py migrate`
- `python3 manage.py test translator`

Targeted API smoke checks (faster than full test run when scoping bugfixes):

- `curl -s http://localhost:8000/api/v1/simulations/`
- `curl -s -X POST http://localhost:8000/api/v1/auth/login/ -H "Content-Type: application/json" -d '{"username":"agent1","password":"pass12345"}'`

Websocket note:

- Simulation websocket endpoint is `ws://<host>/ws/simulations/<sim_id>/?token=<jwt>`.
- Current consumer accepts connections without strict token checks; still use a token in tests for forward-compat behavior.

### C) `backend_server/` (simulation cognition/runtime modules)

Minimum checks:

- `source backend_server/.venv/bin/activate`
- `cd backend_server`
- `pytest tests/test_smoke.py`
- `pytest tests/test_perceive_retrieve.py tests/test_plan_reflect.py tests/test_execute_converse.py`

LLM safety for tests:

- If needed before pytest: `export OPENAI_API_KEY=test-key-for-testing`
- Tests use fixtures from `backend_server/conftest.py` and should not require live model access.

## 6) Common failure fixes (quick runbook)

- Django raises `DJANGO_SECRET_KEY environment variable is required`:
  - Ensure `.env` exists and contains `DJANGO_SECRET_KEY=...`.
- Frontend cannot reach API on local dev:
  - Confirm Vite is running on `3000` and Django on `8000` (Vite proxy points to `localhost:8000`).
- Auth endpoints return 401 for protected routes:
  - Re-run login and use fresh access token (access tokens are short-lived).
- Backend pytest import error from missing `OPENAI_API_KEY`:
  - `export OPENAI_API_KEY=test-key-for-testing` before running tests.

## 7) Keep this skill updated

Whenever you discover a repeatable trick while implementing or debugging:

1. Add the trick here in the closest section (`setup`, specific area workflow, or failure fixes).
2. Keep entries command-first and copy/paste friendly.
3. Prefer short "symptom -> fix" bullets over long prose.
4. Commit skill updates in the same PR as the code change that revealed the trick.
