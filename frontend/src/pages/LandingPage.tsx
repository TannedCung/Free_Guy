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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-5 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Generative Agents — Reverie</h1>
          <nav className="flex gap-6">
            <Link to="/simulate" className="text-blue-600 hover:text-blue-800 font-medium">
              Simulator
            </Link>
            <Link to="/demo" className="text-blue-600 hover:text-blue-800 font-medium">
              Demo Viewer
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="max-w-5xl mx-auto px-4 py-12">
        <section className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Generative Agent Simulations
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            A sandbox environment for simulating believable human behavior using large language
            models. Agents plan, reflect, converse, and act autonomously in a virtual world.
          </p>
        </section>

        {/* Quick links */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <Link
            to="/simulate"
            className="block bg-white rounded-xl shadow p-6 hover:shadow-md transition-shadow border border-gray-100"
          >
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Live Simulation</h3>
            <p className="text-gray-600">
              Watch agents navigate The Ville in real time, observe their decisions, and inspect
              their memory and plans.
            </p>
            <span className="mt-4 inline-block text-blue-600 font-medium">Open simulator →</span>
          </Link>

          <Link
            to="/demo"
            className="block bg-white rounded-xl shadow p-6 hover:shadow-md transition-shadow border border-gray-100"
          >
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Demo Replay</h3>
            <p className="text-gray-600">
              Replay pre-recorded simulations with full playback controls — pause, rewind, and
              inspect each simulation step.
            </p>
            <span className="mt-4 inline-block text-blue-600 font-medium">Open demo viewer →</span>
          </Link>
        </section>

        {/* Create / Fork form */}
        <section className="bg-white rounded-xl shadow p-8 border border-gray-100">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">
            Create or Fork a Simulation
          </h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label htmlFor="sim-name" className="block text-sm font-medium text-gray-700 mb-1">
                Simulation Name <span className="text-red-500">*</span>
              </label>
              <input
                id="sim-name"
                type="text"
                required
                value={simName}
                onChange={(e) => setSimName(e.target.value)}
                placeholder="e.g. my_ville_experiment"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="fork-from" className="block text-sm font-medium text-gray-700 mb-1">
                Fork From (optional)
              </label>
              <input
                id="fork-from"
                type="text"
                value={forkFrom}
                onChange={(e) => setForkFrom(e.target.value)}
                placeholder="e.g. base_the_ville_isabella_maria_klaus"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-sm text-gray-500">
                Leave blank to start a fresh simulation.
              </p>
            </div>

            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-2 rounded-lg transition-colors"
            >
              Create Simulation
            </button>
          </form>
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-16 py-8 text-center text-sm text-gray-400">
        Generative Agents — Stanford University Research Project
      </footer>
    </div>
  )
}
