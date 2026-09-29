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

export async function uploadClothing(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post('/api/clothing/upload', form)
  return response.data
}

export async function deleteClothing(id) {
  await api.delete(`/api/clothing/${id}`)
}

// The backend stores paths like "./uploads/abc.jpg"; the browser needs a full URL.
export function imageUrl(item) {
  const path = item.image_url.replace(/^\.?\//, '')
  return `${API_BASE_URL}/${path}`
}

// FastAPI puts error details in response.data.detail, sometimes as a string,
// sometimes as an object (e.g. the missing-category error from /api/recommend).
export function describeError(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return error.message
}