import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchSetupById } from '../api/mockApi'
import BackLink from '../components/layout/BackLink'
import Page from '../components/layout/Page'
import type { DeviceStatus, Setup } from '../types'
import { statusDotClass } from '../utils/statusColors'

function StatusBadge({ label, status }: { label: string; status: DeviceStatus }) {
  return (
    <div className="flex items-center gap-2 text-[0.9rem]">
      <span className={`h-[10px] w-[10px] shrink-0 rounded-full ${statusDotClass(status)}`} />
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
      <Page>
        <p>Loading setup…</p>
      </Page>
    )
  }

  if (!setup) {
    return (
      <Page>
        <p>Setup not found.</p>
        <BackLink to="/">Back to all setups</BackLink>
      </Page>
    )
  }

  return (
    <Page>
      <BackLink to="/">← All setups</BackLink>
      <h1>{setup.name}</h1>
      <p className="-mt-2 text-text-muted">ID: {setup.id}</p>

      <div className="my-4 flex flex-wrap gap-6">
        <StatusBadge label="Solar Simulator" status={setup.solarSimulatorStatus} />
        <StatusBadge label="Measurement Board" status={setup.measurementBoardStatus} />
      </div>

      <div className="mb-6 rounded-[10px] border border-border bg-surface px-5 py-4">
        <h3 className="mt-0">General Info</h3>
        <p>{setup.description}</p>
        <p>Location: {setup.location}</p>
        <p>Current user: {setup.currentUser ?? 'None'}</p>
      </div>

      <div className="flex gap-4">
        <button
          type="button"
          onClick={() => navigate(`/setups/${setup.id}/solar-simulator`)}
          className="cursor-pointer rounded-lg border border-border bg-accent px-[1.2rem] py-[0.6rem] text-[0.95rem] text-white hover:opacity-90"
        >
          Solar Simulator
        </button>
        <button
          type="button"
          onClick={() => navigate(`/setups/${setup.id}/measurement`)}
          className="cursor-pointer rounded-lg border border-border bg-accent px-[1.2rem] py-[0.6rem] text-[0.95rem] text-white hover:opacity-90"
        >
          Measurement
        </button>
      </div>
    </Page>
  )
}

export default SetupPage
