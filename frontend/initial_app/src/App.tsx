import { Navigate, Route, Routes } from 'react-router-dom'
import AllSetupsHomePage from './pages/AllSetupsHomePage'
import MeasurementPage from './pages/MeasurementPage'
import SetupPage from './pages/SetupPage'
import SolarSimulatorPage from './pages/SolarSimulatorPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<AllSetupsHomePage />} />
      <Route path="/setups/:setupId" element={<SetupPage />} />
      <Route path="/setups/:setupId/solar-simulator" element={<SolarSimulatorPage />} />
      <Route path="/setups/:setupId/measurement" element={<MeasurementPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
