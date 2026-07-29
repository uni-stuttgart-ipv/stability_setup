import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchSetupById } from '../api/mockApi'
import { fetchLatestInfluxValues, mapValuesToReading, type LiveReading } from '../api/influxApi'
import ChartPlaceholder from '../components/charts/ChartPlaceholder'
import IntensitySlider from '../components/controls/IntensitySlider'
import ParametersTable from '../components/tables/ParametersTable'
import { useSolarSimulatorStream } from '../hooks/useSolarSimulatorStream'
import type { Setup } from '../types'
import './SolarSimulatorPage.css'
import { setIntensitySolar, type IntensityRequest } from "../api/solarSimulatorApi";
import { useMutation } from "@tanstack/react-query";

type ApplyStatus = 'idle' | 'applying' | 'applied' | 'failed'

const APPLY_STATUS_LABEL: Record<ApplyStatus, string> = {
  idle: '',
  applying: 'Applying…',
  applied: 'Applied',
  failed: 'Failed to apply',
}

function SolarSimulatorPage() {
  const { setupId } = useParams<{ setupId: string }>()
  const [setup, setSetup] = useState<Setup | null>(null)
  const [liveReading, setLiveReading] = useState<LiveReading | null>(null)
  const [pendingIntensity, setPendingIntensity] = useState(0)
  const [appliedIntensity, setAppliedIntensity] = useState(0)
  const [applyStatus, setApplyStatus] = useState<ApplyStatus>('idle')
  const [loading, setLoading] = useState(true)

  const deviceId = useMemo(() => {
    const setupNumber = setupId?.match(/\d+/)?.[0]
    return setupNumber ? `solar_simulator_${setupNumber}` : undefined
  }, [setupId])

  useEffect(() => {
    if (!setupId || !deviceId) return
    let cancelled = false
    Promise.all([fetchSetupById(setupId), fetchLatestInfluxValues(deviceId)]).then(([setupData, values]) => {
      if (cancelled) return
      setSetup(setupData ?? null)
      setLiveReading(mapValuesToReading(values))
      const initialIntensity = values.set_light_intensity ?? 0
      setPendingIntensity(initialIntensity)
      setAppliedIntensity(initialIntensity)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [setupId, deviceId])

  useSolarSimulatorStream(deviceId, setLiveReading)

  const mutation = useMutation({
    mutationFn: (intensityRequest: IntensityRequest) => setIntensitySolar(deviceId!, intensityRequest),
  });

  function handleApplyIntensity() {
    if (!deviceId) return
    const target = pendingIntensity
    setApplyStatus('applying')
    mutation.mutate(
      { ch0: target, ch1: target },
      {
        onSuccess: () => {
          setAppliedIntensity(target)
          setApplyStatus('applied')
        },
        onError: () => {
          setPendingIntensity(appliedIntensity)
          setApplyStatus('failed')
        },
      },
    )
  }

  if (loading) {
    return (
      <div className="page">
        <p>Loading solar simulator…</p>
      </div>
    )
  }

  const tableReading = {
    temperature: liveReading?.temperature,
    setLightIntensity: appliedIntensity,
    measuredLightIntensity: liveReading?.measuredLightIntensity,
    voltage: liveReading?.voltage,
    current: liveReading?.current,
  }

  return (
    <div className="page">
      {setupId && (
        <Link to={`/setups/${setupId}`} className="back-link">
          ← {setup?.name ?? 'Setup'}
        </Link>
      )}
      <h1>Solar Simulator</h1>

      <section className="section">
        <IntensitySlider value={pendingIntensity} onChange={setPendingIntensity} />
        <div className="intensity-apply-row">
          <button type="button" onClick={handleApplyIntensity} disabled={mutation.isPending}>
            Set Intensity
          </button>
          <span className={`apply-status apply-status--${applyStatus}`}>
            {APPLY_STATUS_LABEL[applyStatus]}
          </span>
        </div>
      </section>

      <section className="section">
        <h3>Latest Values</h3>
        <ParametersTable reading={tableReading} />
      </section>

      <section className="section chart-row">
        <ChartPlaceholder title="Temperature vs Time" />
        <ChartPlaceholder title="Light Intensity vs Time" />
      </section>
    </div>
  )
}

export default SolarSimulatorPage
