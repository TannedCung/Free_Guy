# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is the **Generative Agents** research project (Stanford, Joon Sung Park et al.) — a two-service Python application simulating believable human behaviors in a virtual town called "Smallville". See `README.md` for full setup and simulation instructions.

### Services

| Service | Directory | Command | Port |
|---------|-----------|---------|------|
| Frontend (Django) | `frontend_server/` | `python manage.py runserver 0.0.0.0:8000` | 8000 |
| Backend (Reverie) | `backend_server/` | `python reverie.py` (interactive CLI) | N/A |

### Python environment

- **Python 3.9** is required (Django 2.2 is not compatible with Python 3.12+). The venv lives at `/workspace/venv`.
- Activate with: `source /workspace/venv/bin/activate`
- Both `backend_server/requirements.txt` and `frontend_server/requirements.txt` are installed into the same venv. The `typing-extensions` pin in requirements.txt conflicts with `openai==1.2.0`; the update script uses `--no-deps` then installs missing transitive dependencies separately.

### Running the frontend server

```
source /workspace/venv/bin/activate
cd /workspace/frontend_server
python manage.py runserver 0.0.0.0:8000
```

Verify at `http://localhost:8000/` — should show "Your environment server is up and running!"

### Running the backend simulation

The backend (`reverie.py`) is an interactive CLI that requires an **OpenAI API key** set in `backend_server/constant.py`. Without a valid key, only the frontend (landing, demo, replay) can be tested.

### Demo / Replay (no API key needed)

Pre-simulated data exists in `frontend_server/storage/` and `frontend_server/compressed_storage/`. To replay:
- `http://localhost:8000/replay/July1_the_ville_isabella_maria_klaus-step-3-20/1/`
- `http://localhost:8000/demo/July1_the_ville_isabella_maria_klaus-step-3-20/1/3/`

### Lint / Test / Build

- **Django system check:** `cd frontend_server && python manage.py check`
- **Django tests:** `cd frontend_server && python manage.py test`
- **No dedicated linter** is configured in the repo.
- **No build step** — the project runs directly from source.

### Gotchas

- The `docker-compose.yml` at the repo root is a stub/template with incorrect paths (`./backend` instead of `./backend_server`) and is not functional.
- `constant.py` (not `utils.py`) is the actual config file imported by backend code. The README mentions creating `utils.py`, but the codebase imports from `constant`.
- The `django-storages-redux` package emits a deprecation warning on every Django command — this is harmless.
