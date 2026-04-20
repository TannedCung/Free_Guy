import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import CharactersPage from './pages/CharactersPage'
import CreateCharacterPage from './pages/CreateCharacterPage'
import EditCharacterPage from './pages/EditCharacterPage'
import CreateSimulationPage from './pages/CreateSimulationPage'
import SimulatePage from './pages/SimulatePage'
import SimulationSettingsPage from './pages/SimulationSettingsPage'
import InvitesPage from './pages/InvitesPage'
import ExplorePage from './pages/ExplorePage'
import ReplayPage from './pages/ReplayPage'
import DemoPage from './pages/DemoPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/characters"
            element={
              <ProtectedRoute>
                <CharactersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/characters/new"
            element={
              <ProtectedRoute>
                <CreateCharacterPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/characters/:id/edit"
            element={
              <ProtectedRoute>
                <EditCharacterPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulations/new"
            element={
              <ProtectedRoute>
                <CreateSimulationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulate"
            element={
              <ProtectedRoute>
                <SimulatePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulate/:id"
            element={
              <ProtectedRoute>
                <SimulatePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulate/:id/settings"
            element={
              <ProtectedRoute>
                <SimulationSettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invites"
            element={
              <ProtectedRoute>
                <InvitesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/explore"
            element={
              <ProtectedRoute>
                <ExplorePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/simulate/:id/replay"
            element={
              <ProtectedRoute>
                <ReplayPage />
              </ProtectedRoute>
            }
          />
          <Route path="/demo" element={<DemoPage />} />
          <Route path="/demo/:id" element={<DemoPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
