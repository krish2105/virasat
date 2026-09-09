import psycopg
import pytest


def test_postgis_and_pgvector_present(database_url: str) -> None:
    dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        conn = psycopg.connect(dsn, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"database not reachable: {exc}")
    with conn, conn.cursor() as cur:
        cur.execute("select extname from pg_extension where extname in ('postgis','vector')")
        found = {row[0] for row in cur.fetchall()}
    assert found == {"postgis", "vector"}
