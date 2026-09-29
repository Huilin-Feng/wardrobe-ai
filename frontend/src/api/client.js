import axios from 'axios'

// Local default; the deployed frontend will set VITE_API_URL instead.
export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

export async function listClothing() {
  const response = await api.get('/api/clothing')
  return response.data
}