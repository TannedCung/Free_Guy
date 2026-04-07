# User Flows Design Documentation

This document defines the canonical user flows in this repository and maps each flow to frontend routes, backend APIs, data contracts, and validation points.

## Scope

Covered components:
- `frontend/` React SPA (user interaction surfaces)
- `frontend_server/` Django + DRF API (auth, character, simulation lifecycle, replay, invites)
- WebSocket live updates for simulation observation

Primary goal:
- Ensure the end-to-end flow works: login/register → simulation selection/creation → character creation/edit/drop → simulation run/observe.

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
   - `access` in memory (`_accessToken` module var in `api/client.ts`).
   - `refresh` in `localStorage` (key: `ga_refresh_token`).
3. On app startup (`AuthContext.tsx` useEffect):
   - If refresh token exists, call refresh endpoint.
   - On success, fetch `/auth/me` and hydrate current user.
4. On any API 401:
   - `apiFetch` attempts one refresh retry automatically.
5. Logout:
   - Sends refresh token to `/auth/logout/`.
   - Clears access + refresh tokens locally.

### Failure handling
- Invalid credentials → login page error banner.
- Expired/invalid refresh → refresh token cleared; user remains unauthenticated.
- Protected routes (`ProtectedRoute` wrapper in `App.tsx`) redirect to `/login`.

---

## Flow 2: Dashboard and Simulation Discovery

### User story
As an authenticated user, I can open my dashboard and discover my simulations and characters.

### Route
- `/dashboard`

### APIs
- `GET /api/v1/simulations/mine/` — returns simulations where user has active membership
- `GET /api/v1/characters/` — returns user's characters

### Design
1. Dashboard (`DashboardPage.tsx`) loads simulations + characters in parallel.
2. Simulation cards expose:
   - Observe → `/simulate/:id`
   - Settings → `/simulate/:id/settings`
3. Character cards show availability state:
   - `available` (gray)
   - `in_simulation` (green, edit/delete disabled)

### Notes
- This route is wrapped by `ProtectedRoute`.
- `/simulations/mine/` only shows simulations the user has an active `SimulationMembership` for (not all simulations).

---

## Flow 3: Create Simulation

### User story
As a user, I can create a new simulation world from a selected map and visibility mode.

### Route
- `/simulations/new`

### APIs
- `GET /api/v1/maps/` — returns active maps (requires auth)
- `POST /api/v1/simulations/` — creates simulation

### Request contract
`POST /simulations/`:
- `name` (required; `[A-Za-z0-9_-]+`)
- `map_id` (optional, defaults to `the_ville`)
- `visibility` (`private|public|shared`)
- `fork_from` (optional)

### Design
1. `CreateSimulationPage.tsx` fetches map catalog on load.
2. User selects map + visibility and provides simulation name.
3. On create success, navigate to `/simulate/:id`.
4. Backend creates `SimulationMembership` (admin role, active status) for the creator.
5. Backend sets `owner` field on `Simulation` to the creating user.

### State after creation
- `Simulation.status = "pending"`
- `Simulation.owner = request.user`
- `SimulationMembership(user=creator, role=admin, status=active)` created

---

## Flow 4: Character Authoring (Create/Edit)

### User story
As a user, I can author a character profile including profession/schedule/living context and edit it before dropping into a simulation.

### Routes
- `/characters` — character list
- `/characters/new` — create character
- `/characters/:id/edit` — edit character

### APIs
- `GET /api/v1/characters/`
- `POST /api/v1/characters/`
- `GET /api/v1/characters/:id/`
- `PATCH /api/v1/characters/:id/`
- `DELETE /api/v1/characters/:id/`

### Character fields
| Field | Purpose | Example (doctor) |
|-------|---------|---------|
| `name` | Display name (unique per owner) | `Dr. Sarah Chen` |
| `age` | Age in years | `42` |
| `traits` | Personality traits (maps to `Persona.innate`) | `methodical, empathetic, detail-oriented` |
| `backstory` | Background story (maps to `Persona.learned`) | `Trained as physician, specializes in internal medicine` |
| `currently` | Current occupation/activity | `On shift at Oak Street Clinic` |
| `lifestyle` | Daily routine style | `Early riser, 6am runs, strong work-life balance` |
| `living_area` | Home location in simulation world | `the_ville:oak_street_apartment_4b` |
| `daily_plan` | Schedule/task list (maps to `Persona.daily_plan_req`) | `Rounds 7am, consults 10am, surgery consult 2pm` |
| `status` | `available` or `in_simulation` (read-only) | |
| `simulation` | FK to simulation when in use (read-only) | |

### Design constraints
- Character names are unique per owner (enforced by DB constraint + API validation).
- Characters in `in_simulation` state:
  - cannot be edited (API returns 400; `EditCharacterPage` shows read-only notice)
  - cannot be deleted (API returns 400; `CharactersPage` shows grayed-out button)
  - Edit/Delete controls are visually disabled in `CharactersPage`

### UX guards
- `CharactersPage`: Edit link is grayed/disabled when `status === 'in_simulation'`
- `EditCharacterPage`: Shows "Character is in a simulation" notice instead of form when status is `in_simulation`

---

## Flow 5: Drop Character into Simulation (Character → Persona Projection)

### User story
As a simulation admin, I can drop one of my available characters into a simulation so it becomes an active agent persona.

### Route surface
- `/simulate/:id` (Admin toolbar → "Drop Character" button)

### API
- `POST /api/v1/simulations/:id/drop/`

### Request contract
```json
{ "character_id": 42 }
```

### Projection mapping
When dropping, backend creates `Persona` (idempotent via `get_or_create` on `simulation + name`) from `Character`:

| Character field | → | Persona field |
|---|---|---|
| `name` | → | `name`, `first_name`, `last_name` (split) |
| `age` | → | `age` |
| `traits` | → | `innate` |
| `backstory` | → | `learned` |
| `currently` | → | `currently` |
| `lifestyle` | → | `lifestyle` |
| `living_area` | → | `living_area` |
| `daily_plan` | → | `daily_plan_req` |

### Access rules
- Only simulation admins (`SimulationMembership.role=admin`) may drop.
- Character must belong to requesting user.
- Character must have `status=available`.

### State transitions
- `Character.status` → `in_simulation`
- `Character.simulation` → FK to the target simulation
- `Persona` row created in `Simulation`

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

### State machine
```
pending/completed/failed → [start] → running
running → [pause] → paused
paused → [resume] → running
```

### Validation rules
- `start`: requires at least one persona in simulation; only admins; returns 409 if already running
- `pause`: requires `status=running`; returns 409 if not running
- `resume`: requires `status=paused`; returns 409 if not paused
- All three require admin role

### Admin check
Admin status is determined from `SimulationMembership`:
```python
SimulationMembership.objects.filter(
    simulation=sim, user=request.user,
    role=Role.ADMIN, status=MemberStatus.ACTIVE
).exists()
```

Frontend determines admin status by checking `sim.owner === user.id` (simplified check — sufficient since creator is always owner and admin).

---

## Flow 7: Observe Live Simulation

### User story
As a member/observer, I can watch agents and inspect details while simulation updates stream in.

### Route
- `/simulate/:id`

### APIs
- `GET /api/v1/simulations/:id/` — simulation metadata
- `GET /api/v1/simulations/:id/agents/` — list agents with positions
- `GET /api/v1/simulations/:id/agents/:agent_id/` — detailed agent state

### WebSocket
- `ws://<host>/ws/simulations/:id/?token=<jwt>`
- Handled by `SimulationConsumer` in `consumers.py`

### Design
1. Load metadata + agents on mount.
2. Subscribe to WS for step updates via `useSimulationWebSocket` hook.
3. On WS step update, refetch agents.
4. Fallback: poll agents every 5s when WS is disconnected.
5. Agent sidebar shows list of all agents.
6. Clicking agent opens detail panel (slide-in overlay) with:
   - `act_description` (current action)
   - `chatting_with` (conversation partner)
   - `daily_req` (today's plan)
   - `recent_concepts` (last 5 memory nodes)

### Agent detail fields exposed
- `innate`, `learned`, `lifestyle`, `living_area`, `daily_plan_req`
- `curr_time`, `act_description`, `daily_req`
- `chatting_with`
- `recent_concepts` (list of last 5 ConceptNode records)

---

## Flow 8: Visibility, Collaboration, and Invites

### User story
As a simulation admin, I can control visibility and invite users. As an invitee, I can accept/decline.

### Routes
- `/simulate/:id/settings` — simulation settings (admin only)
- `/invites` — pending invites
- `/explore` — browse public simulations

### APIs
- `PATCH /api/v1/simulations/:id/` — update visibility (admin) ⚠️ **Fixed in this session**
- `GET /api/v1/simulations/:id/members/` — list members
- `POST /api/v1/simulations/:id/members/` — invite user by username
- `DELETE /api/v1/simulations/:id/members/:user_id/` — remove member
- `GET /api/v1/invites/` — list pending invites
- `POST /api/v1/invites/:membership_id/accept/` — accept invite
- `POST /api/v1/invites/:membership_id/decline/` — decline invite
- `GET /api/v1/simulations/public/` — browse public simulations

### Bug fixed: PATCH /simulations/:id/ routing
Previously, `update_simulation` view existed in `simulation_views.py` but was not connected to any URL. `api_views.simulation_detail` only handled `GET`. Fixed by updating `simulation_detail` to handle both `GET` (public) and `PATCH` (authenticated admin). The `update_simulation` dead-code view in `simulation_views.py` remains but is superseded.

### Roles
- `admin`: full control (drop characters, start/pause/resume, invite/remove members, update visibility)
- `observer`: view-only access

### Invite statuses
- `invited` → `active` (accepted) or `declined`

---

## Flow 9: Replay and Demo

### User story
As a user, I can replay historical movement states and inspect timeline progression.

### Routes
- `/simulate/:id/replay` — replay historical steps
- `/demo` — list all available demos
- `/demo/:id` — watch a compressed demo

### APIs
- `GET /api/v1/simulations/:id/replay/` — replay metadata (step range)
- `GET /api/v1/simulations/:id/replay/:step/` — agent positions at step
- `GET /api/v1/demos/` — list available demos
- `GET /api/v1/demos/:id/step/:step/` — demo movement data at step

### Design
- Replay uses persisted `MovementRecord` rows for historical step data.
- Demo viewer uses `DemoMovement` rows (compressed from `MovementRecord`).
- Demo viewer supports scrubbing through steps.

---

## End-to-End Sequence (Primary User Flow)

### Scenario
User logs in, creates simulation, creates doctor character with schedule/living info, edits profile, drops into simulation, starts sim, and observes agent behavior.

### Sequence
```
1. POST /auth/login  or  POST /auth/register
   → Access token (memory) + refresh token (localStorage)

2. GET /simulations/mine  +  GET /characters
   → Dashboard with existing sims and chars

3. GET /maps/  +  POST /simulations/
   → Simulation created; admin membership auto-created

4. POST /characters/
   → Character created (name, age, traits, backstory, currently,
     lifestyle, living_area, daily_plan)

5. PATCH /characters/:id/  (optional refinement)
   → Character profile updated; only allowed when status=available

6. POST /simulations/:id/drop/  (character_id)
   → Persona created from character; Character status → in_simulation

7. POST /simulations/:id/start/
   → Simulation status → running; start_date set

8. GET /simulations/:id/agents/  + WS step updates
   → Live agent positions and actions visible

9. GET /simulations/:id/agents/:agent_id/
   → Detailed agent view (plan, memory, current action)

10. POST /simulations/:id/pause/  (optional)
    → Simulation status → paused

11. POST /simulations/:id/resume/  (optional)
    → Simulation status → running

12. PATCH /simulations/:id/  { visibility: "public" }
    → Simulation becomes discoverable via /explore
```

---

## Data Model Summary

### Core entities
| Model | Purpose |
|-------|---------|
| `User` | Django auth user |
| `Simulation` | A simulation world (name, status, owner, map, visibility) |
| `SimulationMembership` | User ↔ Simulation access (role: admin/observer; status: invited/active/declined) |
| `Character` | User-authored persona template (pre-simulation) |
| `Persona` | Active agent in a simulation (projected from Character) |
| `PersonaScratch` | Persona runtime state (position, schedule, action, chat) |
| `SpatialMemory` | Persona's mental map of the world |
| `ConceptNode` | Memory event/thought/chat entry for a persona |
| `KeywordStrength` | Keyword salience for a persona's memories |
| `EnvironmentState` | Agent positions at each step (written by frontend process_environment) |
| `MovementRecord` | Agent movements per step (written by backend reverie.py) |
| `Demo` | Compressed simulation replay |
| `DemoMovement` | Movement data per step in a demo |
| `Map` | Available simulation world maps |

### Key relationships
```
User ──owns──► Character ──(drop)──► Persona ──belongs to──► Simulation
User ──member──► SimulationMembership ──► Simulation
Persona ──has──► PersonaScratch (1:1)
Persona ──has──► SpatialMemory (1:1)
Persona ──has many──► ConceptNode
Simulation ──has many──► EnvironmentState (per step)
Simulation ──has many──► MovementRecord (per step)
```

---

## Quality Gates for User Flow Correctness

### Verified test coverage (71 tests total)

**Authentication**
- Register/login/refresh/logout all work with JWT tokens

**Character lifecycle**
- Create/edit/delete with all fields
- `in_simulation` state guard on edit and delete (API + frontend)
- `living_area` and `daily_plan` preserved through edit → drop

**Simulation lifecycle**
- Create with admin membership auto-created
- Fork from existing simulation (deep copy all persona data + Qdrant embeddings)
- PATCH visibility (fixed — now routed via `simulation_detail`)
- Start/pause/resume with state machine enforcement
- Cannot start without characters
- Cannot start if already running (409)
- Cannot pause if not running (409)

**Drop character → persona**
- All fields correctly projected (traits→innate, backstory→learned, etc.)
- Character status transitions to `in_simulation`
- Cannot drop same character twice
- Multiple characters coexist in same simulation

**Observation**
- Agents list returns correct persona data
- Agent detail returns plan, lifestyle, living_area, memory concepts
- Demo step API returns movement data

**Complete E2E flow**
- `CompleteUserFlowTest.test_complete_flow_login_to_simulation_observation` covers
  the full sequence: create sim → create doctor character → edit → drop → start →
  observe agents → pause → resume → update visibility

---

## Known Limitations and Future Hardening

1. **Admin check is owner-only in frontend**: `SimulatePage` determines admin by `sim.owner === user.id`. Users with admin membership but not ownership don't see the admin toolbar. Backend correctly uses `SimulationMembership` for auth.

2. **WebSocket token validation is permissive**: `SimulationConsumer.connect` accepts connections without strict JWT validation. Hardening planned.

3. **No browser E2E tests**: All tests are Django integration tests. Playwright E2E coverage for the full UI flow is a future addition.

4. **`living_area` format not validated server-side**: Any string is accepted. Future: validate format `<maze_name>:<location_path>` against available tiles.

5. **`update_simulation` dead code**: The `simulation_views.update_simulation` view (PATCH handler) is no longer routed — the logic was merged into `api_views.simulation_detail`. The dead code in `simulation_views.py` can be removed in a future cleanup.
