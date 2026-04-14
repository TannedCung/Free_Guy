/**
 * Authenticated fetch wrapper.
 *
 * Auth tokens live exclusively in httpOnly cookies set by the server —
 * JavaScript never reads or writes them.  All we need to do is:
 *   • include credentials (cookies) on every request
 *   • retry once after an automatic token refresh when a 401 is received
 */

const API_BASE = '/api/v1'

export async function apiFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const opts: RequestInit = { ...init, credentials: 'include' }

  let res = await fetch(`${API_BASE}${input}`, opts)

  if (res.status === 401) {
    // Ask the server to rotate the refresh cookie and set a new access cookie.
    const refreshRes = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      credentials: 'include',
    })
    if (refreshRes.ok) {
      // Retry the original request — the new access cookie is now set.
      res = await fetch(`${API_BASE}${input}`, opts)
    }
  }

  return res
}
