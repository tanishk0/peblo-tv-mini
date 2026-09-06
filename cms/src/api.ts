import type { Artwork, Episode, Page, PublishResult, PublishRun, Season, Show, TokenResponse, User, ValidationReport } from './types'

const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
const tokenKey = 'peblo.cms.token'
export class ApiError extends Error { constructor(public status: number, message: string, public detail?: unknown) { super(message) } }
export const authStore = { get: () => localStorage.getItem(tokenKey), set: (token: string) => localStorage.setItem(tokenKey, token), clear: () => localStorage.removeItem(tokenKey) }

function friendlyDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item: { msg?: string }) => item.msg ?? 'Invalid input').join('. ')
  if (detail && typeof detail === 'object' && 'message' in detail) return String((detail as { message: unknown }).message)
  return 'Something went wrong. Please try again.'
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = authStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  let response: Response
  try { response = await fetch(`${baseUrl}${path}`, { ...init, headers }) } catch { throw new ApiError(0, 'Network error. Check that the API is running.') }
  if (!response.ok) { const body = await response.json().catch(() => ({})); if (response.status === 401) { authStore.clear(); window.dispatchEvent(new Event('peblo:unauthorized')) } throw new ApiError(response.status, friendlyDetail(body.detail), body.detail) }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
export const api = {
  login: (email: string, password: string) => request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request<User>('/auth/me'),
  shows: (offset = 0, limit = 20) => request<Page<Show>>(`/shows?offset=${offset}&limit=${limit}`),
  show: (id: string) => request<Show>(`/shows/${id}`),
  createShow: (data: Partial<Show>) => request<Show>('/shows', { method: 'POST', body: JSON.stringify(data) }),
  updateShow: (id: number, data: Partial<Show>) => request<Show>(`/shows/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteShow: (id: number) => request<void>(`/shows/${id}`, { method: 'DELETE' }),
  seasons: (showId: string) => request<Page<Season>>(`/shows/${showId}/seasons?limit=100`),
  createSeason: (showId: number, season_number: number) => request<Season>(`/shows/${showId}/seasons`, { method: 'POST', body: JSON.stringify({ season_number }) }),
  updateSeason: (id: number, season_number: number) => request<Season>(`/seasons/${id}`, { method: 'PATCH', body: JSON.stringify({ season_number }) }),
  deleteSeason: (id: number) => request<void>(`/seasons/${id}`, { method: 'DELETE' }),
  episodes: (params: { showId?: string; seasonId?: string; offset?: number; limit?: number } = {}) => { const query = new URLSearchParams(); if (params.showId) query.set('show_id', params.showId); if (params.seasonId) query.set('season_id', params.seasonId); query.set('offset', String(params.offset ?? 0)); query.set('limit', String(params.limit ?? 100)); return request<Page<Episode>>(`/episodes?${query}`) },
  createEpisode: (data: Partial<Episode>) => request<Episode>('/episodes', { method: 'POST', body: JSON.stringify(data) }),
  updateEpisode: (id: string, data: Partial<Episode>) => request<Episode>(`/episodes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteEpisode: (id: string) => request<void>(`/episodes/${id}`, { method: 'DELETE' }),
  uploadArtwork: (episodeId: string, artwork_type: string, file: File) => { const data = new FormData(); data.set('artwork_type', artwork_type); data.set('file', file); return request<Artwork>(`/episodes/${episodeId}/artwork`, { method: 'POST', body: data }) },
  validationReport: () => request<ValidationReport>('/admin/validation-report'),
  publishRuns: () => request<PublishRun[]>('/admin/publish-runs'),
  publish: () => request<PublishResult>('/admin/catalog/publish', { method: 'POST' }),
}
