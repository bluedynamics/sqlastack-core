"""Smoke test: the PostgreSQL test container is reachable."""

from __future__ import annotations

from sqlalchemy import text


def test_pg_engine_connects(pg_engine):
    with pg_engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
