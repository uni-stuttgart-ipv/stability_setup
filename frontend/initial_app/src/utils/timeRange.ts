import type { TimeRange, TimeRangePresetKey } from '../types'

export interface TimeRangePresetOption {
  key: Exclude<TimeRangePresetKey, 'custom'>
  label: string
  durationMs: number
}

const MINUTE = 60_000
const HOUR = 60 * MINUTE

export const TIME_RANGE_PRESETS: TimeRangePresetOption[] = [
  { key: '1m', label: 'Past 1m', durationMs: 1 * MINUTE },
  { key: '5m', label: 'Past 5m', durationMs: 5 * MINUTE },
  { key: '15m', label: 'Past 15m', durationMs: 15 * MINUTE },
  { key: '1h', label: 'Past 1h', durationMs: 1 * HOUR },
  { key: '3h', label: 'Past 3h', durationMs: 3 * HOUR },
  { key: '6h', label: 'Past 6h', durationMs: 6 * HOUR },
  { key: '12h', label: 'Past 12h', durationMs: 12 * HOUR },
  { key: '24h', label: 'Past 24h', durationMs: 24 * HOUR },
]

export function resolvePresetRange(key: Exclude<TimeRangePresetKey, 'custom'>, now: Date = new Date()): TimeRange {
  const preset = TIME_RANGE_PRESETS.find((option) => option.key === key)!
  return {
    preset: key,
    from: new Date(now.getTime() - preset.durationMs),
    to: now,
    label: preset.label,
  }
}

export function buildCustomRange(from: Date, to: Date): TimeRange {
  return {
    preset: 'custom',
    from,
    to,
    label: 'Custom range',
  }
}

export const DEFAULT_TIME_RANGE_PRESET: Exclude<TimeRangePresetKey, 'custom'> = '15m'

export function toLocalInputValue(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}
