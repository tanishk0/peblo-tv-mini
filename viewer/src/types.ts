export type Artwork = { storage_key: string; url: string; width: number; height: number }
export type LanguageVariant = { episode_id: string; language: string; title: string; synopsis: string | null; duration_seconds: number | null; artwork: Partial<Record<'poster'|'banner'|'thumbnail', Artwork>> }
export type EpisodeEntry = { content_group: string; episode_number: number; title: string; synopsis: string | null; languages: LanguageVariant[] }
export type Season = { season_number: number; episodes: EpisodeEntry[] }
export type Show = { id: number; slug: string; title: string; synopsis: string | null; categories: string[]; seasons: Season[]; trailers: EpisodeEntry[] }
export type CatalogueSection = { id: string; shows: Show[] }
export type Catalogue = { schema_version: number; sections: CatalogueSection[]; total_shows?: number; total_entries?: number }
