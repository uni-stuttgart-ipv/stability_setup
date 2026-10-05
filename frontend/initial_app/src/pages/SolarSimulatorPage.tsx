import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchSetupById } from '../api/mockApi'
import { fetchLatestInfluxValues, mapValuesToReading, type LiveReading } from '../api/influxApi'
import { fetchIntensityHistory, fetchTemperatureHistory } from '../api/measurementsApi'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import TimeRangeSelect from '../components/controls/TimeRangeSelect'
import IntensitySlider from '../components/controls/IntensitySlider'
import ParametersTable from '../components/tables/ParametersTable'
import BackLink from '../components/layout/BackLink'
import Page from '../components/layout/Page'
import ManageExperimentModal from '../components/experiment/ManageExperimentModal'
import { useSolarSimulatorStream } from '../hooks/useSolarSimulatorStream'
import type { Setup, TimeRange } from '../types'
import { deviceIdForSetup } from '../utils/device'
import { DEFAULT_TIME_RANGE_PRESET, resolvePresetRange } from '../utils/timeRange'
import { setIntensitySolar, type IntensityRequest } from "../api/solarSimulatorApi";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

type ApplyStatus = 'idle' | 'applying' | 'applied' | 'failed'

const APPLY_STATUS_LABEL: Record<ApplyStatus, string> = {
  idle: '',
  applying: 'Applying…',
  applied: 'Applied',
  failed: 'Failed to apply',
}

const APPLY_STATUS_CLASS: Record<ApplyStatus, string> = {
  idle: '',
  applying: 'text-text-muted',
  applied: 'text-online',
  failed: 'text-error',
}

function SolarSimulatorPage() {
  const { setupId } = useParams<{ setupId: string }>()
  const [setup, setSetup] = useState<Setup | null>(null)
  const [liveReading, setLiveReading] = useState<LiveReading | null>(null)
  const [pendingIntensity, setPendingIntensity] = useState(0)
  const [appliedIntensity, setAppliedIntensity] = useState(0)
  const [applyStatus, setApplyStatus] = useState<ApplyStatus>('idle')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [temperatureRange, setTemperatureRange] = useState<TimeRange>(() =>
    resolvePresetRange(DEFAULT_TIME_RANGE_PRESET),
  )
  const [intensityRange, setIntensityRange] = useState<TimeRange>(() =>
    resolvePresetRange(DEFAULT_TIME_RANGE_PRESET),
  )
  const [isExperimentModalOpen, setIsExperimentModalOpen] = useState(false)

  const deviceId = useMemo(() => (setupId ? deviceIdForSetup(setupId) : undefined), [setupId])

  const temperatureHistoryQuery = useQuery({
    queryKey: ['temperatureHistory', deviceId, temperatureRange.from.getTime(), temperatureRange.to.getTime()],
    queryFn: () => fetchTemperatureHistory(deviceId!, temperatureRange.from, temperatureRange.to),
    enabled: Boolean(deviceId),
    placeholderData: keepPreviousData,
  })

  const intensityHistoryQuery = useQuery({
    queryKey: ['intensityHistory', deviceId, intensityRange.from.getTime(), intensityRange.to.getTime()],
    queryFn: () => fetchIntensityHistory(deviceId!, intensityRange.from, intensityRange.to),
    enabled: Boolean(deviceId),
    placeholderData: keepPreviousData,
  })

  useEffect(() => {
    if (!setupId || !deviceId) return
    let cancelled = false
    Promise.all([fetchSetupById(setupId), fetchLatestInfluxValues(deviceId)])
      .then(([setupData, values]) => {
        if (cancelled) return
        setSetup(setupData ?? null)
        setLiveReading(mapValuesToReading(values))
        const initialIntensity = values.set_light_intensity ?? 0
        setPendingIntensity(initialIntensity)
        setAppliedIntensity(initialIntensity)
        setLoading(false)
      })
      .catch((error) => {
        if (cancelled) return
        console.error('Failed to load solar simulator data:', error)
        setLoadError(true)
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
      <Page>
        <p>Loading solar simulator…</p>
      </Page>
    )
  }

  if (loadError) {
    return (
      <Page>
        {setupId && <BackLink to={`/setups/${setupId}`}>← Setup</BackLink>}
        <p className="text-error">
          Couldn't reach the backend. Check that the API server is running and reachable from this device, then
          reload the page.
        </p>
      </Page>
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
    <Page>
      {setupId && <BackLink to={`/setups/${setupId}`}>← {setup?.name ?? 'Setup'}</BackLink>}
      <h1>Solar Simulator</h1>

      <section className="my-6">
        <IntensitySlider value={pendingIntensity} onChange={setPendingIntensity} />
        <div className="mt-3 flex flex-wrap items-center gap-[0.9rem]">
          <button
            type="button"
            onClick={handleApplyIntensity}
            disabled={mutation.isPending}
            className="cursor-pointer rounded-lg border border-border bg-accent px-[1.1rem] py-2 text-[0.9rem] text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            Set Intensity
          </button>
          <button
            type="button"
            onClick={() => setIsExperimentModalOpen(true)}
            className="cursor-pointer rounded-lg border border-border bg-surface px-[1.1rem] py-2 text-[0.9rem] text-text hover:bg-surface-muted"
          >
            Manage Experiment
          </button>
          <span className={`min-h-[1.2em] text-[0.85rem] ${APPLY_STATUS_CLASS[applyStatus]}`}>
            {APPLY_STATUS_LABEL[applyStatus]}
          </span>
        </div>
      </section>

      <section className="my-6">
        <h3>Latest Values</h3>
        <ParametersTable reading={tableReading} />
      </section>

      <section className="my-6">
        <div className="flex flex-wrap gap-6">
          <div className="min-w-[280px] flex-[1_1_320px]">
            <div className="mb-3 flex">
              <TimeRangeSelect value={temperatureRange} onChange={setTemperatureRange} />
            </div>
            <TimeSeriesChart
              title="Temperature vs Time"
              unit="°C"
              data={temperatureHistoryQuery.data ?? []}
              isLoading={temperatureHistoryQuery.isPending}
              isFetching={temperatureHistoryQuery.isFetching && !temperatureHistoryQuery.isPending}
              isError={temperatureHistoryQuery.isError}
              onRetry={() => temperatureHistoryQuery.refetch()}
            />
          </div>
          <div className="min-w-[280px] flex-[1_1_320px]">
            <div className="mb-3 flex">
              <TimeRangeSelect value={intensityRange} onChange={setIntensityRange} />
            </div>
            <TimeSeriesChart
              title="Light Intensity vs Time"
              unit="W/m²"
              data={intensityHistoryQuery.data ?? []}
              isLoading={intensityHistoryQuery.isPending}
              isFetching={intensityHistoryQuery.isFetching && !intensityHistoryQuery.isPending}
              isError={intensityHistoryQuery.isError}
              onRetry={() => intensityHistoryQuery.refetch()}
            />
          </div>
        </div>
      </section>

      {isExperimentModalOpen && deviceId && (
        <ManageExperimentModal
          deviceId={deviceId}
          deviceLabel={`${setup?.name ?? 'Setup'} - ${deviceId}`}
          onClose={() => setIsExperimentModalOpen(false)}
        />
      )}
    </Page>
  )
}

export default SolarSimulatorPage
