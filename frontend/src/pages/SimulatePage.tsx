import { useEffect, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import GameCanvas from '../game/GameCanvas'
import {
  fetchSimulation,
  fetchSimulationAgents,
  fetchSimulations,
  type Agent,
  type SimulationMeta,
} from '../api/simulations'

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

// ─── Full simulation viewer ───────────────────────────────────────────────────

function SimulationViewer({ simId }: { simId: string }) {
  const [meta, setMeta] = useState<SimulationMeta | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [step, setStep] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastPoll, setLastPoll] = useState<Date | null>(null)

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
    fetchSimulation(simId)
      .then(setMeta)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Simulation not found'),
      )
    pollAgents()
  }, [simId, pollAgents])

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

  return (
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
