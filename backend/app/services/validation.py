"""Aggregate every current catalogue publishing blocker into a CMS report."""
from collections import OrderedDict

from sqlalchemy.orm import Session, selectinload

from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.services.publish_validation import episode_publish_issues, show_publish_issues


class ValidationService:
    """Builds a complete, grouped publish-readiness report in one database pass."""

    def __init__(self, db: Session):
        self.db = db

    def report(self) -> dict:
        shows = self.db.query(Show).all()
        seasons = {season.id: season for season in self.db.query(Season).all()}
        episodes = (
            self.db.query(Episode)
            .options(selectinload(Episode.artworks))
            .order_by(Episode.show_id, Episode.season_id, Episode.episode_number, Episode.id)
            .all()
        )
        grouped: OrderedDict[int, dict] = OrderedDict()
        known_shows = {show.id: show for show in shows}

        def group_for(show_id: int) -> dict:
            if show_id not in grouped:
                show = known_shows.get(show_id)
                grouped[show_id] = {
                    "show_id": show_id,
                    "show_title": show.title if show else "Unknown show",
                    "issues": [],
                    "episodes": [],
                }
            return grouped[show_id]

        for show in shows:
            issues = show_publish_issues(show)
            if issues:
                group_for(show.id)["issues"].extend(issues)

        for episode in episodes:
            issues = episode_publish_issues(episode, seasons.get(episode.season_id))
            if issues:
                group_for(episode.show_id)["episodes"].append({
                    "episode_id": episode.id,
                    "episode_title": episode.title,
                    "issues": issues,
                })

        report_shows = list(grouped.values())
        total_issues = sum(len(show["issues"]) + sum(len(episode["issues"]) for episode in show["episodes"]) for show in report_shows)
        return {"can_publish": total_issues == 0, "total_issues": total_issues, "shows": report_shows}
