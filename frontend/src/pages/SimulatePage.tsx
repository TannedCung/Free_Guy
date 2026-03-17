import { useEffect, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import GameCanvas from '../game/GameCanvas'
import {
  fetchSimulation,
  fetchSimulationAgents,
  fetchSimulations,
  dropCharacter,
  startSimulation,
  pauseSimulation,
  resumeSimulation,
  type Agent,
  type SimulationMeta,
} from '../api/simulations'
import { fetchCharacters, type Character } from '../api/characters'
import { useAuth } from '../context/AuthContext'

const POLL_INTERVAL_MS = 5000

// ─── Simulation picker (shown when no :id in URL) ────────────────────────────

function SimulationPicker() {
  const [simulations, setSimulations] = useState<SimulationMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSimulations()
      .then((data) => setSimulations(data.simulations))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load simulations'),
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Loading simulations…
      </div>
    )
  }
  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        Error: {error}
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h2 className="text-xl font-semibold mb-4 text-white">Select a Simulation</h2>
      {simulations.length === 0 ? (
        <p className="text-gray-400">
          No simulations found. Create one from the{' '}
          <Link to="/" className="text-blue-400 hover:underline">
            home page
          </Link>
          .
        </p>
      ) : (
        <ul className="space-y-3">
          {simulations.map((sim) => (
            <li key={sim.id}>
              <Link
                to={`/simulate/${encodeURIComponent(sim.id)}`}
                className="block bg-gray-800 rounded-lg px-5 py-4 hover:bg-gray-700 transition-colors"
              >
                <div className="font-medium text-white">{sim.name}</div>
                {sim.curr_time && (
                  <div className="text-sm text-gray-400 mt-1">Time: {sim.curr_time}</div>
                )}
                <div className="text-sm text-gray-500 mt-1">
                  {sim.persona_names.length} agent{sim.persona_names.length !== 1 ? 's' : ''} · step{' '}
                  {sim.step}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ─── Agent sidebar card ───────────────────────────────────────────────────────

function AgentCard({ agent }: { agent: Agent }) {
  const location = agent.location
    ? `(${agent.location.x}, ${agent.location.y})`
    : 'Unknown'

  return (
    <div className="bg-gray-800 rounded-lg p-3 mb-3">
      <div className="font-semibold text-white text-sm">{agent.name}</div>
      {agent.currently && (
        <div className="text-xs text-gray-300 mt-1 leading-snug">{agent.currently}</div>
      )}
      <div className="text-xs text-gray-500 mt-1">Location: {location}</div>
    </div>
  )
}

// ─── Admin toolbar ────────────────────────────────────────────────────────────

function AdminToolbar({
  sim,
  onRefresh,
}: {
  sim: SimulationMeta
  onRefresh: () => void
}) {
  const [showDropModal, setShowDropModal] = useState(false)
  const [availableChars, setAvailableChars] = useState<Character[]>([])
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const openDropModal = async () => {
    try {
      const res = await fetchCharacters()
      setAvailableChars(res.characters.filter((c) => c.status === 'available'))
      setSelectedCharId(null)
      setShowDropModal(true)
    } catch {
      setActionError('Failed to load characters')
    }
  }

  const handleDrop = async () => {
    if (!selectedCharId) return
    setLoading(true)
    setActionError(null)
    try {
      await dropCharacter(sim.id, selectedCharId)
      setShowDropModal(false)
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to drop character')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    setActionError(null)
    try {
      await startSimulation(sim.id)
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to start')
    }
  }

  const handlePause = async () => {
    setActionError(null)
    try {
      await pauseSimulation(sim.id)
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to pause')
    }
  }

  const handleResume = async () => {
    setActionError(null)
    try {
      await resumeSimulation(sim.id)
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to resume')
    }
  }

  return (
    <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center gap-3">
      <span className="text-xs text-gray-400 font-medium uppercase">Admin</span>
      <button
        onClick={() => void openDropModal()}
        className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded transition-colors"
      >
        Drop Character
      </button>
      {sim.status !== 'running' && sim.status !== 'paused' && (
        <button
          onClick={() => void handleStart()}
          className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded transition-colors"
        >
          Start
        </button>
      )}
      {sim.status === 'running' && (
        <button
          onClick={() => void handlePause()}
          className="text-xs bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1 rounded transition-colors"
        >
          Pause
        </button>
      )}
      {sim.status === 'paused' && (
        <button
          onClick={() => void handleResume()}
          className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded transition-colors"
        >
          Resume
        </button>
      )}
      {actionError && <span className="text-xs text-red-400">{actionError}</span>}

      {showDropModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h3 className="text-white font-semibold mb-4">Drop Character</h3>
            {availableChars.length === 0 ? (
              <p className="text-gray-400 text-sm">No available characters.</p>
            ) : (
              <select
                value={selectedCharId ?? ''}
                onChange={(e) => setSelectedCharId(parseInt(e.target.value))}
                className="w-full rounded-lg border border-gray-600 bg-gray-700 text-white px-3 py-2 mb-4"
              >
                <option value="">Select a character…</option>
                {availableChars.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            )}
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDropModal(false)}
                className="text-sm text-gray-400 hover:text-white px-3 py-1"
              >
                Cancel
              </button>
              <button
                onClick={() => void handleDrop()}
                disabled={!selectedCharId || loading}
                className="text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-1 rounded"
              >
                {loading ? 'Dropping…' : 'Drop'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Full simulation viewer ───────────────────────────────────────────────────

function SimulationViewer({ simId }: { simId: string }) {
  const { user } = useAuth()
  const [meta, setMeta] = useState<SimulationMeta | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [step, setStep] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastPoll, setLastPoll] = useState<Date | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)

  const loadMeta = useCallback(() => {
    fetchSimulation(simId)
      .then((data) => {
        setMeta(data)
        // User is admin if they are the owner
        setIsAdmin(user !== null && data.owner === user.id)
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Simulation not found'),
      )
  }, [simId, user])

  const pollAgents = useCallback(() => {
    fetchSimulationAgents(simId)
      .then((data) => {
        setAgents(data.agents)
        setStep(data.step)
        setLastPoll(new Date())
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to fetch agents'),
      )
  }, [simId])

  // Initial load
  useEffect(() => {
    loadMeta()
    pollAgents()
  }, [simId, loadMeta, pollAgents])

  // Polling
  useEffect(() => {
    const interval = setInterval(pollAgents, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [pollAgents])

  if (error) {
    return (
      <div className="flex items-center justify-center flex-1 text-red-400">
        Error: {error}
      </div>
    )
  }

  const statusColors: Record<string, string> = {
    pending: 'bg-gray-600',
    running: 'bg-green-600',
    paused: 'bg-yellow-600',
    completed: 'bg-blue-600',
    failed: 'bg-red-600',
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Status bar + admin toolbar */}
      <div className="shrink-0">
        {meta && (
          <div className="flex items-center gap-3 px-4 py-1 bg-gray-800 border-b border-gray-700 text-xs">
            <span
              className={`inline-block px-2 py-0.5 rounded font-medium text-white ${statusColors[meta.status ?? 'pending'] ?? 'bg-gray-600'}`}
            >
              {meta.status ?? 'pending'}
            </span>
          </div>
        )}
        {meta && isAdmin && (
          <AdminToolbar sim={meta} onRefresh={() => { loadMeta(); pollAgents() }} />
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main canvas area */}
        <div className="flex-1 overflow-hidden relative">
          <GameCanvas className="w-full h-full" agents={agents} />
          <div className="absolute bottom-2 left-2 text-xs text-white bg-black/50 px-2 py-1 rounded pointer-events-none">
            Arrow keys to pan
          </div>
        </div>

        {/* Agent sidebar */}
        <aside className="w-64 shrink-0 bg-gray-900 border-l border-gray-700 overflow-y-auto p-3">
          <div className="mb-3">
            {meta?.curr_time && (
              <div className="text-xs text-gray-400 mb-1">
                <span className="font-medium text-gray-300">Time:</span> {meta.curr_time}
              </div>
            )}
            {step !== null && (
              <div className="text-xs text-gray-400 mb-1">
                <span className="font-medium text-gray-300">Step:</span> {step}
              </div>
            )}
            {lastPoll && (
              <div className="text-xs text-gray-600">
                Updated {lastPoll.toLocaleTimeString()}
              </div>
            )}
          </div>

          <hr className="border-gray-700 mb-3" />

          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Agents ({agents.length})
          </h2>

          {agents.length === 0 ? (
            <p className="text-xs text-gray-600">No agents found.</p>
          ) : (
            agents.map((agent) => <AgentCard key={agent.id} agent={agent} />)
          )}
        </aside>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SimulatePage() {
  const { id } = useParams<{ id?: string }>()

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-800 shrink-0 border-b border-gray-700">
        <Link to="/" className="text-blue-400 hover:underline text-sm">
          ← Back
        </Link>
        <h1 className="text-lg font-semibold">
          {id ? `Simulation: ${id}` : 'Simulation Viewer'}
        </h1>
        {id && (
          <p className="text-gray-400 text-sm ml-auto">
            Arrow keys to pan · Polls every 5s
          </p>
        )}
      </header>

      {id ? <SimulationViewer simId={id} /> : <SimulationPicker />}
    </div>
  )
}
