import { useEffect, useMemo, useState } from 'react'
import { createExperiment } from '../../api/experimentApi'
import type { ExperimentBlock } from '../../types'
import {
  buildExperimentPayload,
  createBlock,
  duplicateBlock as cloneBlock,
  totalExperimentDurationHours,
} from '../../utils/experiment'
import { toLocalInputValue } from '../../utils/timeRange'
import ExperimentBlockEditor from './ExperimentBlockEditor'
import ExperimentTimelinePreview from './ExperimentTimelinePreview'

interface CreateExperimentModalProps {
  deviceId: string
  deviceLabel: string
  onClose: () => void
}

function CreateExperimentModal({ deviceId, deviceLabel, onClose }: CreateExperimentModalProps) {
  const [name, setName] = useState('')
  const [startTime, setStartTime] = useState(() => toLocalInputValue(new Date()))
  const [blocks, setBlocks] = useState<ExperimentBlock[]>(() => [createBlock()])
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // End time isn't user-set — it's always start time + however long the protocol
  // below actually takes to run (blocks run back-to-back, repeats included), so it
  // stays in sync automatically as the start time or the blocks change.
  const totalDurationHours = useMemo(() => totalExperimentDurationHours(blocks), [blocks])
  const endTime = useMemo(() => {
    const start = new Date(startTime)
    if (!startTime || Number.isNaN(start.getTime())) return ''
    return toLocalInputValue(new Date(start.getTime() + totalDurationHours * 60 * 60_000))
  }, [startTime, totalDurationHours])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [onClose])

  function updateBlock(updated: ExperimentBlock) {
    setBlocks((prev) => prev.map((block) => (block.id === updated.id ? updated : block)))
  }

  function deleteBlock(id: string) {
    setBlocks((prev) => prev.filter((block) => block.id !== id))
  }

  function duplicateBlockAt(id: string) {
    setBlocks((prev) => {
      const index = prev.findIndex((block) => block.id === id)
      if (index === -1) return prev
      const next = [...prev]
      next.splice(index + 1, 0, cloneBlock(prev[index]))
      return next
    })
  }

  function moveBlock(id: string, direction: -1 | 1) {
    setBlocks((prev) => {
      const index = prev.findIndex((block) => block.id === id)
      const targetIndex = index + direction
      if (index === -1 || targetIndex < 0 || targetIndex >= prev.length) return prev
      const next = [...prev]
      ;[next[index], next[targetIndex]] = [next[targetIndex], next[index]]
      return next
    })
  }

  function addBlock() {
    setBlocks((prev) => [...prev, createBlock()])
  }

  async function handleCreate() {
    const trimmedName = name.trim()

    if (!trimmedName) {
      setValidationError('Give the experiment a name.')
      return
    }
    if (!startTime) {
      setValidationError('Set a start time.')
      return
    }
    if (blocks.length === 0 || blocks.every((block) => block.actions.length === 0)) {
      setValidationError('Add at least one block with an action.')
      return
    }
    if (totalDurationHours <= 0) {
      setValidationError('Every action needs a duration greater than zero.')
      return
    }
    const start = new Date(startTime)
    const end = new Date(endTime)

    setValidationError(null)
    setIsSubmitting(true)
    try {
      const payload = buildExperimentPayload({
        name: trimmedName,
        deviceId,
        startTime: start.toISOString(),
        endTime: end.toISOString(),
        blocks,
      })
      await createExperiment(payload)
      onClose()
    } catch (error) {
      console.error('Failed to create experiment:', error)
      setValidationError("Couldn't save the experiment. Check that the API server is running.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-8"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[960px] rounded-[14px] border border-border bg-surface shadow-[0_20px_60px_rgba(0,0,0,0.35)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="m-0 text-[1.15rem] font-semibold text-text">Create Experiment</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-error bg-error leading-none text-white hover:opacity-85"
          >
            ✕
          </button>
        </div>

        <div className="max-h-[75vh] overflow-y-auto">
          <div className="flex flex-col gap-4 border-b border-border px-6 py-5">
            <label className="flex flex-col gap-1 text-[0.85rem] text-text-muted">
              Experiment Name
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Long-Term Stability Test"
                className="rounded-md border border-border bg-surface px-3 py-2 text-[0.9rem] text-text"
              />
            </label>

            <label className="flex max-w-xs flex-col gap-1 text-[0.85rem] text-text-muted">
              Setup / Device
              <input
                type="text"
                value={deviceLabel}
                readOnly
                className="cursor-not-allowed rounded-md border border-border bg-surface-muted px-3 py-2 text-[0.9rem] text-text-muted"
              />
            </label>

            <div className="flex flex-wrap gap-4">
              <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-[0.85rem] text-text-muted">
                Start Time
                <input
                  type="datetime-local"
                  value={startTime}
                  onChange={(event) => setStartTime(event.target.value)}
                  className="rounded-md border border-border bg-surface px-3 py-2 text-[0.9rem] text-text [font-variant-numeric:tabular-nums]"
                />
              </label>
              <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-[0.85rem] text-text-muted">
                End Time
                <input
                  type="datetime-local"
                  value={endTime}
                  readOnly
                  className="cursor-not-allowed rounded-md border border-border bg-surface-muted px-3 py-2 text-[0.9rem] text-text-muted [font-variant-numeric:tabular-nums]"
                />
              </label>
            </div>
          </div>

          <div className="border-b border-border px-6 py-5">
            <h3 className="mb-4 text-[0.8rem] font-semibold tracking-[0.05em] text-text-muted">PROTOCOL</h3>
            <div className="flex flex-col">
              {blocks.map((block, index) => (
                <div key={block.id}>
                  <ExperimentBlockEditor
                    block={block}
                    index={index}
                    isFirst={index === 0}
                    isLast={index === blocks.length - 1}
                    onChange={updateBlock}
                    onDelete={() => deleteBlock(block.id)}
                    onDuplicate={() => duplicateBlockAt(block.id)}
                    onMoveUp={() => moveBlock(block.id, -1)}
                    onMoveDown={() => moveBlock(block.id, 1)}
                  />
                  {index < blocks.length - 1 && (
                    <div className="flex justify-center py-1 text-text-muted" aria-hidden="true">
                      ↓
                    </div>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addBlock}
              className="mt-3 cursor-pointer rounded-md border border-dashed border-border px-4 py-2 text-[0.85rem] text-text hover:border-accent hover:text-accent"
            >
              + Add Block
            </button>
          </div>

          <div className="px-6 py-5">
            <h3 className="mb-3 text-[0.8rem] font-semibold tracking-[0.05em] text-text-muted">TIMELINE PREVIEW</h3>
            <ExperimentTimelinePreview blocks={blocks} />
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <span className="text-[0.8rem] text-error">{validationError}</span>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded-lg border border-border bg-surface px-4 py-2 text-[0.9rem] text-text hover:bg-surface-muted"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleCreate}
              disabled={isSubmitting}
              className="cursor-pointer rounded-lg border border-border bg-accent px-4 py-2 text-[0.9rem] text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              Create Experiment
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CreateExperimentModal
