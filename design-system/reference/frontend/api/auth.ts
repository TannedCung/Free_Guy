/**
 * Auth API functions.
 *
 * Tokens are managed entirely via httpOnly cookies on the server side.
 * Login and register return only user data; the cookies are set automatically
 * by the server on every auth response.
 */

import { apiFetch } from './client'

export interface UserData {
  id: number
  username: string
  email: string
}

export async function apiLogin(
  username: string,
  password: string,
): Promise<{ user: UserData }> {
  const res = await apiFetch('/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Login failed')
  }
  return res.json() as Promise<{ user: UserData }>
}

export async function apiRegister(
  username: string,
  email: string,
  password: string,
  passwordConfirm: string,
): Promise<{ user: UserData }> {
  const res = await apiFetch('/auth/register/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      email,
      password,
      password_confirm: passwordConfirm,
    }),
  })
  if (!res.ok) {
    const err = (await res.json()) as Record<string, string[]>
    throw err
  }
  return res.json() as Promise<{ user: UserData }>
}

export async function apiLogout(): Promise<void> {
  // Server reads the refresh cookie, blacklists it, and clears both cookies.
  await apiFetch('/auth/logout/', { method: 'POST' })
}

export async function apiFetchMe(): Promise<UserData & { date_joined: string }> {
  const res = await apiFetch('/auth/me/')
  if (!res.ok) throw new Error('Not authenticated')
  return res.json() as Promise<UserData & { date_joined: string }>
}
