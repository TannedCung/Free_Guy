import { useEffect, useState, useCallback, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import GameCanvas from '../game/GameCanvas'
import {
  fetchSimulation,
  fetchSimulationAgents,
  fetchSimulations,
  fetchAgentDetail,
  dropCharacter,
  startSimulation,
  pauseSimulation,
  resumeSimulation,
  runSimulationStep,
  type Agent,
  type AgentDetail,
  type AgentPosition,
  type SimulationMeta,
} from '../api/simulations'
import { fetchCharacters, createCharacter, type Character } from '../api/characters'
import { useAuth } from '../context/AuthContext'
import { useSimulationSSE } from '../hooks/useSimulationSSE'

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
    <div className="max-w-3xl mx-auto p-4 md:p-8">
      <div className="retro-panel p-5">
        <h2 className="retro-title text-lg mb-2">Pick a simulation</h2>
        <p className="retro-subtitle text-sm mb-4">Choose one world to enter.</p>
      {simulations.length === 0 ? (
        <p className="retro-empty-state">
          No simulations found. Create one from the{' '}
          <Link to="/" className="retro-link">
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
                className="block retro-panel px-4 py-3"
              >
                <div className="font-semibold text-gray-900">{sim.name}</div>
                {sim.curr_time && (
                  <div className="text-sm text-gray-600 mt-1">Time: {sim.curr_time}</div>
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
    </div>
  )
}

// ─── Agent sidebar card ───────────────────────────────────────────────────────

function AgentCard({ agent }: { agent: Agent }) {
  const location = agent.location
    ? `(${agent.location.x}, ${agent.location.y})`
    : 'Unknown'

  return (
    <div className="retro-panel p-3 mb-3">
      <div className="font-semibold text-gray-900 text-sm">{agent.name}</div>
      {agent.currently && (
        <div className="text-xs text-gray-600 mt-1 leading-snug">{agent.currently}</div>
      )}
      <div className="text-xs text-gray-500 mt-1">Location: {location}</div>
    </div>
  )
}

// ─── Add Character Modal ──────────────────────────────────────────────────────

function AddCharacterModal({
  simId,
  spawnPos,
  onClose,
  onSuccess,
}: {
  simId: string
  spawnPos: { x: number; y: number } | null
  onClose: () => void
  onSuccess: () => void
}) {
  const [mode, setMode] = useState<'new' | 'existing'>('new')

  // New character form
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [traits, setTraits] = useState('')
  const [backstory, setBackstory] = useState('')
  const [currently, setCurrently] = useState('')
  const [lifestyle, setLifestyle] = useState('')
  const [livingArea, setLivingArea] = useState('')
  const [dailyPlan, setDailyPlan] = useState('')

  // Existing character selection
  const [availableChars, setAvailableChars] = useState<Character[]>([])
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null)
  const [charsLoading, setCharsLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (mode === 'existing') {
      setCharsLoading(true)
      fetchCharacters()
        .then((res) => setAvailableChars(res.characters.filter((c) => c.status === 'available')))
        .catch(() => setError('Failed to load characters'))
        .finally(() => setCharsLoading(false))
    }
  }, [mode])

  const handleSubmitNew = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const char = await createCharacter({
        name,
        age: age ? parseInt(age, 10) : undefined,
        traits,
        backstory,
        currently,
        lifestyle,
        living_area: livingArea,
        daily_plan: dailyPlan,
      })
      await dropCharacter(simId, char.id)
      onSuccess()
      onClose()
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'name' in err) {
        const fieldErr = err as Record<string, string[]>
        const firstKey = Object.keys(fieldErr)[0]
        setError(firstKey ? `${firstKey}: ${fieldErr[firstKey]?.join(', ')}` : 'Failed to add character')
      } else {
        setError(err instanceof Error ? err.message : 'Failed to add character')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDropExisting = async () => {
    if (!selectedCharId) return
    setLoading(true)
    setError(null)
    try {
      await dropCharacter(simId, selectedCharId)
      onSuccess()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to drop character')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="retro-panel p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-1">
          <h3 className="font-semibold text-gray-900">Add Character</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {spawnPos && (
          <p className="text-xs text-gray-500 mb-4">
            Spawn position: tile ({spawnPos.x}, {spawnPos.y})
          </p>
        )}

        {/* Mode tabs */}
        <div className="flex gap-0 mb-5 border-b border-gray-200">
          <button
            onClick={() => setMode('new')}
            className={`pb-2 px-3 text-sm font-medium transition-colors ${
              mode === 'new'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            New Character
          </button>
          <button
            onClick={() => setMode('existing')}
            className={`pb-2 px-3 text-sm font-medium transition-colors ${
              mode === 'existing'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Existing Character
          </button>
        </div>

        {/* New character form */}
        {mode === 'new' && (
          <form onSubmit={(e) => void handleSubmitNew(e)} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Isabella Rodriguez"
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Age</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="e.g. 34"
                className="retro-input"
                min={0}
                max={120}
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Traits</label>
              <textarea
                value={traits}
                onChange={(e) => setTraits(e.target.value)}
                placeholder="e.g. kind, curious, hardworking"
                rows={2}
                className="retro-input resize-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Backstory</label>
              <textarea
                value={backstory}
                onChange={(e) => setBackstory(e.target.value)}
                placeholder="Background and history…"
                rows={2}
                className="retro-input resize-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Currently</label>
              <input
                value={currently}
                onChange={(e) => setCurrently(e.target.value)}
                placeholder="e.g. working at the café"
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Lifestyle</label>
              <input
                value={lifestyle}
                onChange={(e) => setLifestyle(e.target.value)}
                placeholder="e.g. early riser, healthy diet"
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Lives in</label>
              <input
                value={livingArea}
                onChange={(e) => setLivingArea(e.target.value)}
                placeholder="e.g. Oak Hill Apartments:Apt 2"
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Daily plan</label>
              <textarea
                value={dailyPlan}
                onChange={(e) => setDailyPlan(e.target.value)}
                placeholder="Typical daily schedule…"
                rows={2}
                className="retro-input resize-none"
              />
            </div>

            {error && (
              <p className="text-red-500 text-xs">{error}</p>
            )}

            <div className="flex gap-2 justify-end pt-1">
              <button
                type="button"
                onClick={onClose}
                className="retro-button retro-button-ghost text-xs py-1 px-3"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="retro-button retro-button-primary text-xs py-1 px-3"
              >
                {loading ? 'Adding…' : 'Add Character'}
              </button>
            </div>
          </form>
        )}

        {/* Existing character */}
        {mode === 'existing' && (
          <div>
            {charsLoading ? (
              <p className="text-sm text-gray-500">Loading characters…</p>
            ) : availableChars.length === 0 ? (
              <p className="text-sm text-gray-500">No available characters. Create one first.</p>
            ) : (
              <select
                value={selectedCharId ?? ''}
                onChange={(e) => setSelectedCharId(parseInt(e.target.value, 10))}
                className="retro-select w-full mb-4"
              >
                <option value="">Select a character…</option>
                {availableChars.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}{c.age ? ` (${c.age})` : ''}
                  </option>
                ))}
              </select>
            )}

            {error && <p className="text-red-500 text-xs mb-2">{error}</p>}

            <div className="flex gap-2 justify-end">
              <button
                onClick={onClose}
                className="retro-button retro-button-ghost text-xs py-1 px-3"
              >
                Cancel
              </button>
              <button
                onClick={() => void handleDropExisting()}
                disabled={!selectedCharId || loading || charsLoading}
                className="retro-button retro-button-primary text-xs py-1 px-3"
              >
                {loading ? 'Adding…' : 'Add Character'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Admin toolbar ────────────────────────────────────────────────────────────

function AdminToolbar({
  sim,
  onRefresh,
  onEnterDropMode,
}: {
  sim: SimulationMeta
  onRefresh: () => void
  onEnterDropMode: () => void
}) {
  const [actionError, setActionError] = useState<string | null>(null)

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
    <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center gap-3 flex-wrap">
      <span className="text-xs text-gray-400 font-medium uppercase">Admin</span>
      <Link
        to={`/simulate/${encodeURIComponent(sim.id)}/settings`}
        className="retro-button retro-button-ghost text-xs py-1 px-3"
      >
        Settings
      </Link>
      <button
        onClick={onEnterDropMode}
        className="retro-button retro-button-primary text-xs py-1 px-3"
      >
        + Add Character
      </button>
      {sim.status !== 'running' && sim.status !== 'paused' && (
        <button
          onClick={() => void handleStart()}
          className="retro-button retro-button-warm text-xs py-1 px-3"
        >
          Start
        </button>
      )}
      {sim.status === 'running' && (
        <button
          onClick={() => void handlePause()}
          className="retro-button text-xs py-1 px-3 bg-yellow-600 hover:bg-yellow-700 text-white"
        >
          Pause
        </button>
      )}
      {sim.status === 'paused' && (
        <button
          onClick={() => void handleResume()}
          className="retro-button retro-button-warm text-xs py-1 px-3"
        >
          Resume
        </button>
      )}
      {actionError && <span className="text-xs text-red-400">{actionError}</span>}
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
  const [wsError, setWsError] = useState<string | null>(null)
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [agentDetail, setAgentDetail] = useState<AgentDetail | null>(null)

  // Drop-mode state
  const [dropMode, setDropMode] = useState(false)
  const [spawnPos, setSpawnPos] = useState<{ x: number; y: number } | null>(null)
  const [showAddCharModal, setShowAddCharModal] = useState(false)

  // Step orchestration loop (Vercel serverless mode)
  const stepLoopActiveRef = useRef(false)
  const agentPositionsRef = useRef<Record<string, AgentPosition>>({})

  const loadMeta = useCallback(() => {
    fetchSimulation(simId)
      .then((data) => {
        setMeta(data)
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

  const handleStepUpdate = useCallback((payload: { step?: number; sim_curr_time?: string }) => {
    if (payload.step !== undefined) setStep(payload.step)
    setLastPoll(new Date())
    void pollAgents()
  }, [pollAgents])

  const { wsStatus } = useSimulationSSE({
    simId,
    onStepUpdate: handleStepUpdate,
    onForbidden: () => setWsError('Access denied'),
    onAuthError: () => setWsError('Authentication error — please refresh'),
  })

  const selectAgent = useCallback((agentId: string | null) => {
    setSelectedAgentId(agentId)
    if (!agentId) { setAgentDetail(null); return }
    fetchAgentDetail(simId, agentId)
      .then(setAgentDetail)
      .catch(() => setAgentDetail(null))
  }, [simId])

  // Refresh agent detail on step updates
  useEffect(() => {
    if (selectedAgentId) {
      fetchAgentDetail(simId, selectedAgentId)
        .then(setAgentDetail)
        .catch(() => {/* ignore */})
    }
  }, [step, simId, selectedAgentId])

  // ESC closes drop mode, modals, and agent detail panel
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (dropMode) { setDropMode(false); return }
        if (showAddCharModal) { setShowAddCharModal(false); setSpawnPos(null); return }
        selectAgent(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [selectAgent, dropMode, showAddCharModal])

  // Keep agentPositionsRef in sync
  useEffect(() => {
    const positions: Record<string, AgentPosition> = {}
    for (const agent of agents) {
      if (agent.location) {
        positions[agent.name] = { x: agent.location.x, y: agent.location.y }
      }
    }
    agentPositionsRef.current = positions
  }, [agents])

  // Initial load
  useEffect(() => {
    loadMeta()
    pollAgents()
  }, [simId, loadMeta, pollAgents])

  // Polling (fallback when SSE is not connected)
  useEffect(() => {
    if (wsStatus === 'connected') return
    const interval = setInterval(pollAgents, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [pollAgents, wsStatus])

  // ── Step orchestration loop ────────────────────────────────────────────
  const runStepLoop = useCallback(async () => {
    if (stepLoopActiveRef.current) return
    stepLoopActiveRef.current = true
    try {
      while (stepLoopActiveRef.current) {
        const latestMeta = await fetchSimulation(simId).catch(() => null)
        if (!latestMeta || latestMeta.status !== 'running') break

        const currentStep = latestMeta.step ?? 0
        const positions = agentPositionsRef.current

        try {
          const result = await runSimulationStep(simId, positions, currentStep, (stage) => {
            if (stage === 'execute') pollAgents()
          })
          if (result.next_step !== undefined) setStep(result.next_step)
        } catch (err: unknown) {
          console.error('[stepLoop] stage error:', err)
          await new Promise((r) => setTimeout(r, 3000))
        }
      }
    } finally {
      stepLoopActiveRef.current = false
    }
  }, [simId, pollAgents])

  useEffect(() => {
    if (!isAdmin || meta?.status !== 'running') {
      stepLoopActiveRef.current = false
      return
    }
    void runStepLoop()
    return () => {
      stepLoopActiveRef.current = false
    }
  }, [isAdmin, meta?.status, runStepLoop])

  // Map click handler (called by GameCanvas when in drop mode)
  const handleMapClick = useCallback((tileX: number, tileY: number) => {
    setSpawnPos({ x: tileX, y: tileY })
    setDropMode(false)
    setShowAddCharModal(true)
  }, [])

  const [sidebarTab, setSidebarTab] = useState<'agents' | 'debug'>('agents')

  const statusColors: Record<string, string> = {
    pending: 'bg-gray-600',
    running: 'bg-green-600 text-gray-900',
    paused: 'bg-yellow-600',
    completed: 'bg-blue-600 text-gray-900',
    failed: 'bg-red-600',
  }

  if (error) {
    return (
      <div className="flex items-center justify-center flex-1 text-red-400">
        Error: {error}
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Status bar + admin toolbar */}
      <div className="shrink-0">
        {meta && (
          <div className="flex items-center gap-3 px-4 py-1 bg-gray-800 border-b border-gray-700 text-xs">
            <span
              className={`inline-block px-2 py-0.5 retro-badge font-medium text-white ${statusColors[meta.status ?? 'pending'] ?? 'bg-gray-600'}`}
            >
              {meta.status ?? 'pending'}
            </span>
            <span
              className={`ml-auto flex items-center gap-1 ${wsStatus === 'connected' ? 'text-green-400' : 'text-gray-500'}`}
            >
              <span
                className={`inline-block w-2 h-2 rounded-full ${wsStatus === 'connected' ? 'bg-green-400' : 'bg-gray-500'}`}
              />
              {wsStatus === 'connected' ? 'Live' : 'Disconnected'}
            </span>
            {wsError && <span className="text-red-400">{wsError}</span>}
          </div>
        )}
        {meta && isAdmin && (
          <AdminToolbar
            sim={meta}
            onRefresh={() => { loadMeta(); void pollAgents() }}
            onEnterDropMode={() => setDropMode(true)}
          />
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main canvas area */}
        <div className="flex-1 overflow-hidden relative">
          <GameCanvas
            className="w-full h-full"
            agents={agents}
            dropMode={dropMode}
            onMapClick={handleMapClick}
          />

          {/* Drop-mode placement banner */}
          {dropMode && (
            <div className="absolute top-3 left-0 right-0 flex justify-center z-10 pointer-events-none">
              <div className="bg-black/75 text-white text-sm px-5 py-2 rounded-full flex items-center gap-3">
                <span>Click on the map to place your character</span>
                <button
                  className="pointer-events-auto text-gray-300 hover:text-white font-bold text-base leading-none"
                  onClick={() => setDropMode(false)}
                >
                  ×
                </button>
              </div>
            </div>
          )}

          <div className="absolute bottom-2 left-2 text-xs text-white bg-black/50 px-2 py-1 rounded pointer-events-none">
            Arrow keys to pan
          </div>
        </div>

        {/* Agent sidebar */}
        <aside className="w-64 shrink-0 bg-gray-900 border-l border-gray-700 flex flex-col">
          {/* Tab buttons */}
          <div className="flex shrink-0 border-b border-gray-700">
            <button
              onClick={() => setSidebarTab('agents')}
              className={`flex-1 py-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
                sidebarTab === 'agents'
                  ? 'retro-button-primary text-white bg-blue-700 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Agents
            </button>
            <button
              onClick={() => setSidebarTab('debug')}
              className={`flex-1 py-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
                sidebarTab === 'debug'
                  ? 'retro-button-primary text-white bg-blue-700 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Debug
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {sidebarTab === 'agents' && (
              <>
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
                  agents.map((agent) => (
                    <button
                      key={agent.id}
                      onClick={() => selectAgent(agent.id)}
                      className="w-full text-left"
                    >
                      <AgentCard agent={agent} />
                    </button>
                  ))
                )}
              </>
            )}

            {sidebarTab === 'debug' && (
              <div>Debug view coming soon</div>
            )}
          </div>
        </aside>
      </div>

      {/* Add Character modal */}
      {showAddCharModal && meta && (
        <AddCharacterModal
          simId={meta.id}
          spawnPos={spawnPos}
          onClose={() => { setShowAddCharModal(false); setSpawnPos(null) }}
          onSuccess={() => { loadMeta(); void pollAgents() }}
        />
      )}

      {/* Agent detail panel */}
      {agentDetail && (
        <div
          className="fixed inset-0 bg-black/40 z-40"
          onClick={() => selectAgent(null)}
        >
          <aside
            className="absolute right-0 top-0 h-full w-80 bg-gray-900 border-l border-gray-700 overflow-y-auto p-4 z-50"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">{agentDetail.name}</h2>
              <button
                onClick={() => selectAgent(null)}
                className="text-gray-400 hover:text-white text-lg leading-none"
              >
                ×
              </button>
            </div>

            {agentDetail.act_description && (
              <div className="mb-3">
                <div className="text-xs font-medium text-gray-400 uppercase mb-1">Current Action</div>
                <p className="text-xs text-gray-200">{agentDetail.act_description}</p>
              </div>
            )}

            {agentDetail.chatting_with && (
              <div className="mb-3">
                <div className="text-xs font-medium text-gray-400 uppercase mb-1">Chatting With</div>
                <p className="text-xs text-gray-200">{agentDetail.chatting_with}</p>
              </div>
            )}

            {agentDetail.daily_req.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-medium text-gray-400 uppercase mb-1">Today&apos;s Plan</div>
                <ul className="text-xs text-gray-300 space-y-0.5 list-disc list-inside">
                  {agentDetail.daily_req.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {agentDetail.recent_concepts.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-400 uppercase mb-1">Recent Memories</div>
                <ul className="text-xs text-gray-400 space-y-1">
                  {agentDetail.recent_concepts.map((c) => (
                    <li key={c.node_id} className="border-l-2 border-gray-700 pl-2">
                      {c.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SimulatePage() {
  const { id } = useParams<{ id?: string }>()

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-800 shrink-0 border-b border-gray-700">
        <Link to="/" className="retro-link text-sm">
          ← Back
        </Link>
        <h1 className="text-lg font-semibold uppercase tracking-wide">
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
