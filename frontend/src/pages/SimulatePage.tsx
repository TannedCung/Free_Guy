import { Link } from 'react-router-dom'
import GameCanvas from '../game/GameCanvas'

export default function SimulatePage() {
  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-800 shrink-0">
        <Link to="/" className="text-blue-400 hover:underline text-sm">
          ← Back
        </Link>
        <h1 className="text-lg font-semibold">Simulation Viewer</h1>
        <p className="text-gray-400 text-sm ml-auto">
          Use arrow keys to pan · Game canvas powered by Phaser 3
        </p>
      </header>
      <main className="flex-1 overflow-hidden">
        <GameCanvas className="w-full h-full" />
      </main>
    </div>
  )
}
