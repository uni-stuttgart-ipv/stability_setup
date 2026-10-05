import axios from "axios";

// Use whatever host the page itself was loaded from (localhost, a LAN IP,
// etc.) instead of hardcoding 127.0.0.1 — that only ever resolves to the
// device making the request, which breaks API calls from any other device
// on the network.
export const API_BASE_URL = `http://${window.location.hostname}:8000`;

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/`,
  headers: {
    "Content-Type": "application/json",
  },
});

export default apiClient;