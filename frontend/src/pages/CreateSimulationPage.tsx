import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { fetchMaps, type MapMeta } from '../api/maps'
import { createSimulation } from '../api/simulations'

export default function CreateSimulationPage() {
  const navigate = useNavigate()
  const [maps, setMaps] = useState<MapMeta[]>([])
  const [selectedMapId, setSelectedMapId] = useState<string>('the_ville')
  const [simName, setSimName] = useState('')
  const [visibility, setVisibility] = useState<'private' | 'public' | 'shared'>('private')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [mapsLoading, setMapsLoading] = useState(true)

  useEffect(() => {
    async function loadMaps() {
      try {
        const res = await fetchMaps()
        setMaps(res.maps)
        if (res.maps.length > 0) {
          const ville = res.maps.find((m) => m.id === 'the_ville')
          setSelectedMapId(ville ? ville.id : res.maps[0].id)
        }
      } catch {
        // ignore
      } finally {
        setMapsLoading(false)
      }
    }
    void loadMaps()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const sim = await createSimulation(simName, undefined, selectedMapId, visibility)
      navigate(`/simulate/${encodeURIComponent(sim.id)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create simulation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-10">
        <h2 className="text-3xl font-bold text-gray-900 mb-8">New Simulation</h2>
        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="bg-white rounded-xl border border-gray-100 shadow p-8 mb-6">
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Simulation Name <span className="text-red-500">*</span>
              </label>
              <input
                required
                value={simName}
                onChange={(e) => setSimName(e.target.value)}
                placeholder="e.g. my_ville_experiment"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as 'private' | 'public' | 'shared')}
                className="rounded-lg border border-gray-300 px-4 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="private">Private</option>
                <option value="public">Public</option>
                <option value="shared">Shared</option>
              </select>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow p-8 mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Choose a Map</h3>
            {mapsLoading ? (
              <p className="text-gray-500">Loading maps…</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {maps.map((map) => (
                  <button
                    key={map.id}
                    type="button"
                    onClick={() => setSelectedMapId(map.id)}
                    className={`text-left p-4 rounded-xl border-2 transition-colors ${
                      selectedMapId === map.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                  >
                    <h4 className="font-semibold text-gray-900">{map.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{map.description}</p>
                    <p className="text-xs text-gray-400 mt-2">Max agents: {map.max_agents}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading || mapsLoading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium px-6 py-2 rounded-lg transition-colors"
            >
              {loading ? 'Creating…' : 'Create Simulation'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="text-gray-600 hover:text-gray-900 font-medium px-4 py-2"
            >
              Cancel
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
