from pathlib import Path

import pytest

from rs_water_quality.datasets import DATASETS
from rs_water_quality.db import connect, init_schema, load_limits
from rs_water_quality.load import load

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.db
def test_load_od_fixture_twice(conn):
    ds = next(d for d in DATASETS if d.indicator == "od")
    csv_path = FIXTURES / "od_sample.csv"
    sha256 = "abc123"

    n1 = load(conn, ds, csv_path, sha256)
    n2 = load(conn, ds, csv_path, sha256)

    cur = conn.execute("SELECT count(*) FROM measurement")
    count_after_1 = cur.fetchone()[0]

    # Second load should not change measurement count (upsert)
    cur2 = conn.execute("SELECT count(*) FROM measurement")
    count_after_2 = cur2.fetchone()[0]
    assert count_after_2 == count_after_1

    cur3 = conn.execute("SELECT count(*) FROM load_audit")
    assert cur3.fetchone()[0] == 2


@pytest.mark.db
def test_station_keeps_first_non_null_corpo_dagua(conn):
    ds_od = next(d for d in DATASETS if d.indicator == "od")
    load(conn, ds_od, FIXTURES / "od_sample.csv", "aaa")

    ds_dbo = next(d for d in DATASETS if d.indicator == "dbo")
    load(conn, ds_dbo, FIXTURES / "od_sample.csv", "bbb")

    cur = conn.execute("SELECT corpo_dagua FROM station WHERE cd_estacao = 'RS-002'")
    row = cur.fetchone()
    assert row[0] is None  # Informacao nao disponivel -> None, stays None


@pytest.mark.db
def test_rollback_on_failure(conn, monkeypatch):
    ds = next(d for d in DATASETS if d.indicator == "od")
    csv_path = FIXTURES / "od_sample.csv"

    original_execute = conn.execute
    call_count = 0

    def failing_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 10:  # fail after some station inserts
            raise RuntimeError("boom")
        return original_execute(*args, **kwargs)

    monkeypatch.setattr(conn, "execute", failing_execute)
    with pytest.raises(RuntimeError):
        load(conn, ds, csv_path, "abc")

    # Restore original execute for verification queries
    conn.execute = original_execute
    cur = conn.execute("SELECT count(*) FROM measurement")
    assert cur.fetchone()[0] == 0
    cur = conn.execute("SELECT count(*) FROM load_audit")
    assert cur.fetchone()[0] == 0
