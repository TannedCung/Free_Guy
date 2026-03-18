import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import { fetchMySimulations, type SimulationMeta } from '../api/simulations'
import { fetchCharacters, type Character } from '../api/characters'

function statusBadge(status?: string) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-blue-100 text-blue-700',
    failed: 'bg-red-100 text-red-700',
  }
  const label = status ?? 'pending'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[label] ?? colors.pending}`}>
      {label}
    </span>
  )
}

export default function DashboardPage() {
  const [simulations, setSimulations] = useState<SimulationMeta[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [simsRes, charsRes] = await Promise.all([
          fetchMySimulations(),
          fetchCharacters(),
        ])
        setSimulations(simsRes.simulations)
        setCharacters(charsRes.characters)
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-10">
        <h2 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h2>

        {/* Simulations */}
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-800">My Simulations</h3>
            <Link
              to="/simulations/new"
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Create simulation
            </Link>
          </div>
          {loading ? (
            <p className="text-gray-500">Loading…</p>
          ) : simulations.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow p-8 text-center text-gray-500">
              No simulations yet. Create your first simulation!
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {simulations.map((sim) => (
                <div key={sim.id} className="bg-white rounded-xl border border-gray-100 shadow p-5">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-900">{sim.name}</h4>
                    {statusBadge(sim.status)}
                  </div>
                  <p className="text-sm text-gray-500 mb-1">Map: {sim.map_id ?? sim.maze_name ?? '—'}</p>
                  <p className="text-sm text-gray-500 mb-3">
                    Characters: {sim.persona_names.length} · Step: {sim.step}
                  </p>
                  <div className="flex gap-2">
                    <Link
                      to={`/simulate/${encodeURIComponent(sim.id)}`}
                      className="text-sm text-blue-600 hover:underline font-medium"
                    >
                      Observe
                    </Link>
                    <Link
                      to={`/simulate/${encodeURIComponent(sim.id)}/settings`}
                      className="text-sm text-gray-500 hover:underline"
                    >
                      Settings
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Characters */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-800">My Characters</h3>
            <Link
              to="/characters/new"
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Create character
            </Link>
          </div>
          {loading ? (
            <p className="text-gray-500">Loading…</p>
          ) : characters.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-100 shadow p-8 text-center text-gray-500">
              No characters yet. Create your first character!
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {characters.map((char) => (
                <div key={char.id} className="bg-white rounded-xl border border-gray-100 shadow p-4">
                  <h4 className="font-semibold text-gray-900">{char.name}</h4>
                  <p className="text-sm text-gray-500 mt-1">
                    Status:{' '}
                    <span
                      className={
                        char.status === 'in_simulation'
                          ? 'text-green-600 font-medium'
                          : 'text-gray-600'
                      }
                    >
                      {char.status === 'in_simulation' ? 'In simulation' : 'Available'}
                    </span>
                  </p>
                  {char.simulation && (
                    <p className="text-xs text-gray-400 mt-0.5">Sim: {char.simulation}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
