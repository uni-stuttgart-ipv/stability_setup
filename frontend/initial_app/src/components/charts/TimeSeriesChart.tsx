import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TimeSeriesPoint } from '../../types'

interface TimeSeriesChartProps {
  title: string
  unit: string
  data: TimeSeriesPoint[]
  isLoading: boolean
  isFetching: boolean
  isError: boolean
  onRetry: () => void
  color?: string
}

function formatAxisTime(timestamp: string, spanMs: number): string {
  const date = new Date(timestamp)
  if (spanMs > 20 * 60 * 60_000) {
    return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: spanMs <= 5 * 60_000 ? '2-digit' : undefined })
}

function formatFullTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

interface ChartTooltipEntry {
  value?: unknown
  color?: string
  payload?: TimeSeriesPoint
}

interface ChartTooltipProps {
  active?: boolean
  payload?: readonly ChartTooltipEntry[]
  unit: string
}

function ChartTooltip({ active, payload, unit }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null
  const point = payload[0]
  const timestamp = point.payload?.timestamp
  return (
    <div className="rounded-lg border border-border bg-surface px-[0.65rem] py-2 text-[0.8rem] shadow-[0_6px_18px_rgba(0,0,0,0.14)]">
      {timestamp && (
        <div className="mb-1 text-text-muted [font-variant-numeric:tabular-nums]">{formatFullTime(timestamp)}</div>
      )}
      <div className="flex items-center gap-[0.4rem] text-text">
        <span className="inline-block h-[2px] w-[10px] rounded-[1px]" style={{ backgroundColor: point.color }} />
        {point.value == null ? (
          <span className="text-text-muted italic">No reading</span>
        ) : (
          <>
            <strong>{typeof point.value === 'number' ? point.value.toFixed(2) : String(point.value)}</strong>
            <span className="text-text-muted">{unit}</span>
          </>
        )}
      </div>
    </div>
  )
}

function TimeSeriesChart({
  title,
  unit,
  data,
  isLoading,
  isFetching,
  isError,
  onRetry,
  color = 'var(--accent)',
}: TimeSeriesChartProps) {
  const [showTable, setShowTable] = useState(false)

  const spanMs = useMemo(() => {
    if (data.length < 2) return 0
    return new Date(data[data.length - 1].timestamp).getTime() - new Date(data[0].timestamp).getTime()
  }, [data])

  const hasData = data.some((point) => point.value != null)

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h4 className="m-0 text-[0.9rem] text-text">
          {title}
          <span className="font-normal text-text-muted"> ({unit})</span>
        </h4>
        {hasData && (
          <button
            type="button"
            className="cursor-pointer rounded-md border border-border bg-surface px-[0.6rem] py-1 text-xs whitespace-nowrap text-text-muted hover:bg-surface-muted hover:text-text"
            onClick={() => setShowTable((show) => !show)}
            aria-pressed={showTable}
          >
            {showTable ? 'View chart' : 'View table'}
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex h-[220px] items-center justify-center rounded-[10px] border border-dashed border-border bg-surface-muted text-[0.85rem] text-text-muted">
          Loading…
        </div>
      ) : isError ? (
        <div className="flex h-[220px] flex-col items-center justify-center gap-2 rounded-[10px] border border-dashed border-border bg-surface-muted text-[0.85rem]">
          <span className="text-error">Failed to load data</span>
          <button
            type="button"
            onClick={onRetry}
            className="cursor-pointer rounded-md border border-border bg-accent px-3 py-1 text-[0.8rem] text-white hover:opacity-90"
          >
            Retry
          </button>
        </div>
      ) : !hasData ? (
        <div className="flex h-[220px] items-center justify-center rounded-[10px] border border-dashed border-border bg-surface-muted text-[0.85rem] text-text-muted">
          No data for this range
        </div>
      ) : showTable ? (
        <div className="h-[220px] overflow-y-auto rounded-[10px] border border-border bg-surface">
          <table className="w-full border-collapse text-[0.8rem]">
            <thead>
              <tr>
                <th className="sticky top-0 border-b border-border bg-surface-muted px-[0.65rem] py-[0.45rem] text-left font-semibold text-text-muted">
                  Time
                </th>
                <th className="sticky top-0 border-b border-border bg-surface-muted px-[0.65rem] py-[0.45rem] text-left font-semibold text-text-muted">
                  {unit ? `Value (${unit})` : 'Value'}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((point) => (
                <tr key={point.timestamp}>
                  <td className="border-b border-border px-[0.65rem] py-[0.4rem] text-text">
                    {formatFullTime(point.timestamp)}
                  </td>
                  <td className="border-b border-border px-[0.65rem] py-[0.4rem] text-right text-text [font-variant-numeric:tabular-nums]">
                    {point.value == null ? (
                      <span className="text-text-muted italic">No reading</span>
                    ) : (
                      point.value.toFixed(2)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          className="rounded-[10px] border border-border bg-surface px-1 pt-2 pb-1 transition-opacity duration-150 ease-in-out"
          style={{ opacity: isFetching ? 0.55 : 1 }}
        >
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="0" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value: string) => formatAxisTime(value, spanMs)}
                stroke="var(--border)"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickLine={false}
                minTickGap={32}
              />
              <YAxis
                stroke="var(--border)"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={48}
                domain={['auto', 'auto']}
              />
              <Tooltip
                content={(props) => <ChartTooltip {...props} unit={unit} />}
                cursor={{ stroke: 'var(--text-muted)', strokeWidth: 1 }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: 'var(--surface)' }}
                isAnimationActive={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default TimeSeriesChart
