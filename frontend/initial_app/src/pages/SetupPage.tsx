import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchSetupById } from '../api/mockApi'
import type { Setup } from '../types'
import './SetupPage.css'

function StatusBadge({ label, status }: { label: string; status: string }) {
  return (
    <div className="status-badge">
      <span className={`status-dot status-dot--${status}`} />
      <span>
        {label}: <strong>{status}</strong>
      </span>
    </div>
  )
}

function SetupPage() {
  const { setupId } = useParams<{ setupId: string }>()
  const navigate = useNavigate()
  const [setup, setSetup] = useState<Setup | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!setupId) return
    let cancelled = false
    setLoading(true)
    fetchSetupById(setupId).then((data) => {
      if (!cancelled) {
        setSetup(data ?? null)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [setupId])

  if (loading) {
    return (
      <div className="page">
        <p>Loading setup…</p>
      </div>
    )
  }

  if (!setup) {
    return (
      <div className="page">
        <p>Setup not found.</p>
        <Link to="/">Back to all setups</Link>
      </div>
    )
  }

  return (
    <div className="page">
      <Link to="/" className="back-link">
        ← All setups
      </Link>
      <h1>{setup.name}</h1>
      <p className="setup-id">ID: {setup.id}</p>

      <div className="status-row">
        <StatusBadge label="Solar Simulator" status={setup.solarSimulatorStatus} />
        <StatusBadge label="Measurement Board" status={setup.measurementBoardStatus} />
      </div>

      <div className="info-block">
        <h3>General Info</h3>
        <p>{setup.description}</p>
        <p>Location: {setup.location}</p>
        <p>Current user: {setup.currentUser ?? 'None'}</p>
      </div>

      <div className="nav-buttons">
        <button type="button" onClick={() => navigate(`/setups/${setup.id}/solar-simulator`)}>
          Solar Simulator
        </button>
        <button type="button" onClick={() => navigate(`/setups/${setup.id}/measurement`)}>
          Measurement
        </button>
      </div>
    </div>
  )
}

export default SetupPage
