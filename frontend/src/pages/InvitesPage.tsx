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
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-2xl mx-auto px-4 py-10">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Pending Invites</h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-gray-400">Loading…</p>
        ) : invites.length === 0 ? (
          <p className="text-gray-500">
            No pending invites.{' '}
            <Link to="/dashboard" className="text-blue-600 hover:underline">
              Back to dashboard
            </Link>
          </p>
        ) : (
          <ul className="space-y-4">
            {invites.map((invite) => (
              <li key={invite.id} className="bg-white rounded-xl border border-gray-100 shadow p-5">
                <div className="mb-1 font-semibold text-gray-900">{invite.simulation_name}</div>
                {invite.invited_by && (
                  <div className="text-sm text-gray-500 mb-4">
                    Invited by <span className="font-medium">{invite.invited_by}</span>
                  </div>
                )}
                <div className="flex gap-3">
                  <button
                    onClick={() => void handleAccept(invite)}
                    className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-1.5 rounded-lg transition-colors"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => void handleDecline(invite.id)}
                    className="bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm px-4 py-1.5 rounded-lg transition-colors"
                  >
                    Decline
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  )
}
