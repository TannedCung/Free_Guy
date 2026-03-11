# PRD: Full-Stack Refactoring & Modernization of Free_Guy (Generative Agents)

## Introduction

Free_Guy is a multi-agent AI simulation based on the Stanford "Generative Agents: Interactive Simulacra of Human Behavior" paper. It simulates believable human behaviors using LLM-powered agents that inhabit a 2D tile-based world ("The Ville"), where they perceive, plan, reflect, converse, and act autonomously.

The codebase has drifted into a state of significant technical debt: Django 2.2 (EOL since 2022), hardcoded secrets, no proper packaging, wildcard imports, 105KB monolith files, no tests, and a frontend built entirely with inline JavaScript in Django templates. This refactoring effort will bring the project to production-readiness — secure, maintainable, and deployable — across all layers of the stack.

## Goals

- Eliminate all known security vulnerabilities (hardcoded secrets, disabled CSRF, exposed debug mode)
- Upgrade Django from 2.2 to 4.2 LTS with all dependencies modernized
- Replace Django template frontend with a React SPA (Vite + React + Phaser 3)
- Establish proper Python packaging with `pyproject.toml` for both backend and frontend server
- Build a provider-agnostic LLM abstraction layer (OpenAI, Ollama, Anthropic, Gemini, etc.)
- Decompose monolith files (`run_gpt_prompt.py`, `plan.py`) into maintainable modules
- Achieve meaningful test coverage for all cognitive modules and API endpoints
- Set up CI/CD pipeline with linting, type checking, and automated tests
- Migrate simulation metadata to PostgreSQL with proper Django models
- Improve Docker Compose setup for reliable production deployment

---

## User Stories

### Phase 1: Security Fixes & Environment Configuration

#### US-001: Extract secrets to environment variables
**Description:** As a deployer, I want all secrets loaded from environment variables so that credentials are never committed to source control.

**Acceptance Criteria:**
- [ ] Create `.env.example` with all required environment variables documented
- [ ] Django `SECRET_KEY` read from `DJANGO_SECRET_KEY` env var
- [ ] OpenAI API key read from env var (remove `utils.py` pattern)
- [ ] Database credentials read from env vars
- [ ] `python-dotenv` or `django-environ` used for local development
- [ ] `.env` added to `.gitignore`
- [ ] Application fails fast with clear error if required env vars are missing

#### US-002: Re-enable and configure CSRF protection
**Description:** As a security engineer, I want CSRF protection enabled so that the application is protected against cross-site request forgery attacks.

**Acceptance Criteria:**
- [ ] `CsrfViewMiddleware` uncommented and active in middleware stack
- [ ] CSRF tokens included in all POST forms
- [ ] API endpoints that need CSRF exemption use `@csrf_exempt` explicitly with justification comments
- [ ] Verify no forms break after enabling CSRF

#### US-003: Fix Django security settings
**Description:** As a deployer, I want proper security settings so the application is safe to expose to the internet.

**Acceptance Criteria:**
- [ ] `DEBUG` controlled by `DJANGO_DEBUG` env var, defaults to `False`
- [ ] `ALLOWED_HOSTS` populated from `DJANGO_ALLOWED_HOSTS` env var
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` set based on environment
- [ ] `X_FRAME_OPTIONS = 'DENY'`

#### US-004: Secure Docker Compose configuration
**Description:** As a deployer, I want Docker secrets managed properly so credentials aren't hardcoded in `docker-compose.yml`.

**Acceptance Criteria:**
- [ ] Database passwords reference `.env` file via `env_file` directive
- [ ] No hardcoded passwords in `docker-compose.yml`
- [ ] `.env.example` includes all Docker-related variables
- [ ] Health checks added for database and backend services
- [ ] Restart policies defined for all services

---

### Phase 2: Python Packaging & Dependency Modernization

#### US-005: Create proper Python package structure
**Description:** As a developer, I want proper Python packaging so that imports work reliably without `sys.path` hacks.

**Acceptance Criteria:**
- [ ] `pyproject.toml` created for `backend_server` with all dependencies
- [ ] `pyproject.toml` created for `frontend_server` with all dependencies
- [ ] All `sys.path.append(...)` calls removed (13+ files)
- [ ] Modules importable via standard Python package paths (e.g., `from persona.cognitive_modules.plan import ...`)
- [ ] `__init__.py` files added where needed
- [ ] Application runs successfully after packaging changes

#### US-006: Modernize and deduplicate dependencies
**Description:** As a developer, I want up-to-date, deduplicated dependencies so the project is secure and builds are reproducible.

**Acceptance Criteria:**
- [ ] All dependencies upgraded to latest compatible versions (numpy, pandas, scipy, scikit-learn, matplotlib, etc.)
- [ ] `sklearn==0.0` dummy package replaced with `scikit-learn`
- [ ] Duplicate dependencies between frontend/backend consolidated where shared
- [ ] `requirements.txt` files generated from `pyproject.toml` for Docker builds
- [ ] No known CVEs in dependency tree (verify with `pip-audit`)
- [ ] Application still functions correctly after all upgrades

#### US-007: Remove wildcard imports
**Description:** As a developer, I want explicit imports so that dependencies between modules are clear and IDE support works properly.

**Acceptance Criteria:**
- [ ] All `from module import *` replaced with explicit imports
- [ ] Each file imports only what it uses
- [ ] No circular import issues introduced
- [ ] All 13+ affected files updated (`reverie.py`, `views.py`, `persona.py`, cognitive modules, etc.)
- [ ] Application runs correctly after import changes

---

### Phase 3: Django 2.2 to 4.2 LTS Upgrade

#### US-008: Upgrade Django from 2.2 to 4.2 LTS
**Description:** As a developer, I want Django 4.2 LTS so the application receives security patches and has access to modern features.

**Acceptance Criteria:**
- [ ] Django upgraded incrementally: 2.2 -> 3.2 -> 4.2 (following official upgrade guides)
- [ ] All deprecated patterns updated (`url()` -> `path()`, `django.conf.urls` -> `django.urls`, etc.)
- [ ] `DEFAULT_AUTO_FIELD` set in settings
- [ ] `MIDDLEWARE` uses new-style middleware (not `MIDDLEWARE_CLASSES`)
- [ ] All migrations run successfully
- [ ] All views and URL routing work correctly
- [ ] Django admin accessible (if used)

#### US-009: Restructure Django settings for multi-environment support
**Description:** As a deployer, I want environment-specific settings so I can run the same codebase in development, staging, and production.

**Acceptance Criteria:**
- [ ] Settings split: `base.py`, `development.py`, `production.py`
- [ ] `DJANGO_SETTINGS_MODULE` env var selects the settings file
- [ ] Development settings enable debug toolbar, verbose logging
- [ ] Production settings enforce all security headers, use PostgreSQL
- [ ] Static file handling configured (whitenoise for production)

---

### Phase 4: Code Quality & Architecture Improvements

#### US-010: Decompose `run_gpt_prompt.py` into domain-specific modules
**Description:** As a developer, I want the 105KB prompt file broken into focused modules so that each prompt domain is independently maintainable.

**Acceptance Criteria:**
- [ ] `run_gpt_prompt.py` split into separate files by domain (e.g., `prompts/planning.py`, `prompts/conversation.py`, `prompts/reflection.py`, `prompts/perception.py`, `prompts/action.py`)
- [ ] Shared utilities extracted to `prompts/utils.py`
- [ ] Each new module is under 500 lines
- [ ] All imports updated across the codebase
- [ ] No functionality lost — all prompt functions callable from their new locations

#### US-011: Decompose `plan.py` and other large cognitive modules
**Description:** As a developer, I want large cognitive modules broken into smaller, focused functions so they are easier to understand and test.

**Acceptance Criteria:**
- [ ] `plan.py` (1056 lines) split into logical sub-modules (e.g., `daily_planning.py`, `hourly_planning.py`, `task_decomposition.py`)
- [ ] Functions longer than 100 lines refactored into smaller composable functions
- [ ] Each module has a clear single responsibility
- [ ] All calling code updated to use new module paths

#### US-012: Build provider-agnostic LLM abstraction layer
**Description:** As a developer, I want a unified LLM interface so that switching or adding providers (OpenAI, Anthropic, Ollama, Gemini) requires no changes to simulation logic.

**Acceptance Criteria:**
- [ ] Abstract `LLMProvider` base class/protocol defined with methods: `complete(prompt, **kwargs)`, `chat(messages, **kwargs)`, `embed(text)`
- [ ] `OpenAIProvider` implementation wrapping current OpenAI integration
- [ ] `OllamaProvider` implementation wrapping current Ollama integration
- [ ] Provider selection configurable via environment variable (`LLM_PROVIDER=openai`)
- [ ] Model selection configurable via environment variable (`LLM_MODEL=gpt-4`)
- [ ] All existing prompt functions migrated to use the abstraction layer
- [ ] Easy to add new providers by implementing the interface (documented in README)
- [ ] Embedding provider separately configurable from chat/completion provider

#### US-013: Add type hints across the codebase
**Description:** As a developer, I want type annotations so that IDEs provide better autocomplete and bugs are caught before runtime.

**Acceptance Criteria:**
- [ ] All public functions and methods have parameter and return type annotations
- [ ] Key data structures use `dataclasses` or `TypedDict` where appropriate
- [ ] `mypy` configuration added to `pyproject.toml`
- [ ] `mypy` passes with no errors on strict mode for new/modified code
- [ ] `Scratch`, `AssociativeMemory`, `SpatialMemory` classes fully typed

#### US-014: Fix error handling patterns
**Description:** As a developer, I want consistent error handling so that failures are diagnosable and don't silently corrupt state.

**Acceptance Criteria:**
- [ ] All bare `except:` clauses replaced with specific exception types
- [ ] Consistent pattern: functions raise exceptions on failure (not return `False`)
- [ ] Custom exception hierarchy created (`SimulationError`, `LLMError`, `MemoryError`, etc.)
- [ ] Structured logging added (Python `logging` module with levels)
- [ ] All `global_methods.py` bare excepts fixed

#### US-015: Remove dead code and unused files
**Description:** As a developer, I want dead code removed so the codebase is leaner and less confusing.

**Acceptance Criteria:**
- [ ] `defunct_run_gpt_prompt.py` deleted
- [ ] `main_script_old_dolores.html` deleted
- [ ] All commented-out code blocks reviewed and removed (or restored with justification)
- [ ] Unused imports removed from all files
- [ ] Old prompt template versions (v1/, v2/) archived or removed if superseded

---

### Phase 5: Frontend Modernization (React + Vite + Phaser 3)

#### US-016: Initialize React SPA with Vite
**Description:** As a frontend developer, I want a modern React app scaffolded with Vite so that we have fast builds, HMR, and a standard development experience.

**Acceptance Criteria:**
- [ ] New `frontend/` directory created at project root with Vite + React + TypeScript
- [ ] ESLint and Prettier configured
- [ ] Folder structure: `src/pages/`, `src/components/`, `src/hooks/`, `src/api/`, `src/game/`
- [ ] Development server runs on port 3000 with proxy to Django API
- [ ] Production build outputs static files

#### US-017: Implement landing page in React
**Description:** As a user, I want a modern landing page so I can understand the project and navigate to simulations.

**Acceptance Criteria:**
- [ ] Landing page recreated in React with same content as current `landing.html`
- [ ] Responsive design using a CSS framework (Tailwind CSS or similar)
- [ ] Navigation to simulation viewer and demo viewer
- [ ] Simulation creation/forking form
- [ ] Verify in browser that landing page renders correctly

#### US-018: Embed Phaser 3 game canvas in React component
**Description:** As a developer, I want Phaser 3 running inside a React component so that the game engine integrates cleanly with the React lifecycle.

**Acceptance Criteria:**
- [ ] Phaser 3 installed via npm (not CDN script tag)
- [ ] `<GameCanvas />` React component wraps Phaser game instance
- [ ] Phaser game initializes on component mount, destroys on unmount
- [ ] Game canvas resizes responsively within its container
- [ ] No memory leaks on component remount
- [ ] Verify in browser that game canvas renders the tile map

#### US-019: Migrate simulation viewer to React
**Description:** As a user, I want the live simulation viewer rebuilt in React so it has a modern, responsive UI with real-time updates.

**Acceptance Criteria:**
- [ ] Live simulation page uses `<GameCanvas />` component
- [ ] Agent sprites rendered and animated in Phaser canvas
- [ ] Sidebar or overlay shows agent state (current action, thoughts, conversations)
- [ ] Zoom/pan controls work
- [ ] Real-time updates from backend via WebSocket or polling
- [ ] Verify in browser that simulation viewer works end-to-end

#### US-020: Migrate demo/replay viewer to React
**Description:** As a user, I want the demo replay viewer rebuilt in React so I can watch pre-recorded simulations with playback controls.

**Acceptance Criteria:**
- [ ] Demo viewer page uses `<GameCanvas />` component
- [ ] Playback controls (play, pause, speed up, rewind, scrub timeline)
- [ ] Agent speech bubbles rendered correctly
- [ ] Time display showing current simulation time
- [ ] Verify in browser that demo replay works end-to-end

#### US-021: Build Django REST API for frontend
**Description:** As a frontend developer, I want a REST API so the React frontend can communicate with the Django backend without template rendering.

**Acceptance Criteria:**
- [ ] Django REST Framework installed and configured
- [ ] API endpoints: `GET /api/simulations/`, `POST /api/simulations/`, `GET /api/simulations/:id/state/`
- [ ] API endpoint for agent state: `GET /api/simulations/:id/agents/`
- [ ] API endpoint for demo data: `GET /api/demos/:id/step/:step/`
- [ ] CORS configured for frontend dev server origin
- [ ] Authentication via session or token (configurable)
- [ ] API responses use consistent JSON schema

#### US-022: Remove legacy Django templates and inline JS
**Description:** As a developer, I want legacy templates removed so there's a single source of truth for the frontend.

**Acceptance Criteria:**
- [ ] All Django template HTML files removed (after React migration verified)
- [ ] Inline JavaScript from templates migrated to React components
- [ ] Django configured to serve React build output for production
- [ ] Static file serving configured (Django serves API, React handles routing)
- [ ] No 404s or broken routes after migration

---

### Phase 6: Testing Infrastructure & CI/CD

#### US-023: Set up pytest with fixtures for simulation testing
**Description:** As a developer, I want a test framework so I can verify simulation logic without running the full server.

**Acceptance Criteria:**
- [ ] `pytest` configured in `pyproject.toml` with test discovery
- [ ] Fixtures for: mock LLM provider, sample persona, sample maze, sample memory
- [ ] `conftest.py` with shared fixtures at project root
- [ ] Tests run with `pytest` from project root
- [ ] At least one passing test to verify setup

#### US-024: Write unit tests for cognitive modules
**Description:** As a developer, I want unit tests for all cognitive modules so that refactoring doesn't break agent behavior.

**Acceptance Criteria:**
- [ ] Tests for `perceive.py` — agent perceives nearby events and objects
- [ ] Tests for `retrieve.py` — memory retrieval ranks by recency, relevance, importance
- [ ] Tests for `plan.py` — daily plan generation, hourly decomposition
- [ ] Tests for `reflect.py` — reflection triggers and insight generation
- [ ] Tests for `execute.py` — action execution and emoji assignment
- [ ] Tests for `converse.py` — conversation initiation and dialogue generation
- [ ] Each module has at least 3 test cases covering happy path and edge cases
- [ ] Tests use mocked LLM responses (no real API calls)

#### US-025: Write integration tests for API endpoints
**Description:** As a developer, I want API integration tests so that frontend-backend contracts are verified automatically.

**Acceptance Criteria:**
- [ ] Tests for all REST API endpoints defined in US-021
- [ ] Test simulation creation, state retrieval, agent listing
- [ ] Test demo step retrieval
- [ ] Tests use Django test client
- [ ] Database state cleaned between tests

#### US-026: Set up CI/CD pipeline
**Description:** As a developer, I want automated CI so that every push is validated for correctness.

**Acceptance Criteria:**
- [ ] GitHub Actions workflow created (`.github/workflows/ci.yml`)
- [ ] Pipeline runs: `ruff` lint, `mypy` type check, `pytest` tests
- [ ] Frontend pipeline: `eslint`, `tsc --noEmit`, `vitest`
- [ ] Pipeline runs on push to `main` and on all pull requests
- [ ] Pipeline fails on any lint error, type error, or test failure
- [ ] Badge added to README showing CI status

#### US-027: Configure linting and formatting
**Description:** As a developer, I want automated linting and formatting so code style is consistent across the team.

**Acceptance Criteria:**
- [ ] `ruff` configured in `pyproject.toml` for Python linting + formatting
- [ ] `ruff` rules include: import sorting, unused imports, bare excepts, type annotation enforcement
- [ ] Pre-commit hooks configured (`.pre-commit-config.yaml`) for ruff + mypy
- [ ] Frontend: ESLint + Prettier configured in `frontend/`
- [ ] All existing code passes linting (fix or add targeted ignores)

---

### Phase 7: Database Model Design & Migration

#### US-028: Design Django models for simulation metadata
**Description:** As a developer, I want simulation data stored in PostgreSQL so that querying, filtering, and managing simulations is reliable and efficient.

**Acceptance Criteria:**
- [ ] `Simulation` model: id, name, description, status, created_at, updated_at, config JSON
- [ ] `Agent` model: id, simulation FK, name, personality traits, current_location, status
- [ ] `SimulationStep` model: id, simulation FK, step_number, timestamp, world_state JSON
- [ ] `AgentMemory` model: id, agent FK, memory_type (event/thought/chat), content, importance_score, created_at
- [ ] `Conversation` model: id, simulation FK, participants M2M, started_at, transcript JSON
- [ ] Migrations generated and applied successfully
- [ ] Django admin registered for all models

#### US-029: Build data migration from JSON files to PostgreSQL
**Description:** As a developer, I want existing simulation data importable from JSON files so that historical simulations are preserved.

**Acceptance Criteria:**
- [ ] Management command: `python manage.py import_simulation <path_to_json_dir>`
- [ ] Imports agent personas, memory, spatial data, and simulation steps
- [ ] Handles all existing base simulation formats in `storage/`
- [ ] Idempotent — re-running doesn't duplicate data
- [ ] Progress bar or logging during import
- [ ] At least one base simulation successfully imported and viewable

#### US-030: Update simulation engine to read/write from database
**Description:** As a developer, I want the simulation engine (Reverie) to use the database so that simulation state is durable and queryable.

**Acceptance Criteria:**
- [ ] `reverie.py` saves simulation steps to database instead of (or in addition to) JSON files
- [ ] Agent state persisted to database after each simulation step
- [ ] Memory events written to `AgentMemory` model
- [ ] Conversations saved to `Conversation` model
- [ ] Simulation can be paused and resumed from database state
- [ ] JSON file export still available as a management command for backwards compatibility

---

## Functional Requirements

- FR-1: All secrets (API keys, DB passwords, Django secret key) must be loaded from environment variables
- FR-2: CSRF protection must be enabled on all non-API endpoints
- FR-3: Django must be version 4.2 LTS with all middleware modernized
- FR-4: All Python packages must use `pyproject.toml` — no bare `requirements.txt` as source of truth
- FR-5: No `sys.path.append()` calls anywhere in the codebase
- FR-6: No `from module import *` anywhere in the codebase
- FR-7: The LLM abstraction must support at minimum: OpenAI, Ollama, and be extensible via a provider interface
- FR-8: The React frontend must communicate with Django exclusively via REST API
- FR-9: Phaser 3 must be installed via npm, not loaded via CDN script tags
- FR-10: All public Python functions must have type annotations
- FR-11: CI pipeline must enforce lint, type check, and test pass on every PR
- FR-12: PostgreSQL must be the production database with proper Django ORM models
- FR-13: Docker Compose must support one-command startup (`docker compose up`) for the full stack
- FR-14: The simulation engine must be runnable without the frontend (headless mode)
- FR-15: All API endpoints must return consistent JSON response schemas

## Non-Goals

- **Mobile app or PWA** — this is a desktop browser experience only
- **User authentication/authorization system** — no multi-tenant user accounts in this phase
- **Kubernetes/cloud-native deployment** — Docker Compose is sufficient
- **Rewriting the simulation engine from scratch** — refactor and clean up, not rebuild
- **Changing the game map or adding new world content** — only the tech stack is modernized
- **Real-time multiplayer** — single-user simulation viewing only
- **Performance optimization of LLM calls** — beyond the scope of this refactoring (can be a follow-up)
- **Migrating away from Phaser 3** — Phaser remains the game engine, only the wrapper changes

## Design Considerations

- **React component hierarchy:** `App > Layout > [LandingPage | SimulationViewer | DemoViewer]`, with `GameCanvas` as a shared component used by both viewers
- **State management:** React Query (TanStack Query) for server state, React context for UI state — no Redux needed at this scale
- **Styling:** Tailwind CSS for utility-first styling, matching a clean developer-tool aesthetic
- **Phaser integration:** Use `useRef` + `useEffect` pattern to mount/unmount Phaser game instance within React lifecycle
- **API design:** RESTful with Django REST Framework, versioned at `/api/v1/`

## Technical Considerations

- **Django upgrade path:** Must follow 2.2 -> 3.2 -> 4.2 incrementally, running `python -Wa manage.py test` at each step to catch deprecation warnings
- **Phaser + React:** Phaser owns the canvas rendering; React owns the UI chrome. Communication via custom events or a shared state bridge
- **LLM abstraction:** Use Python `Protocol` (structural subtyping) rather than ABC for the provider interface — more Pythonic and doesn't force inheritance
- **Database migration:** Keep JSON file support as a fallback during transition; database becomes primary storage
- **Backwards compatibility:** The `reverie.py` CLI interface should continue to work for users who don't want the web UI
- **Monorepo structure:** After refactoring, the project root should have `backend/`, `frontend/`, `docker/`, `docs/` top-level directories

## Success Metrics

- Zero hardcoded secrets in the codebase (verified by `detect-secrets` scan)
- All dependencies have no known CVEs (`pip-audit` and `npm audit` pass clean)
- Django version is 4.2.x LTS
- React frontend renders simulation identically to current Django template version
- LLM provider switchable via single env var change without code modifications
- `mypy --strict` passes on all new/modified Python code
- Test coverage > 60% on cognitive modules
- CI pipeline passes in under 5 minutes
- `docker compose up` brings up the full stack with zero manual configuration beyond `.env`
- Existing simulation data (base_the_ville_*) importable and viewable after migration

## Open Questions

- Should we implement WebSocket for real-time simulation updates, or is polling sufficient for the first version?
- Should old prompt template versions (v1/, v2/) be archived in a separate branch or deleted entirely?
- Is there value in keeping the `path_tester` debug tool, or should it be removed as part of dead code cleanup?
- Should the LLM abstraction support streaming responses from the start, or can that be added later?
- What retention policy should apply to `AgentMemory` records in PostgreSQL (could grow very large)?
