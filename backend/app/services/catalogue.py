"""Build the deterministic published read model consumed by the future viewer."""
from collections import defaultdict

from sqlalchemy.orm import Session, selectinload

from app.models.enums import ContentStatus
from app.models.episode import Episode
from app.models.show import Show
from app.services.reference import reference_data
from app.services.storage import LocalStorageProvider


class CatalogueBuilder:
    """Transforms published relational CMS data into a stable JSON catalogue."""

    def __init__(self, db: Session):
        self.db = db
        self.artwork_storage = LocalStorageProvider()
        self.show_count = 0
        self.episode_count = 0

    def build(self) -> dict:
        published_shows = (
            self.db.query(Show)
            .filter(Show.status == ContentStatus.PUBLISHED)
            .order_by(Show.slug, Show.id)
            .all()
        )
        self.show_count = len(published_shows)
        show_ids = [show.id for show in published_shows]
        episodes = []
        if show_ids:
            episodes = (
                self.db.query(Episode)
                .options(selectinload(Episode.artworks), selectinload(Episode.season))
                .filter(Episode.show_id.in_(show_ids), Episode.status == ContentStatus.PUBLISHED)
                .order_by(Episode.show_id, Episode.season_id, Episode.episode_number, Episode.content_group, Episode.language, Episode.id)
                .all()
            )
        episodes_by_show: dict[int, list[Episode]] = defaultdict(list)
        for episode in episodes:
            episodes_by_show[episode.show_id].append(episode)
        self.episode_count = len(episodes)

        sections: dict[str, list[dict]] = defaultdict(list)
        for show in published_shows:
            sections[show.section].append(self._show_entry(show, episodes_by_show[show.id]))

        configured_sections = reference_data()["sections"]
        ordered_sections = [
            {"id": section, "shows": sections[section]}
            for section in configured_sections
            if sections.get(section)
        ]
        # Defensive ordering for historical data that passed validation under
        # an earlier reference file; normal publishing validation prevents it.
        ordered_sections.extend(
            {"id": section, "shows": sections[section]}
            for section in sorted(set(sections) - set(configured_sections))
        )
        return {"schema_version": 1, "sections": ordered_sections}

    def _show_entry(self, show: Show, episodes: list[Episode]) -> dict:
        by_season: dict[int, list[Episode]] = defaultdict(list)
        for episode in episodes:
            by_season[episode.season.season_number].append(episode)

        normal_seasons = [
            {"season_number": number, "episodes": self._collapse_entries(by_season[number])}
            for number in sorted(number for number in by_season if number != 0)
        ]
        trailers = self._collapse_entries(by_season.get(0, []))
        return {
            "id": show.id,
            "slug": show.slug,
            "title": show.title,
            "synopsis": show.synopsis,
            "categories": sorted(show.categories),
            "seasons": normal_seasons,
            "trailers": trailers,
        }

    def _collapse_entries(self, episodes: list[Episode]) -> list[dict]:
        grouped: dict[str, list[Episode]] = defaultdict(list)
        for episode in episodes:
            grouped[episode.content_group].append(episode)
        entries = []
        for content_group, variants in grouped.items():
            variants.sort(key=lambda item: (item.language, item.id))
            primary = variants[0]
            entries.append({
                "content_group": content_group,
                "episode_number": primary.episode_number,
                "title": primary.title,
                "synopsis": primary.synopsis,
                "languages": [self._language_variant(variant) for variant in variants],
            })
        return sorted(entries, key=lambda item: (item["episode_number"], item["content_group"]))

    def _language_variant(self, episode: Episode) -> dict:
        artwork = {}
        for asset in sorted(episode.artworks, key=lambda item: item.type.value):
            artwork[asset.type.value] = {
                "storage_key": asset.storage_key,
                "url": self.artwork_storage.get_url(asset.storage_key),
                "width": asset.width,
                "height": asset.height,
            }
        return {
            "episode_id": episode.id,
            "language": episode.language,
            "title": episode.title,
            "synopsis": episode.synopsis,
            "duration_seconds": episode.duration_seconds,
            "artwork": artwork,
        }
