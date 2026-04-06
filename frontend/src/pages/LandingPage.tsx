import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function LandingPage() {
  const [simName, setSimName] = useState('')
  const [forkFrom, setForkFrom] = useState('')

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: wire to POST /api/v1/simulations/ in US-032
    alert(`Creating simulation: ${simName}${forkFrom ? ` (forked from ${forkFrom})` : ''}`)
  }

  return (
    <div className="retro-page">
      <header className="retro-header">
        <div className="retro-header-inner flex flex-wrap items-center justify-between gap-3">
          <h1 className="retro-brand">Reverie Pixel Town</h1>
          <nav className="flex flex-wrap gap-2">
            <Link to="/login" className="retro-navlink">
              Sign in
            </Link>
            <Link to="/register" className="retro-navlink">
              Register
            </Link>
            <Link to="/simulate" className="retro-navlink">
              Simulator
            </Link>
            <Link to="/demo" className="retro-navlink">
              Demo replay
            </Link>
          </nav>
        </div>
      </header>

      <main className="retro-main">
        <section className="retro-panel p-6 md:p-8 mb-6">
          <h2 className="retro-title mb-3">Pixel-style agent playground</h2>
          <p className="retro-subtitle mb-5 max-w-3xl">
            Follow three easy steps: create your simulation, drop characters, then watch your town
            come alive in a retro map view.
          </p>
          <div className="retro-steps max-w-3xl">
            <div className="retro-step-item">
              <span className="retro-step-count">1</span>
              <p className="text-sm">Sign in and create a simulation from your dashboard.</p>
            </div>
            <div className="retro-step-item">
              <span className="retro-step-count">2</span>
              <p className="text-sm">Add or invite characters to your simulation.</p>
            </div>
            <div className="retro-step-item">
              <span className="retro-step-count">3</span>
              <p className="text-sm">Open live simulator or replay mode to observe behavior.</p>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <Link to="/simulate" className="retro-panel block p-5">
            <h3 className="retro-title text-lg mb-2">Live simulation</h3>
            <p className="retro-subtitle text-sm mb-3">
              Watch agents walk, chat, and plan in real time.
            </p>
            <span className="retro-link">Open live simulator</span>
          </Link>

          <Link to="/demo" className="retro-panel block p-5">
            <h3 className="retro-title text-lg mb-2">Demo replay</h3>
            <p className="retro-subtitle text-sm mb-3">
              Replay saved sessions with easy controls and timeline scrubber.
            </p>
            <span className="retro-link">Open replay viewer</span>
          </Link>
        </section>

        <section className="retro-panel p-6 md:p-8">
          <h3 className="retro-title text-lg mb-5">Quick simulation name tester</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label htmlFor="sim-name" className="block text-xs font-bold uppercase mb-1">
                Simulation name <span className="text-red-500">*</span>
              </label>
              <input
                id="sim-name"
                type="text"
                required
                value={simName}
                onChange={(e) => setSimName(e.target.value)}
                placeholder="my_ville_experiment"
                className="retro-input"
              />
            </div>

            <div>
              <label htmlFor="fork-from" className="block text-xs font-bold uppercase mb-1">
                Fork from (optional)
              </label>
              <input
                id="fork-from"
                type="text"
                value={forkFrom}
                onChange={(e) => setForkFrom(e.target.value)}
                placeholder="base_the_ville..."
                className="retro-input"
              />
              <p className="mt-1 text-xs text-gray-500">Leave empty to start fresh.</p>
            </div>

            <button type="submit" className="retro-button retro-button-warm">
              Create simulation
            </button>
          </form>
        </section>
      </main>

      <footer className="py-6 text-center text-xs text-gray-500">
        Reverie research playground
      </footer>
    </div>
  )
}
