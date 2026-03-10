import { Link } from 'react-router-dom'

export default function SimulatePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-bold text-gray-900">Simulation Viewer</h1>
      <p className="text-gray-600">Coming soon — see US-031 (GameCanvas) and US-034 (simulation viewer).</p>
      <Link to="/" className="text-blue-600 hover:underline">
        ← Back to landing
      </Link>
    </div>
  )
}
