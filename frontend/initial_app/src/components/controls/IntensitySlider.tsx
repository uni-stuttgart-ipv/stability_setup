import { useEffect, useState } from 'react'

interface IntensitySliderProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

function clamp(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)))
}

function IntensitySlider({ value, onChange, disabled }: IntensitySliderProps) {
  const [inputText, setInputText] = useState(String(value))

  useEffect(() => {
    setInputText(String(value))
  }, [value])

  function handleInputChange(raw: string) {
    setInputText(raw)
    if (raw.trim() === '') return
    const parsed = Number(raw)
    if (!Number.isNaN(parsed)) {
      onChange(clamp(parsed))
    }
  }

  return (
    <div className="flex max-w-[420px] flex-col gap-2">
      <label htmlFor="light-intensity" className="text-[0.95rem]">
        Light Intensity
      </label>
      <div className="flex items-center gap-[0.8rem]">
        <div className="flex min-w-0 flex-1 flex-col gap-[0.3rem]">
          <input
            id="light-intensity"
            type="range"
            min={0}
            max={100}
            step={1}
            value={value}
            disabled={disabled}
            onChange={(event) => onChange(Number(event.target.value))}
            className="w-full accent-accent"
          />
          <div className="flex justify-between text-[0.75rem] text-text-muted">
            <span>0</span>
            <span>100</span>
          </div>
        </div>
        <div className="flex items-center gap-[0.35rem]">
          <input
            type="number"
            min={0}
            max={100}
            step={1}
            value={inputText}
            disabled={disabled}
            onChange={(event) => handleInputChange(event.target.value)}
            onBlur={() => setInputText(String(value))}
            className="w-[4.2rem] rounded-md border border-border bg-surface px-[0.4rem] py-[0.3rem] text-right text-[0.9rem] text-text"
          />
          <span className="text-[0.85rem] text-text-muted">%</span>
        </div>
      </div>
    </div>
  )
}

export default IntensitySlider
