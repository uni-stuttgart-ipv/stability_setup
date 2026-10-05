import type { ExperimentPayload } from '../types'

// The backend route for this hasn't been decided yet — once it is, replace
// this body with a real `apiClient.post(...)` call (see solarSimulatorApi.ts
// for the pattern).
export async function createExperiment(payload: ExperimentPayload): Promise<void> {
  console.log('[experiment] payload ready for backend:', payload)
}
