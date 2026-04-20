import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import {
  fetchMyInvites,
  acceptInvite,
  declineInvite,
  type InviteItem,
} from '../api/simulations'

export default function InvitesPage() {
  const navigate = useNavigate()
  const [invites, setInvites] = useState<InviteItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMyInvites()
      .then((data) => setInvites(data.invites))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load invites'),
      )
      .finally(() => setLoading(false))
  }, [])

  const handleAccept = async (invite: InviteItem) => {
    try {
      await acceptInvite(invite.id)
      setInvites((prev) => prev.filter((i) => i.id !== invite.id))
      void navigate(`/simulate/${encodeURIComponent(invite.simulation_id)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept invite')
    }
  }

  const handleDecline = async (id: number) => {
    try {
      await declineInvite(id)
      setInvites((prev) => prev.filter((i) => i.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to decline invite')
    }
  }

  return (
    <div className="retro-page">
      <Header />
      <main className="retro-main max-w-3xl">
        <div className="retro-panel p-6 md:p-8">
          <h2 className="retro-title text-xl mb-5">Pending invites</h2>
          <p className="retro-subtitle text-sm mb-6">
            Accept to join instantly or decline to clear your queue.
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <p className="text-gray-500">Loading…</p>
          ) : invites.length === 0 ? (
            <p className="retro-empty-state text-sm">
              No pending invites.{' '}
              <Link to="/dashboard" className="retro-link">
                Return to dashboard
              </Link>
              .
            </p>
          ) : (
            <ul className="space-y-4">
              {invites.map((invite) => (
                <li key={invite.id} className="retro-panel p-5">
                  <div className="mb-1 font-bold uppercase tracking-wide text-sm">{invite.simulation_name}</div>
                  {invite.invited_by && (
                    <div className="text-xs text-gray-500 mb-4">
                      Invited by <span className="font-bold">{invite.invited_by}</span>
                    </div>
                  )}
                  <div className="flex gap-3">
                    <button
                      onClick={() => void handleAccept(invite)}
                      className="retro-button retro-button-warm"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => void handleDecline(invite.id)}
                      className="retro-button retro-button-ghost"
                    >
                      Decline
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  )
}
