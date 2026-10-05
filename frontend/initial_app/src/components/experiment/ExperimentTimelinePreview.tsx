import type { ExperimentBlock } from '../../types'
import { blockEffectiveDurationHours } from '../../utils/experiment'

interface ExperimentTimelinePreviewProps {
  blocks: ExperimentBlock[]
}

function ExperimentTimelinePreview({ blocks }: ExperimentTimelinePreviewProps) {
  const hasActions = blocks.some((block) => block.actions.length > 0)

  if (blocks.length === 0 || !hasActions) {
    return (
      <div className="flex h-20 items-center justify-center rounded-[10px] border border-dashed border-border bg-surface-muted text-[0.85rem] text-text-muted">
        Add a block to preview the timeline
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-[10px] border border-border bg-surface p-3">
      <div className="flex min-w-[640px] items-stretch">
        {blocks.map((block, blockIndex) => {
          const weight = blockEffectiveDurationHours(block) || 1
          return (
            <div
              key={block.id}
              className="flex flex-col border-r border-border pr-3 last:border-r-0 last:pr-0"
              style={{ flexGrow: weight, flexBasis: 0, minWidth: 90 }}
            >
              <div className="mb-1 truncate text-[0.75rem] font-semibold text-text">
                Block {blockIndex + 1}
                {block.repeatMode === 'repeat' && (
                  <span className="text-text-muted"> ×{Math.max(1, block.repeatCount)}</span>
                )}
              </div>
              <div className="flex h-2 overflow-hidden rounded-full">
                {block.actions.length === 0 ? (
                  <div className="w-full bg-border" />
                ) : (
                  block.actions.map((action, actionIndex) => (
                    <div
                      key={action.id}
                      title={`${action.setIntensityPercent}% for ${action.durationHours}h`}
                      style={{
                        flexGrow: action.durationHours || 1,
                        flexBasis: 0,
                        backgroundColor: 'var(--accent)',
                        opacity: 0.35 + (0.5 * (actionIndex + 1)) / block.actions.length,
                      }}
                    />
                  ))
                )}
              </div>
              <div className="mt-1 truncate text-[0.7rem] text-text-muted">
                {block.actions.map((action) => `${action.setIntensityPercent}% ${action.durationHours}h`).join(' → ') ||
                  'No actions'}
              </div>
            </div>
          )
        })}
        <div className="flex items-center pl-2 text-text-muted" aria-hidden="true">
          →
        </div>
      </div>
    </div>
  )
}

export default ExperimentTimelinePreview
