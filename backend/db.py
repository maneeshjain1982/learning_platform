from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    return engine


engine = make_engine(config.DB_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(bind=None) -> None:
    from . import models  # noqa: F401  (registers tables)

    bind = bind or engine
    Base.metadata.create_all(bind)
    _add_missing_columns(bind)


# Columns added after v1. create_all() doesn't alter existing tables, so add them here.
_NEW_COLUMNS = {
    "users": {"username": "VARCHAR(40)", "password_hash": "VARCHAR(200)",
              "role": "VARCHAR(10) NOT NULL DEFAULT 'user'"},
    "paths": {"user_id": "INTEGER NOT NULL DEFAULT 1", "show_on_home": "BOOLEAN NOT NULL DEFAULT 1", "position": "INTEGER NOT NULL DEFAULT 0",
              "kind": "VARCHAR(20) NOT NULL DEFAULT 'learning'"},
    "agent_runs": {"interview_id": "INTEGER REFERENCES interview_preps(id) ON DELETE SET NULL"},
}


def _add_missing_columns(bind) -> None:
    if not str(bind.url).startswith("sqlite"):
        return
    with bind.begin() as conn:
        for table, cols in _NEW_COLUMNS.items():
            have = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, ddl in cols.items():
                if name not in have:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        # Review-question marks moved to qa_marks (per account); the old marks belong to the admin (user 1).
        if not conn.exec_driver_sql("SELECT 1 FROM qa_marks LIMIT 1").first():
            conn.exec_driver_sql("INSERT OR IGNORE INTO qa_marks (user_id, qa_id, status) "
                                 "SELECT 1, id, status FROM academy_qa WHERE status != 'new'")
            conn.exec_driver_sql("UPDATE academy_qa SET status = 'new' WHERE status != 'new'")


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """For background work: commit on success, roll back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
