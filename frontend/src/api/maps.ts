import { apiFetch } from './client'

export interface MapMeta {
  id: string
  name: string
  description: string
  preview_image_url: string
  max_agents: number
}

export interface MapsListResponse {
  maps: MapMeta[]
}

export async function fetchMaps(): Promise<MapsListResponse> {
  const res = await apiFetch('/maps/')
  if (!res.ok) throw new Error(`Failed to fetch maps: ${res.status}`)
  return res.json() as Promise<MapsListResponse>
}
