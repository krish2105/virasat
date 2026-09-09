"""Integration tests run against a dedicated `virasat_test` database, migrated fresh."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator

import pytest

TEST_URL = (
    os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://virasat:virasat@localhost:5434/virasat"
    ).rsplit("/", 1)[0]
    + "/virasat_test"
)
os.environ["DATABASE_URL"] = TEST_URL


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> Iterator[None]:
    import psycopg

    try:
        psycopg.connect(
            TEST_URL.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3
        ).close()
    except psycopg.OperationalError as exc:
        pytest.skip(f"test database not reachable: {exc}")
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    subprocess.run(
        ["uv", "run", "alembic", "downgrade", "base"], check=True, env=env, capture_output=True
    )
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"], check=True, env=env, capture_output=True
    )
    yield


@pytest.fixture()
def client():  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from virasat.api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def officer(client):  # type: ignore[no-untyped-def]
    from virasat.db.models import Officer, Role
    from virasat.db.seed import create_officer
    from virasat.db.session import session_scope

    with session_scope() as s:
        if not s.query(Officer).filter_by(username="test-officer").first():
            create_officer("test-officer", "correct horse", "Test Officer", Role.admin)
    r = client.post("/auth/login", json={"username": "test-officer", "password": "correct horse"})
    assert r.status_code == 200, r.text
    return r.json()
