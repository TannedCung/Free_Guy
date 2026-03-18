import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { fetchMyInvites } from '../api/simulations'

export default function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [pendingInvites, setPendingInvites] = useState(0)

  useEffect(() => {
    if (!user) return
    fetchMyInvites()
      .then((data) => setPendingInvites(data.invites.length))
      .catch(() => {/* ignore */})
  }, [user])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-5xl mx-auto px-4 py-5 flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold text-gray-900">
          Generative Agents — Reverie
        </Link>
        <nav className="flex gap-6 items-center">
          {user ? (
            <>
              <Link to="/dashboard" className="text-blue-600 hover:text-blue-800 font-medium">
                Dashboard
              </Link>
              <Link to="/explore" className="text-blue-600 hover:text-blue-800 font-medium">
                Explore
              </Link>
              <Link to="/invites" className="relative text-blue-600 hover:text-blue-800 font-medium">
                Invites
                {pendingInvites > 0 && (
                  <span className="absolute -top-2 -right-3 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                    {pendingInvites}
                  </span>
                )}
              </Link>
              <span className="text-gray-700 font-medium">{user.username}</span>
              <button
                onClick={() => void handleLogout()}
                className="text-red-600 hover:text-red-800 font-medium"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-blue-600 hover:text-blue-800 font-medium">
                Login
              </Link>
              <Link to="/register" className="text-blue-600 hover:text-blue-800 font-medium">
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
