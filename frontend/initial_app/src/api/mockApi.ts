import type { DeviceStatus, Setup } from '../types'

const SETUP_COUNT = 10
const NETWORK_DELAY_MS = 250

const USERS = ['A. Sharma', 'R. Mehta', 'J. Fernandes', 'P. Iyer', null, null]
const STATUSES: DeviceStatus[] = ['online', 'online', 'online', 'offline', 'error']

function pick<T>(items: T[], seed: number): T {
  return items[seed % items.length]
}

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), NETWORK_DELAY_MS))
}

function buildSetups(): Setup[] {
  return Array.from({ length: SETUP_COUNT }, (_, i) => {
    const index = i + 1
    return {
      id: `setup-${index}`,
      name: `Setup ${index}`,
      location: `Lab ${Math.ceil(index / 4)} - Bench ${((index - 1) % 4) + 1}`,
      description: 'IV characterization setup with solar simulator and measurement board.',
      currentUser: pick(USERS, index),
      solarSimulatorStatus: pick(STATUSES, index),
      measurementBoardStatus: pick(STATUSES, index + 2),
    }
  })
}

const setups: Setup[] = buildSetups()

export function fetchSetups(): Promise<Setup[]> {
  return delay(setups)
}

export function fetchSetupById(setupId: string): Promise<Setup | undefined> {
  return delay(setups.find((setup) => setup.id === setupId))
}
