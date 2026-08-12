export type DeviceStatus = 'online' | 'offline' | 'error'

export interface Setup {
  id: string
  name: string
  location: string
  description: string
  currentUser: string | null
  solarSimulatorStatus: DeviceStatus
  measurementBoardStatus: DeviceStatus
}

export interface SolarSimulatorReading {
  timestamp: string
  temperature: number
  setLightIntensity: number
  measuredLightIntensity: number
  voltage: number
  current: number
}

export interface TimeSeriesPoint {
  timestamp: string
  /** null means the sensor didn't report a reading at this timestamp. */
  value: number | null
}

export type TimeRangePresetKey =
  | '1m'
  | '5m'
  | '15m'
  | '1h'
  | '3h'
  | '6h'
  | '12h'
  | '24h'
  | 'custom'

export interface TimeRange {
  preset: TimeRangePresetKey
  from: Date
  to: Date
  label: string
}
