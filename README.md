# Peblo TV Mini

A full-stack media platform project structured with:

- **`backend/`**: FastAPI REST API, SQLAlchemy 2.0 ORM, Alembic migrations, and PostgreSQL.
- **`cms/`**: Content management interface (Phase 2).
- **`viewer/`**: Client viewing application (Phase 3).

## Run the complete stack with Docker

Copy `.env.example` to `.env` if you need to change the default local
credentials, then run:

```bash
docker-compose up --build
```

This starts PostgreSQL, the FastAPI API, CMS, and public viewer.  The backend
waits for PostgreSQL, applies Alembic migrations, and idempotently seeds the
supplied catalogue fixture on every startup.  PostgreSQL and local published
catalogue data are persisted in Docker volumes.

- CMS: http://localhost:5173
- Viewer: http://localhost:5174
- API: http://localhost:8000/docs
- Seeded admin: `admin@peblo.tv` / `admin123`
- Seeded editor: `editor@peblo.tv` / `editor123`

After first startup, sign in to the CMS as the seeded admin and publish the
seeded catalogue; the viewer intentionally reads only a published snapshot.

---

## Phase 1: Backend Setup

To run the backend locally:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows (or: source .venv/bin/activate on Unix)
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Check health status:
```bash
curl http://localhost:8000/health
```
