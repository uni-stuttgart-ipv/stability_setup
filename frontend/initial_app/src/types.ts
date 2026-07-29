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
