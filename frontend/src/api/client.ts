/**
 * Authenticated fetch wrapper.
 * Attaches Authorization header and auto-retries on 401 after token refresh.
 */

const API_BASE = '/api/v1'
const REFRESH_TOKEN_STORAGE_KEY = 'ga_refresh_token'

// In-memory access token (set by AuthContext)
let _accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  _accessToken = token
}

export function getAccessToken(): string | null {
  return _accessToken
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token)
    return
  }
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
}

export async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null

  const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!res.ok) {
    if (res.status === 401) setRefreshToken(null)
    return null
  }
  const data = (await res.json()) as { access: string }
  _accessToken = data.access
  return data.access
}

export async function apiFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers)
  if (_accessToken) {
    headers.set('Authorization', `Bearer ${_accessToken}`)
  }

  let res = await fetch(`${API_BASE}${input}`, { ...init, headers })

  if (res.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`)
      res = await fetch(`${API_BASE}${input}`, { ...init, headers })
    }
  }

  return res
}
