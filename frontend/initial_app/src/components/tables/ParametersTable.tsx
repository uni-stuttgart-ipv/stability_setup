import type { SolarSimulatorReading } from '../../types'
import './ParametersTable.css'

type ReadingRow = Partial<Record<keyof SolarSimulatorReading, number>>

interface ParametersTableProps {
  reading: ReadingRow | null
}

const COLUMNS: { key: keyof SolarSimulatorReading; label: string; unit: string; digits: number }[] = [
  { key: 'temperature', label: 'Temperature', unit: '°C', digits: 1 },
  { key: 'setLightIntensity', label: 'Set Light Intensity', unit: '%', digits: 0 },
  { key: 'measuredLightIntensity', label: 'Measured Light Intensity', unit: '%', digits: 1 },
  { key: 'voltage', label: 'Voltage', unit: 'V', digits: 2 },
  { key: 'current', label: 'Current', unit: 'A', digits: 2 },
]

function ParametersTable({ reading }: ParametersTableProps) {
  return (
    <table className="parameters-table">
      <thead>
        <tr>
          {COLUMNS.map((column) => (
            <th key={column.key}>{column.label.toUpperCase()}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          {COLUMNS.map((column) => {
            const value = reading?.[column.key]
            return (
              <td key={column.key}>{value != null ? `${value.toFixed(column.digits)} ${column.unit}` : '—'}</td>
            )
          })}
        </tr>
      </tbody>
    </table>
  )
}

export default ParametersTable
