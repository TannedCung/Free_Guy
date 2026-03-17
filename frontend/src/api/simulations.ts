/**
 * API client for simulation endpoints.
 * All endpoints served by the Django backend at /api/v1/
 */

import { apiFetch } from './client'

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
  map_id?: string | null
  visibility?: string
  owner?: number | null
  status?: string
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
  const res = await apiFetch('/simulations/')
  if (!res.ok) throw new Error(`Failed to fetch simulations: ${res.status}`)
  return res.json() as Promise<SimulationsListResponse>
}

export async function fetchMySimulations(): Promise<SimulationsListResponse> {
  const res = await apiFetch('/simulations/mine/')
  if (!res.ok) throw new Error(`Failed to fetch my simulations: ${res.status}`)
  return res.json() as Promise<SimulationsListResponse>
}

export async function fetchPublicSimulations(
  status?: string,
): Promise<SimulationsListResponse> {
  const url = status ? `/simulations/public/?status=${encodeURIComponent(status)}` : '/simulations/public/'
  const res = await apiFetch(url)
  if (!res.ok) throw new Error(`Failed to fetch public simulations: ${res.status}`)
  return res.json() as Promise<SimulationsListResponse>
}

export async function fetchSimulation(simId: string): Promise<SimulationMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/`)
  if (!res.ok) throw new Error(`Failed to fetch simulation: ${res.status}`)
  return res.json() as Promise<SimulationMeta>
}

export async function fetchSimulationAgents(simId: string): Promise<SimulationAgentsResponse> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/agents/`)
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
  mapId?: string,
  visibility?: string,
): Promise<SimulationMeta> {
  const body: Record<string, string> = { name }
  if (forkFrom) body.fork_from = forkFrom
  if (mapId) body.map_id = mapId
  if (visibility) body.visibility = visibility
  const res = await apiFetch('/simulations/', {
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

export async function dropCharacter(simId: string, characterId: number): Promise<SimulationMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/drop/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId }),
  })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to drop character')
  }
  return res.json() as Promise<SimulationMeta>
}

export async function startSimulation(simId: string): Promise<SimulationMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/start/`, { method: 'POST' })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to start simulation')
  }
  return res.json() as Promise<SimulationMeta>
}

export async function pauseSimulation(simId: string): Promise<SimulationMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/pause/`, { method: 'POST' })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to pause simulation')
  }
  return res.json() as Promise<SimulationMeta>
}

export async function resumeSimulation(simId: string): Promise<SimulationMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/resume/`, { method: 'POST' })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to resume simulation')
  }
  return res.json() as Promise<SimulationMeta>
}

export async function updateSimulation(
  simId: string,
  data: { visibility?: string },
): Promise<SimulationMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to update simulation')
  }
  return res.json() as Promise<SimulationMeta>
}

export interface SimulationMember {
  user_id: number
  username: string
  role: string
  status: string
}

export interface SimulationMembersResponse {
  members: SimulationMember[]
}

export async function fetchSimulationMembers(simId: string): Promise<SimulationMembersResponse> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/members/`)
  if (!res.ok) throw new Error(`Failed to fetch members: ${res.status}`)
  return res.json() as Promise<SimulationMembersResponse>
}

export async function inviteMember(simId: string, username: string): Promise<void> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/members/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username }),
  })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to invite member')
  }
}

export async function removeMember(simId: string, userId: number): Promise<void> {
  const res = await apiFetch(
    `/simulations/${encodeURIComponent(simId)}/members/${userId}/`,
    { method: 'DELETE' },
  )
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to remove member')
  }
}

export interface InviteItem {
  id: number
  simulation_id: string
  simulation_name: string
  invited_by: string | null
  role: string
  status: string
  invited_at: string
}

export interface InvitesListResponse {
  invites: InviteItem[]
}

export async function fetchMyInvites(): Promise<InvitesListResponse> {
  const res = await apiFetch('/invites/')
  if (!res.ok) throw new Error(`Failed to fetch invites: ${res.status}`)
  return res.json() as Promise<InvitesListResponse>
}

export async function acceptInvite(membershipId: number): Promise<void> {
  const res = await apiFetch(`/invites/${membershipId}/accept/`, { method: 'POST' })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to accept invite')
  }
}

export async function declineInvite(membershipId: number): Promise<void> {
  const res = await apiFetch(`/invites/${membershipId}/decline/`, { method: 'POST' })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to decline invite')
  }
}

export interface ReplayMeta {
  sim_id: string
  total_steps: number
  first_step: number
  last_step: number
}

export interface ReplayAgentState {
  x: number
  y: number
  pronunciatio: string
  description: string
}

export interface ReplayStepResponse {
  step: number
  sim_curr_time: string | null
  agents: Record<string, ReplayAgentState>
}

export async function fetchReplayMeta(simId: string): Promise<ReplayMeta> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/replay/`)
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? `Failed to fetch replay meta: ${res.status}`)
  }
  return res.json() as Promise<ReplayMeta>
}

export async function fetchReplayStep(simId: string, step: number): Promise<ReplayStepResponse> {
  const res = await apiFetch(`/simulations/${encodeURIComponent(simId)}/replay/${step}/`)
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? `Failed to fetch replay step: ${res.status}`)
  }
  return res.json() as Promise<ReplayStepResponse>
}

export interface ConceptNodeSummary {
  node_id: number
  node_type: string
  subject: string
  predicate: string
  object: string
  description: string
  created: string | null
}

export interface AgentDetail extends Agent {
  simulation_id: string
  learned: string | null
  lifestyle: string | null
  living_area: string | null
  daily_plan_req: string | null
  curr_time: string | null
  act_description: string | null
  daily_req: string[]
  chatting_with: string | null
  recent_concepts: ConceptNodeSummary[]
}

export async function fetchAgentDetail(simId: string, agentId: string): Promise<AgentDetail> {
  const res = await apiFetch(
    `/simulations/${encodeURIComponent(simId)}/agents/${encodeURIComponent(agentId)}/`,
  )
  if (!res.ok) throw new Error(`Failed to fetch agent detail: ${res.status}`)
  return res.json() as Promise<AgentDetail>
}
