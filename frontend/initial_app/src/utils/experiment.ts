import type { ExperimentAction, ExperimentBlock, ExperimentDraft, ExperimentPayload } from '../types'

function createId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `id-${Math.random().toString(36).slice(2)}`
}

export function createAction(
  overrides: Partial<Pick<ExperimentAction, 'setIntensityPercent' | 'durationHours'>> = {},
): ExperimentAction {
  return {
    id: createId(),
    setIntensityPercent: overrides.setIntensityPercent ?? 50,
    durationHours: overrides.durationHours ?? 12,
  }
}

export function createBlock(): ExperimentBlock {
  return {
    id: createId(),
    repeatMode: 'once',
    repeatCount: 1,
    actions: [createAction()],
  }
}

export function duplicateBlock(block: ExperimentBlock): ExperimentBlock {
  return {
    ...block,
    id: createId(),
    actions: block.actions.map((action) => ({ ...action, id: createId() })),
  }
}

export function blockCycleDurationHours(block: ExperimentBlock): number {
  return block.actions.reduce((sum, action) => sum + (action.durationHours || 0), 0)
}

export function blockEffectiveDurationHours(block: ExperimentBlock): number {
  const cycles = block.repeatMode === 'repeat' ? Math.max(1, block.repeatCount) : 1
  return blockCycleDurationHours(block) * cycles
}

export function buildExperimentPayload(draft: ExperimentDraft): ExperimentPayload {
  return {
    name: draft.name.trim(),
    device_id: draft.deviceId,
    start_time: draft.startTime,
    end_time: draft.endTime,
    blocks: draft.blocks.map((block) => ({
      repeat: block.repeatMode === 'repeat' ? Math.max(1, block.repeatCount) : 1,
      actions: block.actions.map((action) => ({
        set_intensity_percent: action.setIntensityPercent,
        duration_hours: action.durationHours,
      })),
    })),
  }
}
