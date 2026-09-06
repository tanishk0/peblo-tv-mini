export type Role = 'editor' | 'admin'
export type Status = 'draft' | 'published' | 'archived'
export type ArtworkType = 'poster' | 'banner' | 'thumbnail'
export interface User { id: number; email: string; role: Role; created_at: string }
export interface TokenResponse { access_token: string; token_type: string; user: User }
export interface Show { id: number; title: string; slug: string; synopsis: string | null; section: string | null; categories: string[]; status: Status; created_at: string; updated_at: string }
export interface Season { id: number; show_id: number; season_number: number; created_at: string; updated_at: string }
export interface Episode { id: string; show_id: number; season_id: number; episode_number: number; title: string; synopsis: string | null; duration_seconds: number | null; language: string; content_group: string; status: Status; artwork_types: ArtworkType[]; created_at: string; updated_at: string }
export interface Page<T> { items: T[]; total: number; offset: number; limit: number }
export interface Artwork { id: number; episode_id: string; type: ArtworkType; storage_key: string; url: string; width: number; height: number; file_size_bytes: number; created_at: string }
export interface Issue { field: string; message: string; action: 'editor' | 'engineering' }
export interface ValidationReport { can_publish: boolean; total_issues: number; shows: { show_id: number; show_title: string; issues: Issue[]; episodes: { episode_id: string; episode_title: string; issues: Issue[] }[] }[]; data_quality_issues: { show_id: number | null; show_title: string; episode_id: string; episode_title: string; message: string; action: 'engineering' }[] }
export interface PublishResult { status: string; publish_run_id: number; catalogue_version: string; show_count: number; episode_count: number; completed_at: string }
export interface PublishRun { id: number; status: string; show_count: number; episode_count: number; error_message: string | null; catalogue_version: string | null; started_at: string; completed_at: string | null }
