import { useEffect, useRef, useState } from 'react'
import type { ExperimentAction, ExperimentBlock } from '../../types'
import { createAction } from '../../utils/experiment'

interface ExperimentBlockEditorProps {
  block: ExperimentBlock
  index: number
  isFirst: boolean
  isLast: boolean
  onChange: (block: ExperimentBlock) => void
  onDelete: () => void
  onDuplicate: () => void
  onMoveUp: () => void
  onMoveDown: () => void
}

function ExperimentBlockEditor({
  block,
  index,
  isFirst,
  isLast,
  onChange,
  onDelete,
  onDuplicate,
  onMoveUp,
  onMoveDown,
}: ExperimentBlockEditorProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [])

  function updateAction(actionId: string, patch: Partial<Pick<ExperimentAction, 'setIntensityPercent' | 'durationHours'>>) {
    onChange({
      ...block,
      actions: block.actions.map((action) => (action.id === actionId ? { ...action, ...patch } : action)),
    })
  }

  function removeAction(actionId: string) {
    onChange({ ...block, actions: block.actions.filter((action) => action.id !== actionId) })
  }

  function addAction() {
    onChange({ ...block, actions: [...block.actions, createAction()] })
  }

  return (
    <div className="rounded-[10px] border border-border bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-[0.8rem] font-semibold tracking-[0.03em] text-text-muted">BLOCK {index + 1}</span>
        <div className="flex items-center gap-2">
          <select
            value={block.repeatMode}
            onChange={(event) => onChange({ ...block, repeatMode: event.target.value as ExperimentBlock['repeatMode'] })}
            className="cursor-pointer rounded-md border border-border bg-surface px-2 py-1 text-[0.78rem] text-text"
          >
            <option value="once">Once</option>
            <option value="repeat">Repeat</option>
          </select>
          {block.repeatMode === 'repeat' && (
            <span className="flex items-center gap-1 text-[0.78rem] text-text-muted">
              ×
              <input
                type="number"
                min={1}
                value={block.repeatCount}
                onChange={(event) =>
                  onChange({ ...block, repeatCount: Math.max(1, Number(event.target.value) || 1) })
                }
                className="w-14 rounded-md border border-border bg-surface px-2 py-1 text-right text-text [font-variant-numeric:tabular-nums]"
              />
            </span>
          )}

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label="Block options"
              className="cursor-pointer rounded-md border border-border bg-surface px-2 py-1 text-text-muted hover:bg-surface-muted hover:text-text"
            >
              ⋮
            </button>
            {menuOpen && (
              <div className="absolute top-[calc(100%+0.3rem)] right-0 z-20 min-w-[140px] rounded-lg border border-border bg-surface p-1 shadow-[0_8px_24px_rgba(0,0,0,0.12)]">
                <button
                  type="button"
                  onClick={() => {
                    onDuplicate()
                    setMenuOpen(false)
                  }}
                  className="block w-full cursor-pointer rounded-md px-2 py-1 text-left text-[0.8rem] text-text hover:bg-surface-muted"
                >
                  Duplicate block
                </button>
                <button
                  type="button"
                  disabled={isFirst}
                  onClick={() => {
                    onMoveUp()
                    setMenuOpen(false)
                  }}
                  className="block w-full cursor-pointer rounded-md px-2 py-1 text-left text-[0.8rem] text-text hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Move up
                </button>
                <button
                  type="button"
                  disabled={isLast}
                  onClick={() => {
                    onMoveDown()
                    setMenuOpen(false)
                  }}
                  className="block w-full cursor-pointer rounded-md px-2 py-1 text-left text-[0.8rem] text-text hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Move down
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={onDelete}
            aria-label="Delete block"
            className="cursor-pointer rounded-md border border-border bg-surface px-2 py-1 text-text-muted hover:border-error hover:text-error"
          >
            🗑
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {block.actions.map((action, actionIndex) => (
          <div key={action.id} className="flex flex-wrap items-center gap-3 rounded-md bg-surface-muted px-3 py-2">
            <span className="text-[0.75rem] font-medium text-text-muted">ACTION {actionIndex + 1}</span>
            <label className="flex items-center gap-2 text-[0.82rem] text-text">
              Set Intensity
              <input
                type="number"
                min={0}
                max={100}
                value={action.setIntensityPercent}
                onChange={(event) => updateAction(action.id, { setIntensityPercent: Number(event.target.value) })}
                className="w-16 rounded-md border border-border bg-surface px-2 py-1 text-right [font-variant-numeric:tabular-nums]"
              />
              %
            </label>
            <label className="flex items-center gap-2 text-[0.82rem] text-text">
              Duration
              <input
                type="number"
                min={0}
                value={action.durationHours}
                onChange={(event) => updateAction(action.id, { durationHours: Number(event.target.value) })}
                className="w-16 rounded-md border border-border bg-surface px-2 py-1 text-right [font-variant-numeric:tabular-nums]"
              />
              hours
            </label>
            <button
              type="button"
              onClick={() => removeAction(action.id)}
              disabled={block.actions.length === 1}
              aria-label="Remove action"
              className="ml-auto cursor-pointer rounded-md px-2 py-1 text-error hover:opacity-70 disabled:cursor-not-allowed disabled:opacity-30"
            >
              ✕
            </button>
          </div>
        ))}

        <button
          type="button"
          onClick={addAction}
          className="cursor-pointer self-start rounded-md border border-dashed border-border px-3 py-[0.35rem] text-[0.8rem] text-text-muted hover:border-accent hover:text-accent"
        >
          + Add Action
        </button>
      </div>
    </div>
  )
}

export default ExperimentBlockEditor
