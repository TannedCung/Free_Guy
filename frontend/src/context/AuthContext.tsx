/**
 * Auth context providing user state and auth operations.
 * Access token is stored in memory; refresh token is managed via cookie.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from 'react'
import {
  apiLogin,
  apiRegister,
  apiLogout,
  apiFetchMe,
  type UserData,
  type AuthTokens,
} from '../api/auth'
import { setAccessToken } from '../api/client'

interface AuthContextValue {
  user: UserData | null
  accessToken: string | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (
    username: string,
    email: string,
    password: string,
    passwordConfirm: string,
  ) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserData | null>(null)
  const [accessToken, setAccessTokenState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  function _setTokens(tokens: AuthTokens) {
    setAccessTokenState(tokens.access)
    setAccessToken(tokens.access)
    setUser(tokens.user)
  }

  // On mount, try to restore session via token refresh (cookie-based)
  useEffect(() => {
    async function tryRestoreSession() {
      try {
        const res = await fetch('/api/v1/auth/token/refresh/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })
        if (res.ok) {
          const data = (await res.json()) as { access: string }
          setAccessTokenState(data.access)
          setAccessToken(data.access)
          const me = await apiFetchMe()
          setUser({ id: me.id, username: me.username, email: me.email })
        }
      } catch {
        // No valid session
      } finally {
        setIsLoading(false)
      }
    }
    void tryRestoreSession()
  }, [])

  async function login(username: string, password: string) {
    const tokens = await apiLogin(username, password)
    _setTokens(tokens)
  }

  async function register(
    username: string,
    email: string,
    password: string,
    passwordConfirm: string,
  ) {
    const tokens = await apiRegister(username, email, password, passwordConfirm)
    _setTokens(tokens)
  }

  async function logout() {
    if (accessToken) {
      try {
        await apiLogout(accessToken)
      } catch {
        // ignore
      }
    }
    setAccessTokenState(null)
    setAccessToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{ user, accessToken, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
