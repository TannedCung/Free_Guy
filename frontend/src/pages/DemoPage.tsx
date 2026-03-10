import { useEffect, useState, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import GameCanvas from '../game/GameCanvas'
import {
  fetchDemos,
  fetchDemoStep,
  type Agent,
  type DemoMeta,
  type DemoStepResponse,
} from '../api/simulations'

// Minimum ms between automatic step advances (avoids API hammering)
const MIN_STEP_INTERVAL_MS = 500

type PlaybackSpeed = 1 | 2 | 4

// ─── Demo picker ──────────────────────────────────────────────────────────────

function DemoPicker() {
  const [demos, setDemos] = useState<DemoMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDemos()
      .then((data) => setDemos(data.demos))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load demos'),
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Loading demos…
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
      <h2 className="text-xl font-semibold mb-4 text-white">Select a Demo</h2>
      {demos.length === 0 ? (
        <p className="text-gray-400">No demos found in compressed_storage/.</p>
      ) : (
        <ul className="space-y-3">
          {demos.map((demo) => (
            <li key={demo.id}>
              <Link
                to={`/demo/${encodeURIComponent(demo.id)}`}
                className="block bg-gray-800 rounded-lg px-5 py-4 hover:bg-gray-700 transition-colors"
              >
                <div className="font-medium text-white">{demo.name}</div>
                {demo.start_date && (
                  <div className="text-sm text-gray-400 mt-1">Start: {demo.start_date}</div>
                )}
                <div className="text-sm text-gray-500 mt-1">
                  {demo.persona_names.length} agent{demo.persona_names.length !== 1 ? 's' : ''}
                  {demo.total_steps != null ? ` · ${demo.total_steps} steps` : ''}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ─── Agent card in sidebar ────────────────────────────────────────────────────

function DemoAgentCard({
  name,
  pronunciatio,
  description,
}: {
  name: string
  pronunciatio: string
  description: string
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 mb-3">
      <div className="flex items-center gap-2">
        <span className="text-lg" aria-hidden="true">
          {pronunciatio}
        </span>
        <span className="font-semibold text-white text-sm">{name}</span>
      </div>
      {description && (
        <div className="text-xs text-gray-400 mt-1 leading-snug">{description}</div>
      )}
    </div>
  )
}

// ─── Demo viewer ──────────────────────────────────────────────────────────────

function DemoViewer({ demoId }: { demoId: string }) {
  const [meta, setMeta] = useState<DemoMeta | null>(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [stepData, setStepData] = useState<DemoStepResponse | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState<PlaybackSpeed>(1)
  const [error, setError] = useState<string | null>(null)

  const totalSteps = meta?.total_steps ?? null
  const maxStep = totalSteps != null ? totalSteps - 1 : 0

  // Fetch demo metadata on mount
  useEffect(() => {
    fetchDemos()
      .then((data) => {
        const found = data.demos.find((d) => d.id === demoId)
        if (found) setMeta(found)
        else setError(`Demo '${demoId}' not found`)
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load demo metadata'),
      )
  }, [demoId])

  // Fetch step data whenever currentStep changes
  useEffect(() => {
    let cancelled = false
    fetchDemoStep(demoId, currentStep)
      .then((data) => {
        if (cancelled) return
        setStepData(data)
        const mapped: Agent[] = Object.entries(data.agents).map(([name, state]) => ({
          id: name,
          name,
          first_name: null,
          last_name: null,
          age: null,
          innate: null,
          currently: state.description,
          location: { maze: '', x: state.movement[0], y: state.movement[1] },
          pronunciatio: state.pronunciatio,
        }))
        setAgents(mapped)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        // If step is beyond the end, stop playback gracefully
        if (err instanceof Error && err.message.includes('404')) {
          setIsPlaying(false)
        } else {
          setError(err instanceof Error ? err.message : 'Failed to fetch step')
        }
      })
    return () => {
      cancelled = true
    }
  }, [demoId, currentStep])

  // Playback timer
  const playTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (playTimerRef.current) {
      clearInterval(playTimerRef.current)
      playTimerRef.current = null
    }
    if (!isPlaying) return

    const intervalMs = Math.max(MIN_STEP_INTERVAL_MS / speed, 125)
    playTimerRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        const next = prev + 1
        if (totalSteps != null && next >= totalSteps) {
          setIsPlaying(false)
          return prev
        }
        return next
      })
    }, intervalMs)

    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current)
    }
  }, [isPlaying, speed, totalSteps])

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const step = parseInt(e.target.value, 10)
    setIsPlaying(false)
    setCurrentStep(step)
  }

  const stepBack = () => {
    setIsPlaying(false)
    setCurrentStep((prev) => Math.max(0, prev - 1))
  }

  const stepForward = () => {
    setIsPlaying(false)
    setCurrentStep((prev) => (totalSteps != null ? Math.min(maxStep, prev + 1) : prev + 1))
  }

  const togglePlay = () => setIsPlaying((prev) => !prev)

  const cycleSpeed = () => {
    setSpeed((prev) => (prev === 1 ? 2 : prev === 2 ? 4 : 1))
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
      {/* Main area: canvas + sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Game canvas */}
        <div className="flex-1 overflow-hidden relative">
          <GameCanvas className="w-full h-full" agents={agents} />
          <div className="absolute bottom-2 left-2 text-xs text-white bg-black/50 px-2 py-1 rounded pointer-events-none">
            Arrow keys to pan
          </div>
        </div>

        {/* Agent sidebar */}
        <aside className="w-64 shrink-0 bg-gray-900 border-l border-gray-700 overflow-y-auto p-3">
          <div className="mb-3">
            {stepData && (
              <div className="text-xs text-gray-400 mb-1">
                <span className="font-medium text-gray-300">Step:</span> {stepData.step}
                {totalSteps != null && (
                  <span className="text-gray-600"> / {totalSteps}</span>
                )}
              </div>
            )}
            {meta?.start_date && (
              <div className="text-xs text-gray-400 mb-1">
                <span className="font-medium text-gray-300">Start:</span> {meta.start_date}
              </div>
            )}
          </div>

          <hr className="border-gray-700 mb-3" />

          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Agents ({agents.length})
          </h2>

          {agents.length === 0 ? (
            <p className="text-xs text-gray-600">No agent data for this step.</p>
          ) : (
            agents.map((agent) => (
              <DemoAgentCard
                key={agent.id}
                name={agent.name}
                pronunciatio={agent.pronunciatio ?? ''}
                description={agent.currently ?? ''}
              />
            ))
          )}
        </aside>
      </div>

      {/* Playback controls bar */}
      <div className="shrink-0 bg-gray-800 border-t border-gray-700 px-4 py-2 flex items-center gap-3">
        {/* Step back */}
        <button
          onClick={stepBack}
          disabled={currentStep === 0}
          className="px-2 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-40 rounded"
          title="Step back"
        >
          ◀
        </button>

        {/* Play / Pause */}
        <button
          onClick={togglePlay}
          className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-500 rounded font-medium"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>

        {/* Step forward */}
        <button
          onClick={stepForward}
          disabled={totalSteps != null && currentStep >= maxStep}
          className="px-2 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-40 rounded"
          title="Step forward"
        >
          ▶
        </button>

        {/* Speed toggle */}
        <button
          onClick={cycleSpeed}
          className="px-2 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded"
          title="Playback speed"
        >
          {speed}×
        </button>

        {/* Timeline scrubber */}
        <div className="flex items-center gap-2 flex-1">
          <span className="text-xs text-gray-400 shrink-0">Step {currentStep}</span>
          <input
            type="range"
            min={0}
            max={maxStep}
            value={currentStep}
            onChange={handleScrub}
            className="flex-1 accent-blue-500"
            title="Timeline scrubber"
          />
          {totalSteps != null && (
            <span className="text-xs text-gray-400 shrink-0">{totalSteps}</span>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DemoPage() {
  const { id } = useParams<{ id?: string }>()

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-800 shrink-0 border-b border-gray-700">
        <Link to="/" className="text-blue-400 hover:underline text-sm">
          ← Back
        </Link>
        <h1 className="text-lg font-semibold">
          {id ? `Demo: ${id}` : 'Demo Viewer'}
        </h1>
        {id && (
          <p className="text-gray-400 text-sm ml-auto">
            Arrow keys to pan · Use controls to play/pause
          </p>
        )}
      </header>

      {id ? <DemoViewer demoId={id} /> : <DemoPicker />}
    </div>
  )
}
