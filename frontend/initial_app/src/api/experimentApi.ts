import apiClient from './client'
import type { Experiment, ExperimentPayload } from '../types'

export async function createExperiment(payload: ExperimentPayload): Promise<Experiment> {
  const response = await apiClient.post<Experiment>('/api/v1/experiments', payload)
  return response.data
}

export async function fetchExperiments(): Promise<Experiment[]> {
  const response = await apiClient.get<Experiment[]>('/api/v1/experiments')
  return response.data
}
