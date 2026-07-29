import apiClient, { API_BASE_URL } from './client'

const MEASUREMENT = 'simulator_data'
const BUCKET = 'stability_test'

export interface InfluxValues {
  temperature?: number
  light?: number
  measured_light_intensity?: number
  voltage?: number
  current?: number
  set_light_intensity?: number
}

interface InfluxPayload {
  values: InfluxValues
}

export interface LiveReading {
  temperature?: number
  measuredLightIntensity?: number
  voltage?: number
  current?: number
}

export function mapValuesToReading(values: InfluxValues): LiveReading {
  return {
    temperature: values.temperature,
    measuredLightIntensity: values.measured_light_intensity ?? values.light,
    voltage: values.voltage,
    current: values.current,
  }
}

export async function fetchLatestInfluxValues(sensor: string): Promise<InfluxValues> {
  const response = await apiClient.get<InfluxPayload>(`api/v1/influx/latest/${MEASUREMENT}`, {
    params: { bucket: BUCKET, sensor },
  })
  return response.data.values
}

export function getInfluxStreamUrl(sensor: string): string {
  return `${API_BASE_URL}/api/v1/influx/stream/${MEASUREMENT}?bucket=${encodeURIComponent(BUCKET)}&sensor=${encodeURIComponent(sensor)}`
}
