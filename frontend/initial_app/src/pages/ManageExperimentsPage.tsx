import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { activateExperiment, fetchExperiments, stopExperiment } from '../api/experimentApi'
import BackLink from '../components/layout/BackLink'
import Page from '../components/layout/Page'
import type { ExperimentStatus } from '../types'
import { deviceIdForSetup } from '../utils/device'

const STATUS_CLASS: Record<ExperimentStatus, string> = {
  ACTIVE: 'border-online text-online',
  PAUSED: 'border-offline text-offline',
  INACTIVE: 'border-border text-text-muted',
  STOPPING: 'border-error text-error',
  STOPPED: 'border-border text-text-muted',
  COMPLETING: 'border-accent text-accent',
  COMPLETED: 'border-online text-online',
}

const HEADER_CLASS =
  'whitespace-nowrap border border-border bg-surface-muted px-[0.9rem] py-[0.6rem] text-left text-[0.72rem] font-semibold tracking-[0.03em] text-text-muted'
const CELL_CLASS = 'whitespace-nowrap border border-border px-[0.9rem] py-[0.6rem] text-left text-[0.85rem]'

// The backend stores created_at as naive UTC, so tag it as UTC before parsing
// or the browser would read it as local time.
function parseBackendDate(value: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`)
}

function formatDate(value: string): string {
  const date = parseBackendDate(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function ManageExperimentsPage() {
  const { setupId } = useParams<{ setupId: string }>()
  const deviceId = useMemo(() => (setupId ? deviceIdForSetup(setupId) : undefined), [setupId])
  const queryClient = useQueryClient()

  const experimentsQuery = useQuery({
    queryKey: ['experiments'],
    queryFn: fetchExperiments,
  })

  const activateMutation = useMutation({
    mutationFn: activateExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
    },
  })

  const stopMutation = useMutation({
    mutationFn: stopExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
    },
  })

  const experiments = useMemo(
    () => (experimentsQuery.data ?? []).filter((experiment) => experiment.experiment_json.device_id === deviceId),
    [experimentsQuery.data, deviceId],
  )

  return (
    <Page>
      {setupId && <BackLink to={`/setups/${setupId}/solar-simulator`}>← Solar Simulator</BackLink>}
      <h1>Experiments</h1>
      {deviceId && <p className="text-[0.85rem] text-text-muted">Device: {deviceId}</p>}

      <section className="my-6">
        {experimentsQuery.isPending ? (
          <p>Loading experiments…</p>
        ) : experimentsQuery.isError ? (
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-error">Couldn't load experiments. Check that the API server is running.</p>
            <button
              type="button"
              onClick={() => experimentsQuery.refetch()}
              className="cursor-pointer rounded-lg border border-border bg-surface px-[1.1rem] py-2 text-[0.9rem] text-text hover:bg-surface-muted"
            >
              Retry
            </button>
          </div>
        ) : experiments.length === 0 ? (
          <p className="text-text-muted">No experiments for this setup yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {['NAME', 'STATUS', 'START', 'END', 'BLOCKS', 'CREATED', 'ACTIONS'].map((label) => (
                    <th key={label} className={HEADER_CLASS}>
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {experiments.map((experiment) => {
                  const { name, start_time, end_time, blocks } = experiment.experiment_json
                  return (
                    <tr key={experiment.experiment_id}>
                      <td className={CELL_CLASS}>{name}</td>
                      <td className={CELL_CLASS}>
                        <span
                          className={`rounded-full border px-2 py-[0.1rem] text-[0.72rem] font-semibold ${STATUS_CLASS[experiment.status]}`}
                        >
                          {experiment.status}
                        </span>
                      </td>
                      <td className={CELL_CLASS}>{formatDate(start_time)}</td>
                      <td className={CELL_CLASS}>{formatDate(end_time)}</td>
                      <td className={CELL_CLASS}>{blocks.length}</td>
                      <td className={CELL_CLASS}>{formatDate(experiment.created_at)}</td>
                      <td className={CELL_CLASS}>
                        {(() => {
                          const isActivatingThis =
                            activateMutation.isPending && activateMutation.variables === experiment.experiment_id
                          const isStoppingThis =
                            stopMutation.isPending && stopMutation.variables === experiment.experiment_id
                          return (
                            <div className="flex flex-col gap-1">
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={() => activateMutation.mutate(experiment.experiment_id)}
                                  disabled={experiment.status !== 'INACTIVE' || isActivatingThis}
                                  className="cursor-pointer rounded-lg border border-border bg-accent px-[0.9rem] py-[0.35rem] text-[0.8rem] text-white disabled:cursor-not-allowed disabled:opacity-40"
                                >
                                  {isActivatingThis ? 'Starting…' : 'Run'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => stopMutation.mutate(experiment.experiment_id)}
                                  disabled={experiment.status !== 'ACTIVE' || isStoppingThis}
                                  className="cursor-pointer rounded-lg border border-error bg-error px-[0.9rem] py-[0.35rem] text-[0.8rem] text-white disabled:cursor-not-allowed disabled:opacity-40"
                                >
                                  {isStoppingThis ? 'Stopping…' : 'Stop'}
                                </button>
                              </div>
                              {activateMutation.isError && activateMutation.variables === experiment.experiment_id && (
                                <span className="text-[0.75rem] text-error">Failed to start — try again.</span>
                              )}
                              {stopMutation.isError && stopMutation.variables === experiment.experiment_id && (
                                <span className="text-[0.75rem] text-error">Failed to stop — try again.</span>
                              )}
                            </div>
                          )
                        })()}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </Page>
  )
}

export default ManageExperimentsPage
