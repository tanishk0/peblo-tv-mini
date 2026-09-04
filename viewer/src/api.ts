import type { Catalogue } from './types'

const baseUrl = import.meta.env.VITE_CATALOGUE_API_URL ?? 'http://localhost:8000/api/v1'
export class CatalogueError extends Error { constructor(public status: number, message: string) { super(message) } }
async function get<T>(path: string): Promise<T> {
  let response: Response
  try { response = await fetch(`${baseUrl}${path}`) } catch { throw new CatalogueError(0, 'We could not reach Peblo TV. Please try again.') }
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new CatalogueError(response.status, typeof data.detail === 'string' ? data.detail : 'The catalogue is unavailable right now.') }
  return response.json() as Promise<T>
}
export const catalogueApi = {
  current: () => get<Catalogue>('/catalog'),
  search: (filters: { q?: string; category?: string; language?: string }) => { const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value) }); return get<Catalogue>(`/catalog/search${params.size ? `?${params}` : ''}`) },
}
