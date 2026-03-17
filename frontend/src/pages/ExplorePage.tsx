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
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Explore Simulations</h2>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 font-medium">Status:</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-gray-400">Loading…</p>
        ) : simulations.length === 0 ? (
          <p className="text-gray-500">No public simulations found.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {simulations.map((sim) => (
              <div
                key={sim.id}
                className="bg-white rounded-xl border border-gray-100 shadow p-5 flex flex-col gap-2"
              >
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-gray-900">{sim.name}</h3>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${statusColors[sim.status ?? 'pending'] ?? 'bg-gray-100 text-gray-600'}`}
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
                  className="mt-auto self-start bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-1.5 rounded-lg transition-colors"
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
