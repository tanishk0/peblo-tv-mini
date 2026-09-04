# Peblo TV Mini - Backend

FastAPI backend foundation for Peblo TV Mini, powered by SQLAlchemy 2.0, Alembic migrations, and PostgreSQL.

## Features

- **FastAPI**: Modern, high-performance web framework with automatic OpenAPI documentation.
- **SQLAlchemy 2.0**: Modern declarative ORM and connection pooling.
- **Alembic**: Database migrations configured with dynamic environment settings.
- **Pydantic Settings**: Centralized environment variable parsing and validation via `.env`.
- **Health Check**: `GET /health` endpoint for uptime monitoring and orchestration health probes.

---

## Directory Layout

```text
backend/
├── alembic/
│   ├── versions/            # Database migration revisions
│   ├── env.py               # Alembic runtime environment (loads app config & metadata)
│   └── script.py.mako       # Migration template
├── alembic.ini              # Alembic configuration
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py # Health check endpoint
│   │       └── api.py       # v1 router aggregator
│   ├── core/
│   │   └── config.py        # Settings and environment configuration
│   ├── db/
│   │   ├── base.py          # DeclarativeBase metadata registry
│   │   └── session.py       # Engine, SessionLocal & get_db dependency
│   ├── models/              # SQLAlchemy 2.0 ORM data models
│   │   ├── enums.py         # ContentStatus, UserRole, ArtworkType, etc.
│   │   ├── user.py          # User accounts
│   │   ├── show.py          # Shows
│   │   ├── season.py        # Seasons (Season 0 for trailers)
│   │   ├── episode.py       # Episodes with UNIQUE(content_group, language)
│   │   ├── artwork.py       # Artworks with UNIQUE(episode_id, type)
│   │   └── publish_run.py   # Catalog publication audit logs
│   └── main.py              # FastAPI entrypoint, middleware, root routes
├── tests/
│   ├── test_health.py       # Health check tests
│   └── test_models.py       # Model constraint & relationship tests
├── .env.example             # Example environment variables
├── requirements.txt         # Project dependencies
└── README.md
```

---

## Getting Started

### 1. Create and Activate a Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and adjust database credentials as needed:

```bash
cp .env.example .env
```

### 4. Run the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Root: [http://localhost:8000/](http://localhost:8000/)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Database Migrations (Alembic)

Database credentials are automatically picked up from your `.env` file via `app/core/config.py`.

```bash
# Generate a new migration revision
alembic revision --autogenerate -m "create_initial_tables"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Running Tests

```bash
pytest
```

---

## Authentication & Authorization (CMS API)

The internal CMS API enforces role-based access control via JWT Bearer tokens:

- **Login**: `POST /api/v1/auth/login` with JSON `{ "email": "...", "password": "..." }`
- **Current User**: `GET /api/v1/auth/me` (requires `Authorization: Bearer <token>`)
- **Roles**:
  - `editor`: Access to CRUD operations.
  - `admin`: Access to CRUD operations and publishing endpoints.
- **Enforcement**:
  - `require_editor`: Accepts `editor` and `admin`.
  - `require_admin`: Accepts only `admin` (editors receive `403 Forbidden`).
  - Unauthenticated requests receive `401 Unauthorized`.

