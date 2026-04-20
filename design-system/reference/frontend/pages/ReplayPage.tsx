import { useEffect, useRef, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import GameCanvas from '../game/GameCanvas'
import {
  fetchReplayMeta,
  fetchReplayStep,
  fetchSimulation,
  type ReplayMeta,
  type ReplayStepResponse,
  type SimulationMeta,
  type Agent,
} from '../api/simulations'

const SPEED_INTERVALS: Record<number, number> = { 1: 1000, 2: 500, 5: 200 }

function replayAgentsToAgents(stepData: ReplayStepResponse): Agent[] {
  return Object.entries(stepData.agents).map(([name, state]) => ({
    id: name,
    name,
    first_name: null,
    last_name: null,
    age: null,
    innate: null,
    currently: state.description,
    pronunciatio: state.pronunciatio,
    location: { maze: '', x: state.x, y: state.y },
  }))
}

export default function ReplayPage() {
  const { id } = useParams<{ id: string }>()
  const simId = id ?? ''

  const [meta, setMeta] = useState<ReplayMeta | null>(null)
  const [sim, setSim] = useState<SimulationMeta | null>(null)
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [stepData, setStepData] = useState<ReplayStepResponse | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<1 | 2 | 5>(1)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const playIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load replay meta and sim meta
  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(() => {
      Promise.all([fetchReplayMeta(simId), fetchSimulation(simId)])
        .then(([replayMeta, simData]) => {
          if (cancelled) return
          setMeta(replayMeta)
          setSim(simData)
          setCurrentStep(replayMeta.first_step)
        })
        .catch((err: unknown) =>
          setError(err instanceof Error ? err.message : 'Failed to load replay'),
        )
        .finally(() => { if (!cancelled) setLoading(false) })
    }, 0)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [simId])

  // Load step data when currentStep changes
  const loadStep = useCallback((step: number) => {
    fetchReplayStep(simId, step)
      .then((data) => {
        setStepData(data)
        setAgents(replayAgentsToAgents(data))
      })
      .catch(() => {/* ignore missing steps */})
  }, [simId])

  useEffect(() => {
    if (meta) loadStep(currentStep)
  }, [currentStep, meta, loadStep])

  // Playback
  useEffect(() => {
    if (!playing || !meta) return
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= meta.last_step) {
          setPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, SPEED_INTERVALS[speed])
    playIntervalRef.current = interval
    return () => clearInterval(interval)
  }, [playing, speed, meta])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-gray-400">
        Loading replay…
      </div>
    )
  }

  if (error || !meta) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-red-400">
        {error ?? 'No replay data available'}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-800 shrink-0 border-b border-gray-700">
        <Link
          to={`/simulate/${encodeURIComponent(simId)}`}
          className="retro-link text-sm"
        >
          ← Back
        </Link>
        <h1 className="text-lg font-semibold uppercase tracking-wide">Replay: {simId}</h1>
        {sim?.status === 'running' && (
          <Link
            to={`/simulate/${encodeURIComponent(simId)}`}
            className="ml-auto retro-button retro-button-warm"
          >
            Watch Live
          </Link>
        )}
      </header>

      {/* Step info */}
      <div className="shrink-0 px-4 py-2 bg-gray-800 border-b border-gray-700 text-xs text-gray-300 flex items-center gap-4 uppercase tracking-wide">
        <span>Step: <strong>{currentStep}</strong></span>
        {stepData?.sim_curr_time && (
          <span>Time: <strong>{stepData.sim_curr_time}</strong></span>
        )}
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-hidden">
        <GameCanvas className="w-full h-full" agents={agents} />
      </div>

      {/* Controls */}
      <div className="shrink-0 bg-gray-800 border-t border-gray-700 px-4 py-3 flex flex-col gap-2">
        <input
          type="range"
          min={meta.first_step}
          max={meta.last_step}
          value={currentStep}
          onChange={(e) => {
            setPlaying(false)
            setCurrentStep(parseInt(e.target.value))
          }}
          className="w-full accent-blue-500"
        />
        <div className="flex items-center gap-3">
          {playing ? (
            <button
              onClick={() => setPlaying(false)}
              className="retro-button text-sm bg-yellow-600 hover:bg-yellow-700 text-white"
            >
              Pause
            </button>
          ) : (
            <button
              onClick={() => setPlaying(true)}
              disabled={currentStep >= meta.last_step}
              className="retro-button retro-button-warm text-sm disabled:opacity-50"
            >
              Play
            </button>
          )}
          <label className="text-xs text-gray-400 uppercase tracking-wide">Speed:</label>
          {([1, 2, 5] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`retro-button text-xs ${speed === s ? 'retro-button-primary' : 'retro-button-ghost text-gray-300 hover:bg-gray-600'}`}
            >
              {s}x
            </button>
          ))}
          <span className="ml-auto text-xs text-gray-500">
            {currentStep} / {meta.last_step}
          </span>
        </div>
      </div>
    </div>
  )
}
