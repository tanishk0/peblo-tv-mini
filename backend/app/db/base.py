from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 DeclarativeBase.

    All ORM models inherit from this class, allowing
    Alembic's env.py to discover all metadata automatically.
    """
    pass


# Import models so Base.metadata is populated for Alembic migrations
import app.models  # noqa: F401

