import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import { fetchPublicSimulations, type SimulationMeta } from '../api/simulations'

const STATUS_OPTIONS = ['', 'pending', 'running', 'paused', 'completed', 'failed']

export default function ExplorePage() {
  const [simulations, setSimulations] = useState<SimulationMeta[]>([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(() => {
      setLoading(true)
      setError(null)
      fetchPublicSimulations(status || undefined)
        .then((data) => { if (!cancelled) setSimulations(data.simulations) })
        .catch((err: unknown) => {
          if (!cancelled)
            setError(err instanceof Error ? err.message : 'Failed to load simulations')
        })
        .finally(() => { if (!cancelled) setLoading(false) })
    }, 0)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [status])

  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-blue-100 text-blue-700',
    failed: 'bg-red-100 text-red-700',
  }

  return (
    <div className="retro-page">
      <Header />
      <main className="retro-main">
        <div className="flex items-center justify-between mb-6">
          <h2 className="retro-title text-xl">Explore Simulations</h2>
          <div className="flex items-center gap-2">
            <label className="text-xs uppercase font-bold text-gray-600">Status:</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="retro-select"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="retro-panel mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-gray-400">Loading…</p>
        ) : simulations.length === 0 ? (
          <div className="retro-panel retro-empty-state">No public simulations found.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {simulations.map((sim) => (
              <div
                key={sim.id}
                className="retro-panel p-5 flex flex-col gap-2"
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-gray-900 uppercase text-sm">{sim.name}</h3>
                  <span
                    className={`retro-badge text-xs px-2 py-0.5 rounded font-medium ${statusColors[sim.status ?? 'pending'] ?? 'bg-gray-100 text-gray-600'}`}
                  >
                    {sim.status ?? 'pending'}
                  </span>
                </div>
                {sim.maze_name && (
                  <div className="text-xs text-gray-500">Map: {sim.maze_name}</div>
                )}
                <div className="text-xs text-gray-500">
                  {sim.persona_names.length} agent{sim.persona_names.length !== 1 ? 's' : ''}
                </div>
                <Link
                  to={`/simulate/${encodeURIComponent(sim.id)}`}
                  className="mt-auto self-start retro-button retro-button-primary"
                >
                  Observe
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
