
# Free Guy — Reverie Pixel Town

[![CI](https://github.com/TannedCung/Free_Guy/actions/workflows/ci.yml/badge.svg)](https://github.com/TannedCung/Free_Guy/actions/workflows/ci.yml)

<p align="center" width="100%">
<img src="design-system/assets/cover.png" alt="Reverie Pixel Town" style="width: 80%; min-width: 300px; display: block; margin: auto;">
</p>

A web platform for running and watching **multi-agent LLM simulations** inside a retro pixel-art town. Agents powered by large language models (Ollama / OpenAI-compatible) live, work, and interact on a shared Phaser 3 tilemap — visible in real time through a React SPA.

Built on top of [Park et al. — Generative Agents (UIST '23)](https://arxiv.org/abs/2304.03442).

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite + Tailwind v4 + Phaser 3 |
| Backend | Django 4.2 + DRF + Django Channels (WebSocket) |
| Auth | django-allauth (Google / GitHub OAuth) + JWT httpOnly cookies |
| LLM runtime | Ollama (local) — swap for any OpenAI-compatible endpoint |
| Vector store | Qdrant |
| Database | PostgreSQL 12 |
| Cache / broker | Redis 7 |
| Reverse proxy | nginx (Docker) |
| Containerisation | docker-compose |

---

## Quick start

### Prerequisites

- Docker + Docker Compose v2
- An `.env` file in the project root (see below)

### 1. Create `.env`

```env
# Django
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Postgres
POSTGRES_USER=freeguy
POSTGRES_PASSWORD=freeguy
POSTGRES_DB=freeguy

# Optional: expose via ngrok or similar tunnel
# DJANGO_SITE_DOMAIN=your-tunnel.ngrok-free.dev
```

### 2. Start all services

```bash
docker compose up --build
```

The app is available at **http://localhost** (nginx on port 80).

### 3. Run database migrations and seed social auth

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py setup_social_auth \
  --google-client-id YOUR_GOOGLE_CLIENT_ID \
  --google-client-secret YOUR_GOOGLE_CLIENT_SECRET
```

### 4. Open the app

Navigate to [http://localhost](http://localhost), sign in with Google, and create your first simulation.

---

## Development

The Vite dev server runs inside the `frontend` container and proxies `/api` and `/accounts` to the Django backend. nginx routes all traffic so you only need one port (80).

```bash
# Rebuild after code changes
docker compose up --build --force-recreate frontend

# Watch Django logs
docker compose logs -f backend

# Run frontend unit tests (Vitest)
docker compose exec frontend npx vitest run
```

### Using an ngrok tunnel (OAuth from external URL)

1. Start ngrok: `ngrok http 80`
2. Set in `.env`:
   ```env
   DJANGO_SITE_DOMAIN=your-subdomain.ngrok-free.dev
   ```
3. Recreate the backend and run `setup_social_auth` again so the Django Sites framework picks up the new domain:
   ```bash
   docker compose up --force-recreate backend
   docker compose exec backend python manage.py setup_social_auth ...
   ```

---

## Project structure

```
Free_Guy/
├── frontend/               # React SPA (Vite)
│   ├── public/assets/      # symlink → frontend_server/static_dirs/assets
│   └── src/
│       ├── components/     # Header, Primitives, ...
│       ├── pages/          # LandingPage, Dashboard, SimulatePage, ...
│       └── game/           # Phaser 3 GameCanvas
├── frontend_server/        # Django project
│   ├── translator/         # DRF views, auth, agent API
│   ├── static_dirs/assets/ # Game assets (tilemap, tilesets, sprites)
│   └── templates/          # Django HTML templates (allauth overrides)
├── design-system/          # Design tokens + React primitives
├── nginx/nginx.conf        # Reverse proxy config
├── scripts/                # Utility / migration scripts
└── docker-compose.yml
```

---

## Authentication flow

1. User clicks **Sign in with Google** → `/api/v1/auth/social/google/`
2. Django-allauth handles the OAuth dance with Google
3. On success, `oauth_complete` view issues JWT tokens as **httpOnly cookies** (`access_token`, `refresh_token`) and destroys the allauth session
4. React reads auth state via `/api/v1/auth/me/` — no tokens stored in JS

---

## Game assets

Assets live in `frontend_server/static_dirs/assets/` and are symlinked into `frontend/public/assets/` for Vite. Inside Docker the symlink is broken (build context boundary), so `docker-compose.yml` mounts the real directory:

```yaml
volumes:
  - ./frontend_server/static_dirs/assets:/app/public/assets:ro
```

---

## Original research

This project is derived from the open-source release accompanying:

> **Generative Agents: Interactive Simulacra of Human Behavior**
> Joon Sung Park, Joseph C. O'Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, Michael S. Bernstein
> UIST 2023 — [arxiv.org/abs/2304.03442](https://arxiv.org/abs/2304.03442)

Game asset credits:
- Background art: [PixyMoon (@_PixyMoon\_)](https://twitter.com/_PixyMoon_)
- Furniture / interior: [LimeZu (@lime_px)](https://twitter.com/lime_px)
- Character sprites: [ぴぽ (@pipohi)](https://twitter.com/pipohi)
