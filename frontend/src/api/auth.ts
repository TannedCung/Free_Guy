/**
 * Auth API functions.
 */

import { apiFetch } from './client'

export interface UserData {
  id: number
  username: string
  email: string
}

export interface AuthTokens {
  access: string
  refresh: string
  user: UserData
}

export async function apiLogin(
  username: string,
  password: string,
): Promise<AuthTokens> {
  const res = await apiFetch('/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = (await res.json()) as { detail?: string }
    throw new Error(err.detail ?? 'Login failed')
  }
  return res.json() as Promise<AuthTokens>
}

export async function apiRegister(
  username: string,
  email: string,
  password: string,
  passwordConfirm: string,
): Promise<AuthTokens> {
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
  return res.json() as Promise<AuthTokens>
}

export async function apiLogout(refresh: string): Promise<void> {
  await apiFetch('/auth/logout/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
}

export async function apiFetchMe(): Promise<UserData & { date_joined: string }> {
  const res = await apiFetch('/auth/me/')
  if (!res.ok) throw new Error('Failed to fetch user profile')
  return res.json() as Promise<UserData & { date_joined: string }>
}
