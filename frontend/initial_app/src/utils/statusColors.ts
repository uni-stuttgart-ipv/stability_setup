import type { DeviceStatus } from '../types'

const STATUS_DOT_CLASSES: Record<DeviceStatus, string> = {
  online: 'bg-online',
  offline: 'bg-offline',
  error: 'bg-error',
}

export function statusDotClass(status: DeviceStatus): string {
  return STATUS_DOT_CLASSES[status]
}
