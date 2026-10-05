import { useEffect } from 'react'
import { getInfluxStreamUrl, mapValuesToReading, type LiveReading } from '../api/influxApi'

export function useSolarSimulatorStream(sensor: string | undefined, onReading: (reading: LiveReading) => void) {
  useEffect(() => {
    if (!sensor) return
    const source = new EventSource(getInfluxStreamUrl(sensor))
    source.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      onReading(mapValuesToReading(payload.values ?? {}))
    }
    return () => source.close()
  }, [sensor, onReading])
}
