import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})
    setLoading(true)
    try {
      await register(username, email, password, passwordConfirm)
      navigate('/dashboard')
    } catch (err) {
      if (err && typeof err === 'object') {
        setErrors(err as Record<string, string[]>)
      } else {
        setErrors({ non_field_errors: ['Registration failed'] })
      }
    } finally {
      setLoading(false)
    }
  }

  const fieldError = (field: string) =>
    errors[field]?.[0] ?? null

  return (
    <div className="retro-page flex items-center justify-center px-4 py-8">
      <div className="retro-panel p-6 md:p-8 w-full max-w-lg">
        <h2 className="retro-title mb-3 text-center">Create account</h2>
        <p className="retro-subtitle text-sm text-center mb-5">
          Join the town in under one minute.
        </p>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-xs font-bold uppercase mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="your_username"
              className="retro-input"
            />
            {fieldError('username') && (
              <p className="mt-1 text-sm text-red-600">{fieldError('username')}</p>
            )}
          </div>
          <div>
            <label htmlFor="email" className="block text-xs font-bold uppercase mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="retro-input"
            />
            {fieldError('email') && (
              <p className="mt-1 text-sm text-red-600">{fieldError('email')}</p>
            )}
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-bold uppercase mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="retro-input"
            />
            {fieldError('password') && (
              <p className="mt-1 text-sm text-red-600">{fieldError('password')}</p>
            )}
          </div>
          <div>
            <label htmlFor="password-confirm" className="block text-xs font-bold uppercase mb-1">
              Confirm password
            </label>
            <input
              id="password-confirm"
              type="password"
              required
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              placeholder="••••••••"
              className="retro-input"
            />
            {fieldError('password_confirm') && (
              <p className="mt-1 text-sm text-red-600">{fieldError('password_confirm')}</p>
            )}
          </div>
          {errors.non_field_errors && (
            <p className="text-sm text-red-600">{errors.non_field_errors[0]}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full retro-button retro-button-primary"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="retro-link">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
