import { useEffect, useState } from 'react'
import './IntensitySlider.css'

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
    <div className="intensity-slider">
      <label htmlFor="light-intensity">Light Intensity</label>
      <div className="intensity-slider__row">
        <div className="intensity-slider__track">
          <input
            id="light-intensity"
            type="range"
            min={0}
            max={100}
            step={1}
            value={value}
            disabled={disabled}
            onChange={(event) => onChange(Number(event.target.value))}
          />
          <div className="intensity-slider__scale">
            <span>0</span>
            <span>100</span>
          </div>
        </div>
        <div className="intensity-slider__input-group">
          <input
            type="number"
            className="intensity-slider__input"
            min={0}
            max={100}
            step={1}
            value={inputText}
            disabled={disabled}
            onChange={(event) => handleInputChange(event.target.value)}
            onBlur={() => setInputText(String(value))}
          />
          <span className="intensity-slider__unit">%</span>
        </div>
      </div>
    </div>
  )
}

export default IntensitySlider
