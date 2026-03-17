import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LandingPage from './pages/LandingPage'
import SimulatePage from './pages/SimulatePage'
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
          <Route path="/login" element={<LandingPage />} />
          <Route path="/register" element={<LandingPage />} />
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
          <Route path="/demo" element={<DemoPage />} />
          <Route path="/demo/:id" element={<DemoPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
