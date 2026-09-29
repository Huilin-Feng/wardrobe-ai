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

// FastAPI puts error details in response.data.detail in three shapes:
// a string, an object from our own handlers, or a list from request validation.
export function describeError(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.missing?.length) return `${detail.message}: ${detail.missing.join(', ')}`
  if (detail?.message) return detail.message
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return error.message
}

export async function recommendOutfit(city, occasion) {
  // Weather lookup plus an LLM call can take a while; allow more than the default.
  const response = await api.post('/api/recommend', { city, occasion }, { timeout: 60000 })
  return response.data
}