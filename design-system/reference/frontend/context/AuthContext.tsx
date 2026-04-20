/**
 * Auth context.
 *
 * Session state is derived entirely from the server: on mount we call /auth/me/
 * (which triggers an automatic cookie-based token refresh if needed).  There is
 * no client-side token storage — the httpOnly cookies are invisible to JS.
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
} from '../api/auth'

interface AuthContextValue {
  user: UserData | null
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
  const [isLoading, setIsLoading] = useState(true)

  // On mount, check if the server considers us authenticated.
  // apiFetch will transparently refresh the access cookie if it has expired.
  useEffect(() => {
    apiFetchMe()
      .then((me) => setUser({ id: me.id, username: me.username, email: me.email }))
      .catch(() => {
        // No valid session — stay logged out.
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const { user: userData } = await apiLogin(username, password)
    setUser(userData)
  }

  async function register(
    username: string,
    email: string,
    password: string,
    passwordConfirm: string,
  ) {
    const { user: userData } = await apiRegister(username, email, password, passwordConfirm)
    setUser(userData)
  }

  async function logout() {
    try {
      await apiLogout()
    } catch {
      // ignore network errors on logout
    }
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
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
