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
    <header className="retro-header">
      <div className="retro-header-inner flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Link to="/" className="retro-brand">
          Reverie Pixel Town
        </Link>
        <nav className="flex flex-wrap gap-2 items-center">
          {user ? (
            <>
              <Link to="/dashboard" className="retro-navlink">
                Dashboard
              </Link>
              <Link to="/characters" className="retro-navlink">
                Characters
              </Link>
              <Link to="/explore" className="retro-navlink">
                Explore
              </Link>
              <Link to="/invites" className="relative retro-navlink">
                Invites
                {pendingInvites > 0 && (
                  <span className="absolute -top-2 -right-3 retro-badge bg-red-500 text-white">
                    {pendingInvites}
                  </span>
                )}
              </Link>
              <Link to="/simulations/new" className="retro-button retro-button-warm">
                + New Simulation
              </Link>
              <span className="text-xs md:text-sm font-bold uppercase tracking-wide text-gray-700">
                {user.username}
              </span>
              <button
                onClick={() => void handleLogout()}
                className="retro-button retro-button-danger"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="retro-navlink">
                Login
              </Link>
              <Link to="/register" className="retro-navlink">
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
