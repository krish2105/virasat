import os

import pytest

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://virasat:virasat@localhost:5434/virasat"
)


@pytest.fixture(scope="session")
def database_url() -> str:
    return DATABASE_URL
