/**
 * API client for simulation endpoints.
 * All endpoints served by the Django backend at /api/v1/
 */

const API_BASE = '/api/v1'

export interface AgentLocation {
  maze: string
  x: number
  y: number
}

export interface Agent {
  id: string
  name: string
  first_name: string | null
  last_name: string | null
  age: number | null
  innate: string | null
  currently: string | null
  location: AgentLocation | null
  /** Emoji or short status label shown above the sprite (e.g. from demo pronunciatio) */
  pronunciatio?: string | null
}

// ─── Demo types ───────────────────────────────────────────────────────────────

export interface DemoMeta {
  id: string
  name: string
  fork_sim_code: string | null
  start_date: string | null
  curr_time: string | null
  sec_per_step: number | null
  maze_name: string | null
  persona_names: string[]
  step: number
  total_steps: number | null
}

export interface DemoAgentState {
  movement: [number, number]
  pronunciatio: string
  description: string
  chat: unknown
}

export interface DemoStepResponse {
  demo_id: string
  step: number
  sec_per_step: number | null
  agents: Record<string, DemoAgentState>
}

export interface DemosListResponse {
  demos: DemoMeta[]
}

export interface SimulationMeta {
  id: string
  name: string
  fork_sim_code: string | null
  start_date: string | null
  curr_time: string | null
  sec_per_step: number | null
  maze_name: string | null
  persona_names: string[]
  step: number
}

export interface SimulationAgentsResponse {
  simulation_id: string
  step: number | null
  agents: Agent[]
}

export interface SimulationsListResponse {
  simulations: SimulationMeta[]
}

export async function fetchSimulations(): Promise<SimulationsListResponse> {
  const res = await fetch(`${API_BASE}/simulations/`)
  if (!res.ok) throw new Error(`Failed to fetch simulations: ${res.status}`)
  return res.json() as Promise<SimulationsListResponse>
}

export async function fetchSimulation(simId: string): Promise<SimulationMeta> {
  const res = await fetch(`${API_BASE}/simulations/${encodeURIComponent(simId)}/`)
  if (!res.ok) throw new Error(`Failed to fetch simulation: ${res.status}`)
  return res.json() as Promise<SimulationMeta>
}

export async function fetchSimulationAgents(simId: string): Promise<SimulationAgentsResponse> {
  const res = await fetch(`${API_BASE}/simulations/${encodeURIComponent(simId)}/agents/`)
  if (!res.ok) throw new Error(`Failed to fetch agents: ${res.status}`)
  return res.json() as Promise<SimulationAgentsResponse>
}

export async function fetchDemos(): Promise<DemosListResponse> {
  const res = await fetch(`${API_BASE}/demos/`)
  if (!res.ok) throw new Error(`Failed to fetch demos: ${res.status}`)
  return res.json() as Promise<DemosListResponse>
}

export async function fetchDemoStep(demoId: string, step: number): Promise<DemoStepResponse> {
  const res = await fetch(`${API_BASE}/demos/${encodeURIComponent(demoId)}/step/${step}/`)
  if (!res.ok) throw new Error(`Failed to fetch demo step: ${res.status}`)
  return res.json() as Promise<DemoStepResponse>
}

export async function createSimulation(
  name: string,
  forkFrom?: string,
): Promise<SimulationMeta> {
  const body: Record<string, string> = { name }
  if (forkFrom) body.fork_from = forkFrom
  const res = await fetch(`${API_BASE}/simulations/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = (await res.json()) as { error?: string }
    throw new Error(err.error ?? `Failed to create simulation: ${res.status}`)
  }
  return res.json() as Promise<SimulationMeta>
}
