import pytest

from rs_water_quality.db import connect, init_schema, load_limits


@pytest.fixture
def conn():
    import os
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


def _insert_station(conn, cd, ambiente=None):
    conn.execute(
        "INSERT INTO station (cd_estacao, uf, entidade, corpo_dagua, ambiente, lat, lon) "
        "VALUES (%s, 'RS', 'FEPAM', NULL, %s, 0, 0)",
        (cd, ambiente),
    )


def _insert_measurement(conn, cd, indicator, year, stat, value):
    conn.execute(
        "INSERT INTO measurement (cd_estacao, indicator, year, stat, value) "
        "VALUES (%s, %s, %s, %s, %s)",
        (cd, indicator, year, stat, value),
    )


def _violations(conn):
    cur = conn.execute("SELECT cd_estacao, indicator, year FROM violation ORDER BY 1")
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


@pytest.mark.db
def test_od_min_49_is_breach(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "od", 2020, "min", 4.9)
    assert len(_violations(conn)) == 1


@pytest.mark.db
def test_od_min_50_not_breach(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "od", 2020, "min", 5.0)
    assert len(_violations(conn)) == 0


@pytest.mark.db
def test_dbo_max_51_is_breach(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "dbo", 2020, "max", 5.1)
    assert len(_violations(conn)) == 1


@pytest.mark.db
def test_dbo_max_50_not_breach(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "dbo", 2020, "max", 5.0)
    assert len(_violations(conn)) == 0


@pytest.mark.db
def test_od_mean_below_5_not_breach(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "od", 2020, "mean", 4.9)
    assert len(_violations(conn)) == 0


@pytest.mark.db
def test_fosforo_lentico_breach(conn):
    _insert_station(conn, "S1", ambiente="lentico")
    _insert_measurement(conn, "S1", "fosforo_total", 2020, "max", 0.05)
    assert len(_violations(conn)) == 1


@pytest.mark.db
def test_fosforo_lotico_not_breach(conn):
    _insert_station(conn, "S1", ambiente="lotico")
    _insert_measurement(conn, "S1", "fosforo_total", 2020, "max", 0.05)
    assert len(_violations(conn)) == 0


@pytest.mark.db
def test_fosforo_null_ambiente_no_breach(conn):
    _insert_station(conn, "S1", ambiente=None)
    _insert_measurement(conn, "S1", "fosforo_total", 2020, "max", 0.05)
    assert len(_violations(conn)) == 0


@pytest.mark.db
def test_ecoli_never_in_violation(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "ecoli", 2020, "mean", 5000)
    assert len(_violations(conn)) == 0


@pytest.mark.db
def test_iqa_never_in_violation(conn):
    _insert_station(conn, "S1")
    _insert_measurement(conn, "S1", "iqa", 2020, "mean", 10)
    assert len(_violations(conn)) == 0
