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
      <div className="retro-page flex items-center justify-center h-64 text-gray-500">
        Loading…
      </div>
    )
  }

  if (!meta) return null

  return (
    <div className="retro-page">
      <header className="retro-header">
        <div className="retro-header-inner flex flex-wrap items-center gap-2">
          <Link
            to={`/simulate/${encodeURIComponent(simId)}`}
            className="retro-navlink"
          >
            Back to simulation
          </Link>
          <h1 className="retro-title text-base md:text-lg">Settings: {meta.name}</h1>
        </div>
      </header>

      <main className="retro-main space-y-6 max-w-4xl">
        <section className="retro-panel p-5">
          <h2 className="retro-title text-base mb-3">Visibility</h2>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={meta.visibility ?? 'private'}
              onChange={(e) => void handleVisibilityChange(e.target.value)}
              className="retro-select"
            >
              <option value="private">Private</option>
              <option value="shared">Shared</option>
              <option value="public">Public</option>
            </select>
            {visibilityError && <span className="text-sm text-red-500">{visibilityError}</span>}
          </div>
        </section>

        <section className="retro-panel p-5">
          <h2 className="retro-title text-base mb-3">Members</h2>
          {removeError && <p className="text-sm text-red-500 mb-3">{removeError}</p>}
          {members.length === 0 ? (
            <div className="retro-empty-state text-sm">No members yet.</div>
          ) : (
            <ul className="space-y-2 mb-4">
              {members.map((m) => (
                <li
                  key={m.user_id}
                  className="border-2 border-gray-300 bg-white px-3 py-2 flex items-center justify-between gap-2"
                >
                  <div>
                    <span className="font-semibold text-sm">{m.username}</span>
                    <span className="ml-2 text-xs text-gray-500 uppercase">{m.role}</span>
                    <span className="ml-2 text-xs text-gray-500 uppercase">{m.status}</span>
                  </div>
                  {m.role !== 'admin' && (
                    <button
                      onClick={() => void handleRemove(m.user_id)}
                      className="retro-button retro-button-danger"
                    >
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={(e) => void handleInvite(e)} className="flex flex-col md:flex-row gap-2">
            <input
              required
              value={inviteUsername}
              onChange={(e) => setInviteUsername(e.target.value)}
              placeholder="Username to invite"
              className="retro-input flex-1"
            />
            <button type="submit" className="retro-button retro-button-primary">
              Invite
            </button>
          </form>
          {inviteError && <p className="text-red-500 text-sm mt-2">{inviteError}</p>}
          {inviteSuccess && <p className="text-green-700 text-sm mt-2">{inviteSuccess}</p>}
        </section>
      </main>
    </div>
  )
}
