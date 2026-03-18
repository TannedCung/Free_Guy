import { useEffect, useState, useCallback } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  fetchSimulation,
  fetchSimulationMembers,
  updateSimulation,
  inviteMember,
  removeMember,
  type SimulationMeta,
  type SimulationMember,
} from '../api/simulations'
import { useAuth } from '../context/AuthContext'

export default function SimulationSettingsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [meta, setMeta] = useState<SimulationMeta | null>(null)
  const [members, setMembers] = useState<SimulationMember[]>([])
  const [inviteUsername, setInviteUsername] = useState('')
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null)
  const [removeError, setRemoveError] = useState<string | null>(null)
  const [visibilityError, setVisibilityError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const simId = id ?? ''

  const loadData = useCallback(() => {
    if (!simId) return
    Promise.all([fetchSimulation(simId), fetchSimulationMembers(simId)])
      .then(([simData, membersData]) => {
        if (!user || simData.owner !== user.id) {
          void navigate(`/simulate/${encodeURIComponent(simId)}`, { replace: true })
          return
        }
        setMeta(simData)
        setMembers(membersData.members)
      })
      .catch(() => {
        void navigate(`/simulate/${encodeURIComponent(simId)}`, { replace: true })
      })
      .finally(() => setLoading(false))
  }, [simId, user, navigate])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleVisibilityChange = async (value: string) => {
    if (!meta) return
    setVisibilityError(null)
    try {
      const updated = await updateSimulation(simId, { visibility: value })
      setMeta(updated)
    } catch (err) {
      setVisibilityError(err instanceof Error ? err.message : 'Failed to update visibility')
    }
  }

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    setInviteError(null)
    setInviteSuccess(null)
    try {
      await inviteMember(simId, inviteUsername)
      setInviteSuccess(`Invited ${inviteUsername}`)
      setInviteUsername('')
      loadData()
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : 'Failed to invite user')
    }
  }

  const handleRemove = async (userId: number) => {
    setRemoveError(null)
    try {
      await removeMember(simId, userId)
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
    } catch (err) {
      setRemoveError(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Loading…
      </div>
    )
  }

  if (!meta) return null

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-800 border-b border-gray-700">
        <Link
          to={`/simulate/${encodeURIComponent(simId)}`}
          className="text-blue-400 hover:underline text-sm"
        >
          ← Back to Simulation
        </Link>
        <h1 className="text-lg font-semibold">Settings: {meta.name}</h1>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-8">
        {/* Visibility */}
        <section className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4">Visibility</h2>
          <div className="flex items-center gap-4">
            <select
              value={meta.visibility ?? 'private'}
              onChange={(e) => void handleVisibilityChange(e.target.value)}
              className="rounded-lg border border-gray-600 bg-gray-700 text-white px-3 py-2"
            >
              <option value="private">Private</option>
              <option value="shared">Shared</option>
              <option value="public">Public</option>
            </select>
            {visibilityError && <span className="text-red-400 text-sm">{visibilityError}</span>}
          </div>
        </section>

        {/* Members */}
        <section className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4">Members</h2>
          {removeError && <p className="text-red-400 text-sm mb-3">{removeError}</p>}
          {members.length === 0 ? (
            <p className="text-gray-400 text-sm">No members yet.</p>
          ) : (
            <ul className="space-y-2 mb-4">
              {members.map((m) => (
                <li
                  key={m.user_id}
                  className="flex items-center justify-between bg-gray-700 rounded-lg px-4 py-2"
                >
                  <div>
                    <span className="font-medium text-white text-sm">{m.username}</span>
                    <span className="ml-2 text-xs text-gray-400">{m.role}</span>
                    <span className="ml-2 text-xs text-gray-500">{m.status}</span>
                  </div>
                  {m.role !== 'admin' && (
                    <button
                      onClick={() => void handleRemove(m.user_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {/* Invite form */}
          <form onSubmit={(e) => void handleInvite(e)} className="flex gap-2">
            <input
              required
              value={inviteUsername}
              onChange={(e) => setInviteUsername(e.target.value)}
              placeholder="Username to invite"
              className="flex-1 rounded-lg border border-gray-600 bg-gray-700 text-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
            >
              Invite
            </button>
          </form>
          {inviteError && <p className="text-red-400 text-sm mt-2">{inviteError}</p>}
          {inviteSuccess && <p className="text-green-400 text-sm mt-2">{inviteSuccess}</p>}
        </section>
      </main>
    </div>
  )
}
