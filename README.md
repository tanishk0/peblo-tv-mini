# Peblo TV Mini

A full-stack media platform project structured with:

- **`backend/`**: FastAPI REST API, SQLAlchemy 2.0 ORM, Alembic migrations, and PostgreSQL.
- **`cms/`**: Content management interface (Phase 2).
- **`viewer/`**: Client viewing application (Phase 3).

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
