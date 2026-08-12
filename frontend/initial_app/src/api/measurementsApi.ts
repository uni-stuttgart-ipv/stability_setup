import apiClient from './client'
import { BUCKET, MEASUREMENT } from './influxApi'
import type { TimeSeriesPoint } from '../types'

interface HistoryMeasurement {
  timestamp: string
  temperature?: number
  measured_intensity?: number
  sensor?: string
}

interface HistoryPayload {
  measurements: HistoryMeasurement[]
}

async function fetchHistory(path: string, sensor: string, from: Date, to: Date): Promise<HistoryMeasurement[]> {
  const response = await apiClient.get<HistoryPayload>(path, {
    params: {
      measurement: MEASUREMENT,
      bucket: BUCKET,
      sensor,
      start: from.toISOString(),
      end: to.toISOString(),
    },
  })
  return response.data.measurements
}

export async function fetchTemperatureHistory(sensor: string, from: Date, to: Date): Promise<TimeSeriesPoint[]> {
  const measurements = await fetchHistory('api/v1/influx/measurement/history/temperature', sensor, from, to)
  return measurements.map((point) => ({ timestamp: point.timestamp, value: point.temperature ?? null }))
}

export async function fetchIntensityHistory(sensor: string, from: Date, to: Date): Promise<TimeSeriesPoint[]> {
  const measurements = await fetchHistory('api/v1/influx/measurement/history/intensity', sensor, from, to)
  return measurements.map((point) => ({ timestamp: point.timestamp, value: point.measured_intensity ?? null }))
}
