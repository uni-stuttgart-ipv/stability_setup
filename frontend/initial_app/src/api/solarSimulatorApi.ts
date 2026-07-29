import apiClient from "./client";

// export interface Setup {
//   id: string;
//   name: string;
//   status: string;
// }

export interface IntensityRequest {
  ch0: number;
  ch1: number;
}

export interface IntensityResponse {
    esp32Id: string;
}

// export const getSetups = async (): Promise<Setup[]> => {
//   const response = await apiClient.get<Setup[]>("/setups");
//   return response.data;
// };

// export const getSetup = async (setupId: string): Promise<Setup> => {
//   const response = await apiClient.get<Setup>(`/setups/${setupId}`);
//   return response.data;
// };

export const setIntensitySolar = async (
    deviceID: string,
    intensityRequest: IntensityRequest
): Promise<IntensityResponse> => {
  const response = await apiClient.post<IntensityResponse>(`/set/${deviceID}`, intensityRequest);
  return response.data;
};