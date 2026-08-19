import { useEffect, useRef, useState } from 'react'
import type { TimeRange } from '../../types'
import { TIME_RANGE_PRESETS, buildCustomRange, resolvePresetRange, toLocalInputValue } from '../../utils/timeRange'

interface TimeRangeSelectProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

function TimeRangeSelect({ value, onChange }: TimeRangeSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showCustom, setShowCustom] = useState(value.preset === 'custom')
  const [customFrom, setCustomFrom] = useState(() => toLocalInputValue(value.from))
  const [customTo, setCustomTo] = useState(() => toLocalInputValue(value.to))
  const [customError, setCustomError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  function handlePresetSelect(key: (typeof TIME_RANGE_PRESETS)[number]['key']) {
    setCustomError(null)
    setShowCustom(false)
    onChange(resolvePresetRange(key))
    setIsOpen(false)
  }

  function handleApplyCustom() {
    if (!customFrom || !customTo) {
      setCustomError('Pick both a start and end time.')
      return
    }
    const from = new Date(customFrom)
    const to = new Date(customTo)
    if (from.getTime() >= to.getTime()) {
      setCustomError('Start must be before end.')
      return
    }
    setCustomError(null)
    onChange(buildCustomRange(from, to))
    setIsOpen(false)
  }

  return (
    <div className="relative inline-block" ref={containerRef}>
      <button
        type="button"
        className="flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-surface px-3 py-[0.45rem] text-[0.85rem] text-text hover:bg-surface-muted"
        onClick={() => setIsOpen((open) => !open)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span>{value.label}</span>
        <span className="text-[0.7rem] text-text-muted" aria-hidden="true">
          ▾
        </span>
      </button>

      {isOpen && (
        <div
          className="absolute top-[calc(100%+0.4rem)] left-0 z-20 min-w-[200px] rounded-[10px] border border-border bg-surface p-[0.35rem] shadow-[0_8px_24px_rgba(0,0,0,0.12)]"
          role="listbox"
        >
          {TIME_RANGE_PRESETS.map((option) => (
            <button
              type="button"
              key={option.key}
              className="flex w-full cursor-pointer items-center gap-[0.55rem] rounded-md px-2 py-[0.4rem] text-left text-[0.85rem] text-text hover:bg-surface-muted"
              role="option"
              aria-selected={value.preset === option.key}
              onClick={() => handlePresetSelect(option.key)}
            >
              <span className="inline-flex w-4 justify-center text-base font-bold text-accent" aria-hidden="true">
                {value.preset === option.key ? '✓' : ''}
              </span>
              <span>{option.label}</span>
            </button>
          ))}

          <div className="mt-[0.35rem] border-t border-border pt-[0.35rem]">
            <button
              type="button"
              className="flex w-full cursor-pointer items-center gap-[0.55rem] rounded-md px-2 py-[0.4rem] text-left text-[0.85rem] text-text hover:bg-surface-muted"
              role="option"
              aria-selected={value.preset === 'custom'}
              onClick={() => setShowCustom((show) => !show)}
            >
              <span className="inline-flex w-4 justify-center text-base font-bold text-accent" aria-hidden="true">
                {value.preset === 'custom' ? '✓' : ''}
              </span>
              <span>Custom range</span>
            </button>

            {showCustom && (
              <div className="flex flex-col gap-2 px-2 pt-[0.4rem] pb-[0.2rem]">
                <label className="flex flex-col gap-1 text-[0.78rem] text-text-muted">
                  From
                  <input
                    type="datetime-local"
                    value={customFrom}
                    max={customTo}
                    onChange={(event) => setCustomFrom(event.target.value)}
                    className="rounded-md border border-border bg-surface px-[0.45rem] py-[0.35rem] text-[0.82rem] text-text [font-variant-numeric:tabular-nums]"
                  />
                </label>
                <label className="flex flex-col gap-1 text-[0.78rem] text-text-muted">
                  To
                  <input
                    type="datetime-local"
                    value={customTo}
                    min={customFrom}
                    onChange={(event) => setCustomTo(event.target.value)}
                    className="rounded-md border border-border bg-surface px-[0.45rem] py-[0.35rem] text-[0.82rem] text-text [font-variant-numeric:tabular-nums]"
                  />
                </label>
                {customError && <p className="m-0 text-[0.78rem] text-error">{customError}</p>}
                <button
                  type="button"
                  onClick={handleApplyCustom}
                  className="cursor-pointer self-end rounded-md border border-border bg-accent px-[0.9rem] py-[0.35rem] text-[0.82rem] text-white"
                >
                  Apply
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default TimeRangeSelect
