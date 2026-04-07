from sqlmodel import SQLModel, Session, create_engine
from .config import DATABASE_URL


def _normalize(url: str) -> str:
    # Vercel/Neon often expose `postgres://` — SQLAlchemy wants `postgresql+psycopg://`
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_url = _normalize(DATABASE_URL)
_is_sqlite = _url.startswith("sqlite")

engine = create_engine(
    _url,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)


def init_db() -> None:
    from . import models  # noqa: F401  ensure models register
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
