# PRD: Full PostgreSQL Migration — Replace File-Based Storage with Relational Database

## Introduction

Free_Guy currently persists all simulation state — metadata, environment snapshots, agent movements, persona memories, spatial knowledge, and embeddings — as JSON files on disk under `frontend_server/storage/`, `frontend_server/temp_storage/`, and `frontend_server/compressed_storage/`. This file-based approach was inherited from the original Stanford research codebase and served as a quick prototype, but it creates serious problems: no transactional integrity, no concurrent access safety, no queryability, O(n) lookups across thousands of JSON files, tight coupling between the simulation engine and the filesystem layout, and fragile IPC via temp files.

This PRD defines a **complete replacement** of all file-based data storage with PostgreSQL as the single source of truth, plus Qdrant as a dedicated vector database for embedding storage and similarity search. The migration is a "big bang" approach — once complete, no file I/O remains for simulation data persistence.

## Goals

- Replace **every** JSON file read/write in the data path with PostgreSQL queries via Django ORM
- Design comprehensive, normalized database tables that faithfully represent all current data structures (scratch, associative memory nodes, spatial memory, environment state, movements, demos)
- Integrate Qdrant as the dedicated vector store for persona embeddings, enabling native similarity search
- Migrate all existing simulation data from `storage/` into PostgreSQL + Qdrant via an automated import command
- Replace temp-file IPC (`curr_sim_code.json`, `curr_step.json`, `path_tester_*.json`) with a database-backed runtime state table
- Ensure all existing API endpoints, the simulation engine (`reverie.py`), and the frontend continue to function identically after migration
- Achieve zero file I/O for simulation data — static maze assets (CSVs, tile images) remain as files since they are read-only game assets, not simulation state

---

## Current State: What Gets Replaced

### File Storage Layout Being Eliminated

```
frontend_server/
├── storage/{sim_code}/
│   ├── reverie/meta.json                              → simulations table
│   ├── environment/{step}.json                        → environment_states table
│   ├── movement/{step}.json                           → movement_records table
│   └── personas/{name}/bootstrap_memory/
│       ├── scratch.json                               → personas + persona_scratch tables
│       ├── spatial_memory.json                        → spatial_memories table
│       └── associative_memory/
│           ├── nodes.json                             → concept_nodes table
│           ├── kw_strength.json                       → keyword_strengths table
│           └── embeddings.json                        → Qdrant collection
├── temp_storage/
│   ├── curr_sim_code.json                             → runtime_state table
│   ├── curr_step.json                                 → runtime_state table
│   ├── path_tester_env.json                           → runtime_state table
│   └── path_tester_out.json                           → runtime_state table
└── compressed_storage/{demo_code}/
    ├── meta.json                                      → demos table
    └── master_movement.json                           → demo_movements table
```

### Files That Read/Write Simulation Data (Must Be Modified)

| File | Current I/O | Change To |
|------|-------------|-----------|
| `backend_server/reverie.py` | Reads/writes meta.json, environment/*.json, movement/*.json, temp files | Django ORM queries |
| `backend_server/persona/persona.py` | Calls scratch.save(), a_mem.save(), s_mem.save() | Django ORM save |
| `backend_server/persona/memory_structures/scratch.py` | Reads/writes scratch.json | Load/save from `persona_scratch` table |
| `backend_server/persona/memory_structures/associative_memory.py` | Reads/writes nodes.json, kw_strength.json, embeddings.json | Load/save from `concept_nodes`, `keyword_strengths` tables + Qdrant |
| `backend_server/persona/memory_structures/spatial_memory.py` | Reads/writes spatial_memory.json | Load/save from `spatial_memories` table |
| `backend_server/db_persistence.py` | Optional bridge to Django ORM | Becomes the **primary** persistence layer (refactored) |
| `backend_server/constant.py` | Defines `fs_storage`, `fs_temp_storage` paths | Remove file path constants, add DB config |
| `frontend_server/translator/views.py` | Writes environment JSON, reads movement JSON | Django ORM queries |
| `frontend_server/translator/api_views.py` | Reads simulation/agent/demo data from files | Django ORM queries |
| `frontend_server/translator/management/commands/import_simulation.py` | Reads JSON → DB | Update for new comprehensive schema |
| `frontend_server/translator/management/commands/export_simulation.py` | DB → JSON | Update for new comprehensive schema |
| `backend_server/utils/compress_sim_storage.py` | Reads storage/ → writes compressed_storage/ | Read from DB → write to `demos`/`demo_movements` tables |

### Static Assets That Remain as Files (NOT Migrated)

These are read-only game configuration files, not simulation state:
- `static_dirs/assets/the_ville/matrix/maze_meta_info.json`
- `static_dirs/assets/the_ville/matrix/special_blocks/*.csv`
- `static_dirs/assets/the_ville/matrix/maze/*.csv`
- `static_dirs/assets/the_ville/visuals/` (tile images)
- `static_dirs/assets/the_ville/agent_history_init_n*.csv`

---

## Database Schema Design

### PostgreSQL Tables

#### 1. `simulations` — replaces `storage/{sim}/reverie/meta.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `name` | `VARCHAR(255)` | UNIQUE, NOT NULL | The sim_code (e.g., "base_the_ville_isabella_maria_klaus") |
| `description` | `TEXT` | DEFAULT '' | |
| `status` | `VARCHAR(20)` | DEFAULT 'pending', INDEX | pending/running/paused/completed/failed |
| `fork_sim_code` | `VARCHAR(255)` | NULLABLE | Name of the parent simulation if forked |
| `start_date` | `VARCHAR(100)` | NULLABLE | Simulation world start date string (e.g., "February 13, 2023") |
| `curr_time` | `VARCHAR(100)` | NULLABLE | Current simulation world time string |
| `sec_per_step` | `INTEGER` | DEFAULT 10 | Seconds of simulation time per step |
| `maze_name` | `VARCHAR(255)` | DEFAULT 'the_ville' | |
| `step` | `INTEGER` | DEFAULT 0 | Current step counter |
| `config` | `JSONB` | DEFAULT '{}' | Extensible config blob |
| `created_at` | `TIMESTAMPTZ` | auto_now_add, INDEX | |
| `updated_at` | `TIMESTAMPTZ` | auto_now | |

#### 2. `personas` — replaces persona identity from `scratch.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `simulation_id` | `INTEGER` | FK → simulations, INDEX | |
| `name` | `VARCHAR(255)` | NOT NULL | Full name (e.g., "Isabella Rodriguez") |
| `first_name` | `VARCHAR(100)` | NULLABLE | |
| `last_name` | `VARCHAR(100)` | NULLABLE | |
| `age` | `INTEGER` | NULLABLE | |
| `innate` | `TEXT` | NULLABLE | L0 permanent core traits |
| `learned` | `TEXT` | NULLABLE | L1 stable traits |
| `currently` | `TEXT` | NULLABLE | L2 external implementation |
| `lifestyle` | `TEXT` | NULLABLE | |
| `living_area` | `VARCHAR(255)` | NULLABLE | |
| `daily_plan_req` | `TEXT` | NULLABLE | |
| `status` | `VARCHAR(20)` | DEFAULT 'active', INDEX | active/idle/sleeping |
| **UNIQUE** | | `(simulation_id, name)` | |

#### 3. `persona_scratch` — replaces full mutable state from `scratch.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `persona_id` | `INTEGER` | FK → personas, UNIQUE | One-to-one |
| `vision_r` | `INTEGER` | DEFAULT 4 | Tiles the persona can see |
| `att_bandwidth` | `INTEGER` | DEFAULT 3 | Attention bandwidth |
| `retention` | `INTEGER` | DEFAULT 5 | Memory retention count |
| `curr_time` | `TIMESTAMPTZ` | NULLABLE | Perceived world time |
| `curr_tile` | `JSONB` | NULLABLE | [x, y] coordinate tuple |
| `concept_forget` | `INTEGER` | DEFAULT 100 | |
| `daily_reflection_time` | `INTEGER` | DEFAULT 180 | Minutes |
| `daily_reflection_size` | `INTEGER` | DEFAULT 5 | |
| `overlap_reflect_th` | `INTEGER` | DEFAULT 2 | |
| `kw_strg_event_reflect_th` | `INTEGER` | DEFAULT 4 | |
| `kw_strg_thought_reflect_th` | `INTEGER` | DEFAULT 4 | |
| `recency_w` | `INTEGER` | DEFAULT 1 | |
| `relevance_w` | `INTEGER` | DEFAULT 1 | |
| `importance_w` | `INTEGER` | DEFAULT 1 | |
| `recency_decay` | `FLOAT` | DEFAULT 0.99 | |
| `importance_trigger_max` | `INTEGER` | DEFAULT 150 | |
| `importance_trigger_curr` | `INTEGER` | DEFAULT 150 | |
| `importance_ele_n` | `INTEGER` | DEFAULT 0 | |
| `thought_count` | `INTEGER` | DEFAULT 5 | |
| `daily_req` | `JSONB` | DEFAULT '[]' | List of daily goals |
| `f_daily_schedule` | `JSONB` | DEFAULT '[]' | Decomposed schedule [[task, duration], ...] |
| `f_daily_schedule_hourly_org` | `JSONB` | DEFAULT '[]' | Original hourly schedule |
| `act_address` | `VARCHAR(512)` | NULLABLE | "world:sector:arena:object" |
| `act_start_time` | `TIMESTAMPTZ` | NULLABLE | |
| `act_duration` | `INTEGER` | NULLABLE | Minutes |
| `act_description` | `TEXT` | NULLABLE | |
| `act_pronunciatio` | `VARCHAR(50)` | NULLABLE | Emoji expression |
| `act_event` | `JSONB` | DEFAULT '[null, null, null]' | [subject, predicate, object] triple |
| `act_obj_description` | `TEXT` | NULLABLE | |
| `act_obj_pronunciatio` | `VARCHAR(50)` | NULLABLE | |
| `act_obj_event` | `JSONB` | DEFAULT '[null, null, null]' | |
| `chatting_with` | `VARCHAR(255)` | NULLABLE | Name of chat partner |
| `chat` | `JSONB` | NULLABLE | [[speaker, message], ...] |
| `chatting_with_buffer` | `JSONB` | DEFAULT '{}' | {persona_name: cooldown_counter} |
| `chatting_end_time` | `TIMESTAMPTZ` | NULLABLE | |
| `act_path_set` | `BOOLEAN` | DEFAULT FALSE | |
| `planned_path` | `JSONB` | DEFAULT '[]' | [[x,y], ...] |

#### 4. `environment_states` — replaces `storage/{sim}/environment/{step}.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `simulation_id` | `INTEGER` | FK → simulations, INDEX | |
| `step` | `INTEGER` | NOT NULL, INDEX | |
| `agent_positions` | `JSONB` | NOT NULL | {"Agent Name": {"maze": "x", "x": 50, "y": 70}} |
| **UNIQUE** | | `(simulation_id, step)` | |

#### 5. `movement_records` — replaces `storage/{sim}/movement/{step}.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `simulation_id` | `INTEGER` | FK → simulations, INDEX | |
| `step` | `INTEGER` | NOT NULL, INDEX | |
| `sim_curr_time` | `VARCHAR(100)` | NULLABLE | Sim time at this step (from meta.curr_time) |
| `persona_movements` | `JSONB` | NOT NULL | {"Agent Name": {"movement": [x,y], "pronunciatio": "...", "description": "...", "chat": [...]}} |
| **UNIQUE** | | `(simulation_id, step)` | |

#### 6. `concept_nodes` — replaces `associative_memory/nodes.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `persona_id` | `INTEGER` | FK → personas, INDEX | |
| `node_id` | `VARCHAR(50)` | NOT NULL | "node_1", "node_2", etc. |
| `node_count` | `INTEGER` | NOT NULL | Global insertion order |
| `type_count` | `INTEGER` | NOT NULL | Per-type insertion order |
| `node_type` | `VARCHAR(20)` | NOT NULL, INDEX | 'event', 'thought', 'chat' |
| `depth` | `INTEGER` | DEFAULT 0 | Reflection depth |
| `created` | `TIMESTAMPTZ` | NOT NULL, INDEX | In-simulation creation time |
| `expiration` | `TIMESTAMPTZ` | NULLABLE | |
| `last_accessed` | `TIMESTAMPTZ` | NOT NULL | |
| `subject` | `VARCHAR(512)` | NOT NULL, INDEX | SPO triple: subject |
| `predicate` | `VARCHAR(512)` | NOT NULL | SPO triple: predicate |
| `object` | `VARCHAR(512)` | NOT NULL | SPO triple: object |
| `description` | `TEXT` | NOT NULL | Human-readable description |
| `embedding_key` | `VARCHAR(255)` | NOT NULL | Key linking to Qdrant vector |
| `poignancy` | `FLOAT` | DEFAULT 0.0 | Importance/poignancy score |
| `keywords` | `JSONB` | DEFAULT '[]' | List of keyword strings |
| `filling` | `JSONB` | DEFAULT '[]' | List of node_id references |
| **UNIQUE** | | `(persona_id, node_id)` | |

**Indexes:** `(persona_id, node_type)`, `(persona_id, subject)`, `(persona_id, created DESC)`

#### 7. `keyword_strengths` — replaces `associative_memory/kw_strength.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `persona_id` | `INTEGER` | FK → personas, INDEX | |
| `keyword` | `VARCHAR(255)` | NOT NULL | Lowercased keyword |
| `strength_type` | `VARCHAR(20)` | NOT NULL | 'event' or 'thought' |
| `strength` | `INTEGER` | DEFAULT 0 | Cumulative count |
| **UNIQUE** | | `(persona_id, keyword, strength_type)` | |

#### 8. `spatial_memories` — replaces `spatial_memory.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `persona_id` | `INTEGER` | FK → personas, UNIQUE | One-to-one |
| `tree` | `JSONB` | DEFAULT '{}' | Nested world→sector→arena→objects dict |

#### 9. `demos` — replaces `compressed_storage/{demo}/meta.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `name` | `VARCHAR(255)` | UNIQUE, NOT NULL | Demo code identifier |
| `fork_sim_code` | `VARCHAR(255)` | NULLABLE | |
| `start_date` | `VARCHAR(100)` | NULLABLE | |
| `curr_time` | `VARCHAR(100)` | NULLABLE | |
| `sec_per_step` | `INTEGER` | DEFAULT 10 | |
| `maze_name` | `VARCHAR(255)` | DEFAULT 'the_ville' | |
| `persona_names` | `JSONB` | DEFAULT '[]' | |
| `step` | `INTEGER` | DEFAULT 0 | |
| `total_steps` | `INTEGER` | NULLABLE | |
| `created_at` | `TIMESTAMPTZ` | auto_now_add | |

#### 10. `demo_movements` — replaces `compressed_storage/{demo}/master_movement.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `demo_id` | `INTEGER` | FK → demos, INDEX | |
| `step` | `INTEGER` | NOT NULL | |
| `agent_movements` | `JSONB` | NOT NULL | {"Agent Name": {"movement": [...], "pronunciatio": "...", "description": "...", "chat": [...]}} |
| **UNIQUE** | | `(demo_id, step)` | |

#### 11. `runtime_state` — replaces `temp_storage/*.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `key` | `VARCHAR(255)` | UNIQUE, NOT NULL | 'curr_sim_code', 'curr_step', 'path_tester_env', 'path_tester_out' |
| `value` | `JSONB` | DEFAULT '{}' | The JSON payload |
| `updated_at` | `TIMESTAMPTZ` | auto_now | |

#### 12. `conversations` — replaces chat data scattered across movement + memory

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `simulation_id` | `INTEGER` | FK → simulations, INDEX | |
| `started_at` | `TIMESTAMPTZ` | NOT NULL, INDEX | |
| `transcript` | `JSONB` | DEFAULT '[]' | [[speaker, message], ...] |

#### 13. `conversation_participants` — M2M join table

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `SERIAL` | PK | |
| `conversation_id` | `INTEGER` | FK → conversations | |
| `persona_id` | `INTEGER` | FK → personas | |
| **UNIQUE** | | `(conversation_id, persona_id)` | |

### Qdrant Collection

#### `persona_embeddings` — replaces `associative_memory/embeddings.json`

| Field | Type | Notes |
|-------|------|-------|
| `point_id` | UUID | Auto-generated |
| `vector` | `float[]` | The embedding vector (dimension varies by model, typically 1536 for OpenAI) |
| **Payload:** `persona_id` | `int` | Links to PostgreSQL personas.id |
| **Payload:** `embedding_key` | `string` | Original key (e.g., "event_1", "thought_3") — matches concept_nodes.embedding_key |
| **Payload:** `simulation_id` | `int` | For multi-simulation isolation |

**Collection config:** cosine distance metric, HNSW index for ANN search.

---

## User Stories

### Phase 1: Schema & Infrastructure

#### US-001: Create comprehensive Django models for all simulation data

**Description:** As a developer, I need Django ORM models for every data entity so that all simulation state can be stored in PostgreSQL.

**Acceptance Criteria:**
- [ ] `Simulation` model with all fields from meta.json (name, fork_sim_code, start_date, curr_time, sec_per_step, maze_name, step, status, config)
- [ ] `Persona` model with identity fields (name, first_name, last_name, age, innate, learned, currently, lifestyle, living_area, daily_plan_req, status)
- [ ] `PersonaScratch` model with all 30+ mutable state fields (one-to-one with Persona)
- [ ] `EnvironmentState` model (simulation FK, step, agent_positions JSONB)
- [ ] `MovementRecord` model (simulation FK, step, sim_curr_time, persona_movements JSONB)
- [ ] `ConceptNode` model with all associative memory node fields (persona FK, node_id, type, depth, SPO triple, poignancy, keywords, filling)
- [ ] `KeywordStrength` model (persona FK, keyword, strength_type, strength)
- [ ] `SpatialMemory` model (persona FK one-to-one, tree JSONB)
- [ ] `Demo` model with all demo metadata fields
- [ ] `DemoMovement` model (demo FK, step, agent_movements JSONB)
- [ ] `RuntimeState` model (key unique, value JSONB)
- [ ] `Conversation` model with M2M participants
- [ ] All unique constraints and indexes defined as specified in the schema
- [ ] Migrations generated and applied successfully against PostgreSQL 16
- [ ] Django admin registered for all models with list_display and search_fields

#### US-002: Set up Qdrant integration for embedding storage

**Description:** As a developer, I need Qdrant configured as the vector database so embeddings can be stored and queried with similarity search.

**Acceptance Criteria:**
- [ ] Qdrant service added to `docker-compose.yml` with persistent volume
- [ ] `qdrant-client` added to `backend_server/requirements.txt` and `frontend_server/requirements.txt`
- [ ] `QDRANT_URL` environment variable configured in `.env` and Docker
- [ ] A `qdrant_client.py` utility module created with functions: `store_embedding(persona_id, embedding_key, vector)`, `get_embedding(persona_id, embedding_key)`, `search_similar(persona_id, query_vector, top_k)`, `delete_persona_embeddings(persona_id)`
- [ ] `persona_embeddings` collection auto-created on first use with correct dimension and cosine distance
- [ ] Qdrant health check added to Docker compose

#### US-003: Create runtime state database table for IPC

**Description:** As a developer, I need temp file IPC replaced with a `runtime_state` table so the backend and frontend can communicate simulation state through the database.

**Acceptance Criteria:**
- [ ] `RuntimeState` model created with key (unique), value (JSONB), updated_at
- [ ] Helper functions: `set_runtime_state(key, value)`, `get_runtime_state(key)` that replace file reads/writes
- [ ] Keys supported: `curr_sim_code`, `curr_step`, `path_tester_env`, `path_tester_out`
- [ ] `views.py` `path_tester_update` writes to `runtime_state` instead of `temp_storage/path_tester_env.json`
- [ ] `reverie.py` reads/writes `curr_sim_code` and `curr_step` from `runtime_state` instead of temp files
- [ ] `reverie.py` reads `path_tester_env` and writes `path_tester_out` via `runtime_state`
- [ ] All temp file references in `constant.py` removed

---

### Phase 2: Backend Persistence Layer Refactor

#### US-004: Refactor `reverie.py` to use PostgreSQL for all simulation state

**Description:** As a developer, I need the simulation engine to read/write all state from PostgreSQL so that file storage is eliminated.

**Acceptance Criteria:**
- [ ] `ReverieServer.__init__` loads simulation metadata from `Simulation` model instead of `meta.json`
- [ ] `ReverieServer.__init__` loads initial environment state from `EnvironmentState` model instead of `environment/{step}.json`
- [ ] `ReverieServer.save` writes to `Simulation`, `Persona`, `PersonaScratch`, `EnvironmentState` instead of JSON files
- [ ] `ReverieServer.start_server` writes movement data to `MovementRecord` model instead of `movement/{step}.json`
- [ ] `ReverieServer.start_server` updates `Simulation.step` and `Simulation.curr_time` in DB
- [ ] `ReverieServer.start_server` writes current step/sim_code to `RuntimeState` instead of temp files
- [ ] `ReverieServer.start_path_tester_server` reads/writes via `RuntimeState`
- [ ] All `json.load(open(...))` and `json.dump(...)` calls for simulation data removed from `reverie.py`
- [ ] `fs_storage` and `fs_temp_storage` constants no longer referenced in reverie.py
- [ ] Simulation can be started, run for multiple steps, paused, and resumed entirely from DB state

#### US-005: Refactor `Scratch` class to load/save from PostgreSQL

**Description:** As a developer, I need the Scratch (short-term memory) class to persist to the `persona_scratch` table so persona state survives without JSON files.

**Acceptance Criteria:**
- [ ] `Scratch.__init__` accepts either a `persona_id` (DB mode) or `f_saved` path (legacy mode, for import only)
- [ ] New `Scratch.load_from_db(persona_id)` class method that populates all fields from `PersonaScratch` row
- [ ] `Scratch.save` method writes all fields to `PersonaScratch` via Django ORM instead of JSON
- [ ] `Scratch.save` also updates identity fields on the parent `Persona` record (name, age, innate, etc.)
- [ ] All 40+ fields round-trip correctly: save → load produces identical state
- [ ] Datetime fields correctly serialized/deserialized between Python datetime and DB timestamp
- [ ] JSON fields (daily_req, f_daily_schedule, curr_tile, act_event, planned_path, etc.) stored as JSONB

#### US-006: Refactor `AssociativeMemory` to load/save from PostgreSQL + Qdrant

**Description:** As a developer, I need the associative memory (long-term memory stream) to persist concept nodes in PostgreSQL and embeddings in Qdrant.

**Acceptance Criteria:**
- [ ] `AssociativeMemory.__init__` accepts `persona_id` and loads all `ConceptNode` rows from DB
- [ ] `AssociativeMemory.__init__` loads embeddings from Qdrant collection (not DB)
- [ ] `AssociativeMemory.__init__` loads keyword strengths from `KeywordStrength` table
- [ ] `add_event`, `add_thought`, `add_chat` write the new `ConceptNode` row to DB immediately (not just in-memory)
- [ ] `add_event`, `add_thought`, `add_chat` store the embedding vector in Qdrant via `qdrant_client.store_embedding()`
- [ ] `add_event`, `add_thought` update `KeywordStrength` rows in DB
- [ ] `AssociativeMemory.save` persists any remaining in-memory state (bulk upsert)
- [ ] In-memory caches (`id_to_node`, `seq_event`, `kw_to_event`, etc.) still maintained for fast runtime access
- [ ] All existing retrieval methods (`retrieve_relevant_events`, `retrieve_relevant_thoughts`, `get_last_chat`) work correctly against DB-loaded data

#### US-007: Refactor `SpatialMemory` (MemoryTree) to load/save from PostgreSQL

**Description:** As a developer, I need the spatial memory tree to persist in the `spatial_memories` table.

**Acceptance Criteria:**
- [ ] `MemoryTree.__init__` accepts `persona_id` and loads `tree` from `SpatialMemory` row
- [ ] `MemoryTree.save` writes `tree` JSONB to `SpatialMemory` row via Django ORM
- [ ] All accessor methods (`get_str_accessible_sectors`, `get_str_accessible_sector_arenas`, `get_str_accessible_arena_game_objects`) work identically
- [ ] Tree structure round-trips correctly through JSONB

#### US-008: Refactor `Persona` class to use DB-backed memory structures

**Description:** As a developer, I need the `Persona` class to initialize and save all memory structures through the database.

**Acceptance Criteria:**
- [ ] `Persona.__init__` loads scratch, associative memory, and spatial memory from DB using `persona_id`
- [ ] `Persona.save` calls DB-backed save on all three memory structures
- [ ] No file path construction (`bootstrap_memory/scratch.json`, etc.) in persona initialization
- [ ] Persona can be fully reconstructed from database state alone

---

### Phase 3: Frontend Server Refactor

#### US-009: Refactor `api_views.py` to query PostgreSQL

**Description:** As a developer, I need all REST API endpoints to read from PostgreSQL instead of scanning the filesystem.

**Acceptance Criteria:**
- [ ] `simulations_list` GET queries `Simulation.objects.all()` instead of `os.listdir(STORAGE_DIR)`
- [ ] `simulations_list` POST creates `Simulation` + directory scaffolding via Django ORM (no file writes for meta.json)
- [ ] Fork operation copies DB records (simulation, personas, scratch, memories) instead of `shutil.copytree`
- [ ] `simulation_detail` queries `Simulation` model
- [ ] `simulation_state` queries `EnvironmentState` model for latest step
- [ ] `simulation_agents` queries `Persona` + `PersonaScratch` models joined with latest `EnvironmentState`
- [ ] `simulation_agent_detail` queries `Persona` + `PersonaScratch` models
- [ ] `demos_list` queries `Demo.objects.all()` instead of `os.listdir(COMPRESSED_STORAGE_DIR)`
- [ ] `demo_step` queries `DemoMovement` model instead of loading `master_movement.json`
- [ ] All `STORAGE_DIR` and `COMPRESSED_STORAGE_DIR` constants removed from api_views.py
- [ ] All `os.path`, `os.listdir`, `json.load`, `shutil` calls removed from api_views.py
- [ ] API response format remains identical (no breaking changes to frontend)

#### US-010: Refactor `views.py` process_environment and update_environment

**Description:** As a developer, I need the Phaser game loop endpoints to read/write simulation state from PostgreSQL.

**Acceptance Criteria:**
- [ ] `process_environment` writes agent positions to `EnvironmentState` model instead of `storage/{sim}/environment/{step}.json`
- [ ] `update_environment` reads movement data from `MovementRecord` model instead of `storage/{sim}/movement/{step}.json`
- [ ] `path_tester_update` writes to `RuntimeState` table instead of `temp_storage/path_tester_env.json`
- [ ] Response format remains identical for Phaser compatibility
- [ ] File I/O imports (`json`, `os` for storage paths) removed from views.py

---

### Phase 4: Data Migration & Import

#### US-011: Build comprehensive import command for existing file-based simulations

**Description:** As a developer, I need a management command that migrates all existing file-based simulation data into PostgreSQL + Qdrant.

**Acceptance Criteria:**
- [ ] Command: `python manage.py import_simulation <sim_code>` imports a single simulation
- [ ] Command: `python manage.py import_simulation --all` imports all simulations in `storage/`
- [ ] Imports: simulation metadata from `reverie/meta.json` → `Simulation` row
- [ ] Imports: all environment steps from `environment/*.json` → `EnvironmentState` rows
- [ ] Imports: all movement steps from `movement/*.json` → `MovementRecord` rows
- [ ] Imports: each persona's scratch.json → `Persona` + `PersonaScratch` rows
- [ ] Imports: each persona's spatial_memory.json → `SpatialMemory` row
- [ ] Imports: each persona's nodes.json → `ConceptNode` rows
- [ ] Imports: each persona's kw_strength.json → `KeywordStrength` rows
- [ ] Imports: each persona's embeddings.json → Qdrant `persona_embeddings` collection
- [ ] Idempotent: re-running does not duplicate data (uses `update_or_create`)
- [ ] Prints progress with counts: "Imported 3 personas, 847 concept nodes, 12 environment steps..."
- [ ] Handles missing/corrupted files gracefully with warnings (does not abort entire import)
- [ ] Transaction-safe: each simulation import is wrapped in a database transaction

#### US-012: Build import command for compressed demo data

**Description:** As a developer, I need existing demo/replay data migrated from compressed_storage into PostgreSQL.

**Acceptance Criteria:**
- [ ] Command: `python manage.py import_demo <demo_code>` imports a single demo
- [ ] Command: `python manage.py import_demo --all` imports all demos in `compressed_storage/`
- [ ] Imports: demo meta.json → `Demo` row
- [ ] Imports: master_movement.json → individual `DemoMovement` rows (one per step)
- [ ] Idempotent
- [ ] Prints progress: "Imported demo 'xyz' with 1440 movement steps"

#### US-013: Build export command for database-to-file backup

**Description:** As a developer, I need an export command so simulation data can be backed up to JSON files from the database.

**Acceptance Criteria:**
- [ ] Command: `python manage.py export_simulation <sim_name> --output <dir>`
- [ ] Exports to the original file layout (reverie/meta.json, environment/*.json, movement/*.json, personas/*/bootstrap_memory/*)
- [ ] Includes embeddings export from Qdrant → embeddings.json
- [ ] Useful for backup, debugging, and interoperability

---

### Phase 5: Cleanup & Compression

#### US-014: Refactor `compress_sim_storage.py` to read from database

**Description:** As a developer, I need the simulation compression utility to read from PostgreSQL instead of scanning storage/ files.

**Acceptance Criteria:**
- [ ] `compress()` queries `Simulation`, `MovementRecord`, and `Persona` from DB
- [ ] Writes compressed output to `Demo` + `DemoMovement` tables (not files)
- [ ] All file path references removed

#### US-015: Remove file storage infrastructure

**Description:** As a developer, I need all file storage code paths removed so there is a single source of truth.

**Acceptance Criteria:**
- [ ] `constant.py`: `fs_storage` and `fs_temp_storage` variables removed
- [ ] Docker volumes `simulation-storage` and `simulation-temp` removed from `docker-compose.yml`
- [ ] Dockerfile steps that `mkdir storage temp_storage` removed
- [ ] `global_methods.py` `check_if_file_exists` no longer used for simulation data
- [ ] No remaining `open()` calls for simulation data in backend_server/ or frontend_server/translator/
- [ ] `storage/` and `temp_storage/` directories no longer required at runtime

---

### Phase 6: Testing & Validation

#### US-016: Write integration tests for DB-backed simulation lifecycle

**Description:** As a developer, I need tests verifying the full simulation lifecycle works through PostgreSQL.

**Acceptance Criteria:**
- [ ] Test: Create a simulation via API → verify `Simulation` row exists
- [ ] Test: Fork a simulation → verify all related data (personas, scratch, memories) copied in DB
- [ ] Test: Run `process_environment` → verify `EnvironmentState` row created
- [ ] Test: Run `update_environment` → verify it reads from `MovementRecord`
- [ ] Test: Save persona scratch → verify `PersonaScratch` row matches all fields
- [ ] Test: Save/load associative memory → verify all concept nodes round-trip
- [ ] Test: Save/load spatial memory → verify tree structure round-trips through JSONB
- [ ] Test: Import existing base simulation → verify all data present in DB
- [ ] Test: Export simulation → verify file output matches expected format
- [ ] Test: Qdrant store/retrieve embedding → verify vector round-trips correctly
- [ ] All tests pass against PostgreSQL 16 (not SQLite)

#### US-017: End-to-end validation of simulation run

**Description:** As a developer, I need to verify that a full simulation runs identically on the DB-backed system.

**Acceptance Criteria:**
- [ ] Import `base_the_ville_isabella_maria_klaus` (or equivalent base sim) into DB
- [ ] Start simulation via `reverie.py` — runs for at least 10 steps without errors
- [ ] Verify agent positions update in `EnvironmentState` table
- [ ] Verify movement records appear in `MovementRecord` table
- [ ] Verify concept nodes accumulate in `ConceptNode` table
- [ ] Verify embeddings stored in Qdrant
- [ ] Verify frontend can display simulation state via API
- [ ] Verify demo compression works from DB data
- [ ] Verify demo playback works from DB data

---

## Functional Requirements

- FR-1: All simulation state (metadata, steps, movements, personas, memories, embeddings, demos, IPC) **must** be stored in PostgreSQL or Qdrant — no JSON file I/O for simulation data
- FR-2: The `Simulation` model must store all fields currently in `reverie/meta.json` including fork lineage
- FR-3: `PersonaScratch` must store all 40+ mutable state fields currently in `scratch.json` with correct types
- FR-4: `ConceptNode` must store all associative memory node fields with proper indexes for efficient retrieval by persona, type, subject, and creation time
- FR-5: `KeywordStrength` must support atomic increment operations for concurrent keyword counting
- FR-6: Embeddings must be stored in Qdrant with cosine similarity search capability
- FR-7: `EnvironmentState` and `MovementRecord` must support efficient lookup by `(simulation_id, step)` for the game loop
- FR-8: `RuntimeState` must support fast key-value lookups for IPC between frontend and backend
- FR-9: The simulation fork operation must deep-copy all related DB records (simulation + personas + scratch + memories + spatial + keyword strengths) and Qdrant embeddings
- FR-10: All API response schemas must remain backward-compatible — no breaking changes to frontend
- FR-11: The import command must handle all existing base simulations in `storage/` directory
- FR-12: The import command must be idempotent (safe to re-run)
- FR-13: Demo movement data must be stored as individual rows per step (not one giant JSON blob) for efficient step-by-step retrieval
- FR-14: Static maze assets (CSV maps, tile images) remain as files — they are read-only game configuration, not simulation state

## Non-Goals

- **Schema normalization of JSONB fields** — fields like `f_daily_schedule`, `agent_positions`, `persona_movements` remain as JSONB for now. Normalizing them into separate tables is a future optimization.
- **Real-time change notifications** — no PostgreSQL LISTEN/NOTIFY or WebSocket push. The frontend continues to poll.
- **Multi-tenancy / row-level security** — no per-user data isolation in this phase.
- **Historical audit trail** — no versioning or soft-deletes of simulation state. Overwrites replace previous values.
- **Qdrant clustering** — single-node Qdrant is sufficient. Distributed deployment is out of scope.
- **Migration of static maze assets to DB** — CSVs and images stay on disk.
- **Performance benchmarking** — correctness first. Performance tuning (connection pooling, read replicas, query optimization) is a follow-up.
- **Backward compatibility with file-based mode** — after migration, the file-based code path is removed entirely. The export command serves as the escape hatch.

## Technical Considerations

- **Django ORM from backend_server:** The `backend_server/reverie.py` process runs outside Django's normal lifecycle. It must call `django.setup()` (as `db_persistence.py` already does) to access the ORM. This pattern is already established and will be extended.
- **Transaction boundaries:** Each simulation step should be wrapped in `django.db.transaction.atomic()` to ensure environment state, movement, and persona updates are committed together.
- **Qdrant client lifecycle:** The Qdrant client should be a singleton initialized once. Use `qdrant_client.QdrantClient(url=QDRANT_URL)` with connection pooling.
- **Embedding dimension:** OpenAI `text-embedding-ada-002` produces 1536-dimensional vectors. The Qdrant collection must be created with the correct dimension, configurable via environment variable `EMBEDDING_DIMENSION`.
- **Bulk operations:** The import command should use `bulk_create` and `bulk_update` for performance when importing thousands of concept nodes and environment steps.
- **Datetime handling:** The simulation uses custom datetime string formats (`"%B %d, %Y, %H:%M:%S"` and `"%Y-%m-%d %H:%M:%S"`). The DB layer must handle conversion between these string formats and proper `TIMESTAMPTZ` columns.
- **JSONB vs normalized tables:** Schedule data (`f_daily_schedule`), paths (`planned_path`), and event triples (`act_event`) are stored as JSONB rather than normalized tables. This trades query flexibility for simpler schema and faster writes — appropriate since these fields are always read/written as a unit.

## Success Metrics

- Zero `open()` calls for simulation data in backend_server/ and frontend_server/translator/ (verified by grep)
- All existing base simulations (`base_the_ville_*`) successfully imported and viewable via API
- Simulation engine runs 100+ steps without file I/O errors or data loss
- All REST API endpoints return identical response schemas (verified by comparing JSON output before/after)
- Qdrant stores and retrieves embeddings with correct dimensionality
- `docker compose up` starts PostgreSQL + Qdrant + all services with zero file storage dependencies
- Import command completes in under 60 seconds for a typical base simulation
- All existing Django tests plus new integration tests pass

## Open Questions

- What Qdrant data persistence strategy should we use? (In-memory with snapshots vs. on-disk storage?)
- Should we add a database connection pool (e.g., `django-db-connection-pool` or PgBouncer) from the start, or defer to performance tuning phase?
- Should the `ConceptNode` table include a GIN index on the `keywords` JSONB field for fast keyword lookups, or is the in-memory cache sufficient?
- How should we handle the `filling` field on ConceptNode (which contains references to other node_ids)? Should these become actual FK relationships or remain as string references in JSONB?
- What is the correct embedding dimension for the models currently in use? Is it always 1536 (OpenAI ada-002) or does it vary by LLM provider?
