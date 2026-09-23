import os

import pytest

from rs_water_quality.db import connect, init_schema, load_limits


@pytest.fixture
def conn():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not set")
    if "rsw_test" not in dsn:
        raise RuntimeError(f"Refusing to run on non-test database: {dsn}")
    c = connect(dsn)
    c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    init_schema(c)
    load_limits(c)
    yield c
    c.close()
