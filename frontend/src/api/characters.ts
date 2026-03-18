import { apiFetch } from './client'

export interface Character {
  id: number
  name: string
  age: number | null
  traits: string
  backstory: string
  currently: string
  lifestyle: string
  daily_plan: string
  status: 'available' | 'in_simulation'
  simulation: string | null
}

export interface CharactersListResponse {
  characters: Character[]
}

export async function fetchCharacters(): Promise<CharactersListResponse> {
  const res = await apiFetch('/characters/')
  if (!res.ok) throw new Error(`Failed to fetch characters: ${res.status}`)
  return res.json() as Promise<CharactersListResponse>
}

export async function createCharacter(
  data: Partial<Omit<Character, 'id' | 'status' | 'simulation'>>,
): Promise<Character> {
  const res = await apiFetch('/characters/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = (await res.json()) as Record<string, string[]>
    throw err
  }
  return res.json() as Promise<Character>
}

export async function deleteCharacter(id: number): Promise<void> {
  const res = await apiFetch(`/characters/${id}/`, { method: 'DELETE' })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Failed to delete character')
  }
}
