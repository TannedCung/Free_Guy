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
  const [step, setStep] = useState<1 | 2>(1)

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

  const selectedMap = maps.find((m) => m.id === selectedMapId)

  // ── Step 1: Map selection ─────────────────────────────────────────────────

  if (step === 1) {
    return (
      <div className="retro-page">
        <Header />
        <main className="retro-main max-w-4xl">
          <div className="mb-6">
            <h2 className="retro-title mb-1">Choose a map</h2>
            <p className="retro-subtitle">Pick the world your simulation will run in.</p>
          </div>

          {mapsLoading ? (
            <p className="text-gray-500">Loading maps…</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
              {maps.map((map) => (
                <button
                  key={map.id}
                  type="button"
                  onClick={() => {
                    setSelectedMapId(map.id)
                    setStep(2)
                  }}
                  className={`text-left border-2 transition-colors overflow-hidden ${
                    selectedMapId === map.id
                      ? 'border-blue-500 retro-panel'
                      : 'border-gray-200 bg-white hover:border-blue-400'
                  }`}
                >
                  {map.preview_image_url ? (
                    <img
                      src={map.preview_image_url}
                      alt={map.name}
                      className="w-full h-40 object-cover"
                    />
                  ) : (
                    <div className="w-full h-40 bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
                      No preview
                    </div>
                  )}
                  <div className="p-4">
                    <h4 className="font-bold uppercase text-sm text-gray-900">{map.name}</h4>
                    {map.description && (
                      <p className="text-xs text-gray-600 mt-1">{map.description}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-2">Max agents: {map.max_agents}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="retro-button retro-button-ghost"
          >
            Cancel
          </button>
        </main>
      </div>
    )
  }

  // ── Step 2: Simulation details ────────────────────────────────────────────

  return (
    <div className="retro-page">
      <Header />
      <main className="retro-main max-w-2xl">
        <button
          type="button"
          onClick={() => setStep(1)}
          className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-flex items-center gap-1"
        >
          ← Back to map selection
        </button>

        <div className="mb-6">
          <h2 className="retro-title mb-1">Create simulation</h2>
          <p className="retro-subtitle">Name your simulation and set its visibility.</p>
        </div>

        {/* Selected map summary */}
        {selectedMap && (
          <div className="retro-panel p-4 mb-6 flex items-center gap-4">
            {selectedMap.preview_image_url ? (
              <img
                src={selectedMap.preview_image_url}
                alt={selectedMap.name}
                className="w-20 h-14 object-cover shrink-0"
              />
            ) : (
              <div className="w-20 h-14 bg-gray-100 shrink-0 flex items-center justify-center text-xs text-gray-400">
                No preview
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="font-bold uppercase text-sm text-gray-900">{selectedMap.name}</div>
              {selectedMap.description && (
                <div className="text-xs text-gray-500 mt-0.5 truncate">{selectedMap.description}</div>
              )}
              <div className="text-xs text-gray-400 mt-0.5">Max agents: {selectedMap.max_agents}</div>
            </div>
            <button
              type="button"
              onClick={() => setStep(1)}
              className="text-xs text-blue-500 hover:text-blue-700 shrink-0"
            >
              Change
            </button>
          </div>
        )}

        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="retro-panel p-6 mb-6 space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase mb-1">
                Simulation Name <span className="text-red-500">*</span>
              </label>
              <input
                required
                value={simName}
                onChange={(e) => setSimName(e.target.value)}
                placeholder="e.g. my_ville_experiment"
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Visibility</label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as 'private' | 'public' | 'shared')}
                className="retro-select"
              >
                <option value="private">Private</option>
                <option value="public">Public</option>
                <option value="shared">Shared</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-sm retro-panel">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="retro-button retro-button-primary"
            >
              {loading ? 'Creating…' : 'Create Simulation'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="retro-button retro-button-ghost"
            >
              Cancel
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
