# User Flows Design Documentation

This document defines the canonical user flows in this repository and maps each flow to frontend routes, backend APIs, data contracts, and validation points.

## Scope

Covered components:
- `frontend/` React SPA (user interaction surfaces)
- `frontend_server/` Django + DRF API (auth, character, simulation lifecycle, replay, invites)
- WebSocket live updates for simulation observation

Primary goal:
- Ensure the end-to-end flow works: login/register -> simulation selection/creation -> character creation/edit/drop -> simulation run/observe.

---

## Flow 1: Authentication and Session Lifecycle

### User story
As a user, I can register/login, stay authenticated across refreshes, and logout cleanly.

### Entry points
- `/register`
- `/login`

### APIs
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/token/refresh/`
- `GET /api/v1/auth/me/`
- `POST /api/v1/auth/logout/`

### Design
1. Register/login returns `{ access, refresh, user }`.
2. Frontend stores:
   - `access` in memory.
   - `refresh` in `localStorage`.
3. On app startup:
   - If refresh token exists, call refresh endpoint.
   - On success, fetch `/auth/me` and hydrate current user.
4. On any API 401:
   - `apiFetch` attempts one refresh retry automatically.
5. Logout:
   - Sends refresh token to `/auth/logout/`.
   - Clears access + refresh tokens locally.

### Failure handling
- Invalid credentials -> login page error banner.
- Expired/invalid refresh -> refresh token cleared; user remains unauthenticated.
- Protected routes redirect to `/login`.

---

## Flow 2: Dashboard and Simulation Discovery

### User story
As an authenticated user, I can open my dashboard and discover my simulations and characters.

### Route
- `/dashboard`

### APIs
- `GET /api/v1/simulations/mine/`
- `GET /api/v1/characters/`

### Design
1. Dashboard loads simulations + characters in parallel.
2. Simulation cards expose:
   - Observe -> `/simulate/:id`
   - Settings -> `/simulate/:id/settings`
3. Character cards show availability state:
   - `available`
   - `in_simulation`

### Notes
- This route is wrapped by `ProtectedRoute`.

---

## Flow 3: Create Simulation

### User story
As a user, I can create a new simulation world from a selected map and visibility mode.

### Route
- `/simulations/new`

### APIs
- `GET /api/v1/maps/`
- `POST /api/v1/simulations/`

### Request contract
`POST /simulations/`:
- `name` (required; `[A-Za-z0-9_-]+`)
- `map_id` (optional, defaults to `the_ville`)
- `visibility` (`private|public|shared`)
- `fork_from` (optional)

### Design
1. Fetch map catalog.
2. User selects map + visibility and provides simulation name.
3. On create success, navigate to `/simulate/:id`.
4. Backend creates admin membership for the creator.

---

## Flow 4: Character Authoring (Create/Edit)

### User story
As a user, I can author a character profile including profession/schedule/living context and edit it before dropping into a simulation.

### Routes
- `/characters`
- `/characters/new`
- `/characters/:id/edit`

### APIs
- `GET /api/v1/characters/`
- `POST /api/v1/characters/`
- `GET /api/v1/characters/:id/`
- `PATCH /api/v1/characters/:id/`
- `DELETE /api/v1/characters/:id/`

### Character fields
- `name`
- `age`
- `traits`
- `backstory`
- `currently` (occupation/current behavior context; e.g. doctor on clinic shift)
- `lifestyle` (routine style)
- `living_area` (where they live; e.g. `the_ville:maple_apartment_2b`)
- `daily_plan` (schedule constraints/tasks)
- `status`
- `simulation`

### Design constraints
- Character names are unique per owner.
- Characters in `in_simulation` state:
  - cannot be edited
  - cannot be deleted

---

## Flow 5: Drop Character into Simulation (Character -> Persona Projection)

### User story
As a simulation admin, I can drop one of my available characters into a simulation so it becomes an active agent persona.

### Route surface
- `/simulate/:id` (Admin toolbar -> "Drop Character")

### API
- `POST /api/v1/simulations/:id/drop/`

### Request contract
- `character_id` (required)

### Projection mapping
When dropping, backend creates `Persona` (idempotent per `simulation + name`) from `Character`:
- `name` -> `name`
- `traits` -> `innate`
- `backstory` -> `learned`
- `currently` -> `currently`
- `lifestyle` -> `lifestyle`
- `living_area` -> `living_area`
- `daily_plan` -> `daily_plan_req`
- plus derived first/last names and age

### Access rules
- Only simulation admins may drop.
- Character must belong to requesting user.
- Character must be `available`.

### State transition
- Character status becomes `in_simulation`.
- Character `simulation` FK set to selected simulation.

---

## Flow 6: Simulation Runtime Control

### User story
As a simulation admin, I can start/pause/resume a simulation.

### Route surface
- `/simulate/:id` (Admin toolbar)

### APIs
- `POST /api/v1/simulations/:id/start/`
- `POST /api/v1/simulations/:id/pause/`
- `POST /api/v1/simulations/:id/resume/`

### Rules
- Start requires at least one persona in simulation.
- Only admins can control runtime.
- Valid state transitions:
  - `pending|completed|failed -> running` (start)
  - `running -> paused`
  - `paused -> running`

---

## Flow 7: Observe Live Simulation

### User story
As a member/observer, I can watch agents and inspect details while simulation updates stream in.

### Route
- `/simulate/:id`

### APIs
- `GET /api/v1/simulations/:id/`
- `GET /api/v1/simulations/:id/agents/`
- `GET /api/v1/simulations/:id/agents/:agent_id/`

### WebSocket
- `ws://<host>/ws/simulations/:id/?token=<jwt>`

### Design
1. Load metadata + agents.
2. Subscribe to WS for step updates.
3. On WS update, refetch agents.
4. Fallback polling every 5s when disconnected.
5. Agent sidebar opens detail panel with:
   - action
   - chat partner
   - daily requirement list
   - recent concepts/memories

---

## Flow 8: Visibility, Collaboration, and Invites

### User story
As a simulation admin, I can control visibility and invite users. As an invitee, I can accept/decline.

### Routes
- `/simulate/:id/settings`
- `/invites`
- `/explore`

### APIs
- `PATCH /api/v1/simulations/:id/` (visibility)
- `GET/POST /api/v1/simulations/:id/members/`
- `DELETE /api/v1/simulations/:id/members/:user_id/`
- `GET /api/v1/invites/`
- `POST /api/v1/invites/:membership_id/accept/`
- `POST /api/v1/invites/:membership_id/decline/`
- `GET /api/v1/simulations/public/`

### Roles
- `admin`: full control
- `observer`: view-only access
- invite statuses: `invited`, `active`, `declined`

---

## Flow 9: Replay and Demo

### User story
As a user, I can replay historical movement states and inspect timeline progression.

### Routes
- `/simulate/:id/replay`
- `/demo`
- `/demo/:id`

### APIs
- `GET /api/v1/simulations/:id/replay/`
- `GET /api/v1/simulations/:id/replay/:step/`
- `GET /api/v1/demos/`
- `GET /api/v1/demos/:id/step/:step/`

### Design
- Replay converts persisted movement records into canvas agent coordinates.
- Demo viewer supports scrubbing + playback speed controls.

---

## End-to-End Sequence (Primary User Flow)

### Scenario
User logs in, creates simulation, creates doctor character with schedule/living info, edits profile, drops into simulation, starts sim, and observes agent behavior.

### Sequence
1. `POST /auth/login`
2. `GET /simulations/mine`, `GET /characters`
3. `POST /simulations`
4. `POST /characters`
5. `PATCH /characters/:id` (optional refinement)
6. `POST /simulations/:id/drop`
7. `POST /simulations/:id/start`
8. `GET /simulations/:id/agents` + WS step updates
9. Optional `POST /pause` / `POST /resume`

---

## Quality Gates for User Flow Correctness

Minimum validation set:
1. Auth register/login/refresh/logout works with token persistence.
2. Character create/edit/delete permissions and state guards work.
3. Drop creates persona with all mapped fields (`lifestyle`, `living_area`, `daily_plan_req`).
4. Start/pause/resume enforce role + state constraints.
5. Observe route renders agents and updates across poll/WS.
6. Broken route checks:
   - `/characters/:id/edit` must be resolvable.

---

## Data Model Notes (Flow-Critical)

- `SimulationMembership` is the source of truth for permissions.
- `Character` is user-authored pre-simulation profile.
- `Persona` is simulation runtime identity projected from `Character`.
- `EnvironmentState` and `MovementRecord` back live/replay positioning.

---

## Future Hardening Recommendations

1. Enforce strict token validation in `SimulationConsumer.connect` (currently permissive).
2. Add E2E browser tests (Playwright) for critical flow chain.
3. Add server-side validation for `living_area` format (optional schema by map).
4. Add audit logging for membership role changes and runtime controls.

