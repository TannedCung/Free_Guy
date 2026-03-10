import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import SimulatePage from './pages/SimulatePage'
import DemoPage from './pages/DemoPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/simulate" element={<SimulatePage />} />
        <Route path="/simulate/:id" element={<SimulatePage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/demo/:id" element={<DemoPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
