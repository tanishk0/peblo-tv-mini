"""Authenticated CRUD endpoints for the internal CMS content hierarchy."""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, require_admin, require_editor
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.schemas.content import (
    EpisodeCreate, EpisodePage, EpisodeResponse, EpisodeUpdate,
    SeasonCreate, SeasonPage, SeasonResponse, SeasonUpdate,
    ShowCreate, ShowPage, ShowResponse, ShowUpdate,
)
from app.services.publish_validation import episode_publish_issues, show_publish_issues


shows_router = APIRouter()
seasons_router = APIRouter()
episodes_router = APIRouter()


def not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} not found")


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


def commit_or_conflict(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict(message)


def validate_show_publish(show: Show) -> None:
    issues = show_publish_issues(show)
    if issues:
        raise HTTPException(422, detail=issues[0]["message"])


def validate_episode_relationship(db: Session, episode: Episode) -> Season:
    season = db.get(Season, episode.season_id)
    if not season:
        raise HTTPException(422, detail="season_id does not reference an existing season")
    if season.show_id != episode.show_id:
        raise HTTPException(422, detail="season_id must belong to the supplied show_id")
    return season


def validate_episode_publish(episode: Episode, season: Season | None = None) -> None:
    issues = episode_publish_issues(episode, season or episode.season)
    if issues:
        raise HTTPException(422, detail=issues[0]["message"])


def episode_response(episode: Episode) -> EpisodeResponse:
    result = EpisodeResponse.model_validate(episode)
    result.artwork_types = sorted((artwork.type for artwork in episode.artworks), key=lambda item: item.value)
    return result


@shows_router.post("", response_model=ShowResponse, status_code=status.HTTP_201_CREATED)
def create_show(payload: ShowCreate, db: Session = Depends(get_db), _=Depends(require_editor)):
    show = Show(**payload.model_dump())
    validate_show_publish(show)
    db.add(show)
    commit_or_conflict(db, "A show with this slug already exists")
    db.refresh(show)
    return show


@shows_router.get("", response_model=ShowPage)
def list_shows(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _=Depends(require_editor)):
    return {"items": db.query(Show).order_by(Show.id).offset(offset).limit(limit).all(), "total": db.query(func.count(Show.id)).scalar(), "offset": offset, "limit": limit}


@shows_router.get("/{show_id}", response_model=ShowResponse)
def get_show(show_id: int, db: Session = Depends(get_db), _=Depends(require_editor)):
    return db.get(Show, show_id) or (_ for _ in ()).throw(not_found("Show"))


@shows_router.patch("/{show_id}", response_model=ShowResponse)
def update_show(show_id: int, payload: ShowUpdate, db: Session = Depends(get_db), _=Depends(require_editor)):
    show = db.get(Show, show_id)
    if not show:
        raise not_found("Show")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(show, field, value)
    validate_show_publish(show)
    commit_or_conflict(db, "A show with this slug already exists")
    db.refresh(show)
    return show


@shows_router.delete("/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_show(show_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    show = db.get(Show, show_id)
    if not show:
        raise not_found("Show")
    db.delete(show)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@seasons_router.post("/shows/{show_id}/seasons", response_model=SeasonResponse, status_code=status.HTTP_201_CREATED)
def create_season(show_id: int, payload: SeasonCreate, db: Session = Depends(get_db), _=Depends(require_editor)):
    if not db.get(Show, show_id):
        raise not_found("Show")
    season = Season(show_id=show_id, **payload.model_dump())
    db.add(season)
    commit_or_conflict(db, "That season number already exists for this show")
    db.refresh(season)
    return season


@seasons_router.get("/shows/{show_id}/seasons", response_model=SeasonPage)
def list_show_seasons(show_id: int, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _=Depends(require_editor)):
    if not db.get(Show, show_id):
        raise not_found("Show")
    query = db.query(Season).filter(Season.show_id == show_id)
    return {"items": query.order_by(Season.season_number).offset(offset).limit(limit).all(), "total": query.count(), "offset": offset, "limit": limit}


@seasons_router.get("/seasons/{season_id}", response_model=SeasonResponse)
def get_season(season_id: int, db: Session = Depends(get_db), _=Depends(require_editor)):
    return db.get(Season, season_id) or (_ for _ in ()).throw(not_found("Season"))


@seasons_router.patch("/seasons/{season_id}", response_model=SeasonResponse)
def update_season(season_id: int, payload: SeasonUpdate, db: Session = Depends(get_db), _=Depends(require_editor)):
    season = db.get(Season, season_id)
    if not season:
        raise not_found("Season")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(season, field, value)
    commit_or_conflict(db, "That season number already exists for this show")
    db.refresh(season)
    return season


@seasons_router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(season_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    season = db.get(Season, season_id)
    if not season:
        raise not_found("Season")
    db.delete(season)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@episodes_router.post("", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
def create_episode(payload: EpisodeCreate, db: Session = Depends(get_db), _=Depends(require_editor)):
    values = payload.model_dump()
    values["id"] = values["id"] or str(uuid4())
    episode = Episode(**values)
    season = validate_episode_relationship(db, episode)
    validate_episode_publish(episode, season)
    db.add(episode)
    commit_or_conflict(db, "An episode already uses this id or this content_group and language combination")
    return episode_response(db.query(Episode).options(selectinload(Episode.artworks)).filter(Episode.id == episode.id).one())


@episodes_router.get("", response_model=EpisodePage)
def list_episodes(show_id: int | None = Query(None, gt=0), season_id: int | None = Query(None, gt=0), offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _=Depends(require_editor)):
    query = db.query(Episode).options(selectinload(Episode.artworks))
    if show_id is not None:
        query = query.filter(Episode.show_id == show_id)
    if season_id is not None:
        query = query.filter(Episode.season_id == season_id)
    total = query.count()
    items = query.order_by(Episode.season_id, Episode.episode_number, Episode.id).offset(offset).limit(limit).all()
    return {"items": [episode_response(item) for item in items], "total": total, "offset": offset, "limit": limit}


@episodes_router.get("/{episode_id}", response_model=EpisodeResponse)
def get_episode(episode_id: str, db: Session = Depends(get_db), _=Depends(require_editor)):
    episode = db.query(Episode).options(selectinload(Episode.artworks)).filter(Episode.id == episode_id).first()
    if not episode:
        raise not_found("Episode")
    return episode_response(episode)


@episodes_router.patch("/{episode_id}", response_model=EpisodeResponse)
def update_episode(episode_id: str, payload: EpisodeUpdate, db: Session = Depends(get_db), _=Depends(require_editor)):
    episode = db.query(Episode).options(selectinload(Episode.artworks)).filter(Episode.id == episode_id).first()
    if not episode:
        raise not_found("Episode")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(episode, field, value)
    season = validate_episode_relationship(db, episode)
    validate_episode_publish(episode, season)
    commit_or_conflict(db, "Another episode already uses this content_group and language combination")
    db.refresh(episode)
    return episode_response(episode)


@episodes_router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(episode_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise not_found("Episode")
    db.delete(episode)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
