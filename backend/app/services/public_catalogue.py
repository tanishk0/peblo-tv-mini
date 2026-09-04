"""Read and search published catalogue snapshots without CMS database access."""
from copy import deepcopy

from app.services.catalogue_storage import CatalogueStorageProvider


class PublicCatalogueService:
    """Snapshot-only read model used by public viewer endpoints."""

    def __init__(self, storage: CatalogueStorageProvider):
        self.storage = storage

    def current(self) -> dict:
        catalogue = self.storage.read_current()
        if catalogue is None:
            raise LookupError("No published catalogue is available yet.")
        return catalogue

    def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        language: str | None = None,
        section: str | None = None,
    ) -> dict:
        catalogue = self.current()
        query = q.casefold().strip() if q else None
        category_filter = category.casefold().strip() if category else None
        language_filter = language.casefold().strip() if language else None
        section_filter = section.casefold().strip() if section else None

        result_sections = []
        total_shows = 0
        total_entries = 0
        for source_section in catalogue.get("sections", []):
            if section_filter and source_section["id"].casefold() != section_filter:
                continue
            matching_shows = []
            for source_show in source_section.get("shows", []):
                categories = source_show.get("categories", [])
                if category_filter and not any(item.casefold() == category_filter for item in categories):
                    continue
                show_matches_query = bool(query and (
                    query in source_show.get("title", "").casefold()
                    or any(query in item.casefold() for item in categories)
                ))
                show = self._filtered_show(source_show, query, language_filter, show_matches_query)
                has_entries = any(season["episodes"] for season in show["seasons"]) or bool(show["trailers"])
                # A show-title/category search is still useful when the show has
                # no episodes; a language-only search is not.
                if has_entries or (show_matches_query and not language_filter) or (not query and not language_filter):
                    matching_shows.append(show)
                    total_shows += 1
                    total_entries += sum(len(season["episodes"]) for season in show["seasons"]) + len(show["trailers"])
            if matching_shows:
                result_sections.append({"id": source_section["id"], "shows": matching_shows})

        return {
            "schema_version": catalogue.get("schema_version", 1),
            "total_shows": total_shows,
            "total_entries": total_entries,
            "sections": result_sections,
        }

    def _filtered_show(self, source_show: dict, query: str | None, language: str | None, show_matches_query: bool) -> dict:
        show = {key: deepcopy(value) for key, value in source_show.items() if key not in {"seasons", "trailers"}}
        show["seasons"] = []
        for season in source_show.get("seasons", []):
            entries = self._filtered_entries(season.get("episodes", []), query, language, show_matches_query)
            if entries:
                show["seasons"].append({"season_number": season["season_number"], "episodes": entries})
        show["trailers"] = self._filtered_entries(source_show.get("trailers", []), query, language, show_matches_query)
        return show

    def _filtered_entries(self, entries: list[dict], query: str | None, language: str | None, show_matches_query: bool) -> list[dict]:
        result = []
        for source_entry in entries:
            variants = [
                deepcopy(variant)
                for variant in source_entry.get("languages", [])
                if not language or variant.get("language", "").casefold() == language
            ]
            episode_matches_query = bool(query and any(query in variant.get("title", "").casefold() for variant in source_entry.get("languages", [])))
            if not variants or (query and not show_matches_query and not episode_matches_query):
                continue
            entry = {key: deepcopy(value) for key, value in source_entry.items() if key != "languages"}
            entry["languages"] = variants
            result.append(entry)
        return result
