import os
from pathlib import Path

import pytest

from rs_water_quality.transform import Measurement, Station, parse, read_rows

FIXTURES = Path(__file__).parent / "fixtures"


def test_non_rs_excluded():
    rows = read_rows(FIXTURES / "od_sample.csv")
    stations, measurements = parse(rows, "od")
    station_ids = {s.cd_estacao for s in stations}
    assert "SP-001" not in station_ids
    assert len(stations) == 3


def test_empty_cells_produce_no_measurement():
    rows = read_rows(FIXTURES / "od_sample.csv")
    stations, measurements = parse(rows, "od")
    rs002_mean = [m for m in measurements if m.cd_estacao == "RS-002" and m.year == 2020 and m.stat == "mean"]
    assert len(rs002_mean) == 0


def test_informacao_nao_disponivel_becomes_none():
    rows = read_rows(FIXTURES / "od_sample.csv")
    stations, _ = parse(rows, "od")
    rs002 = next(s for s in stations if s.cd_estacao == "RS-002")
    assert rs002.corpo_dagua is None


def test_ambiente_mapping():
    rows = read_rows(FIXTURES / "od_sample.csv")
    stations, _ = parse(rows, "od")
    by_id = {s.cd_estacao: s for s in stations}
    assert by_id["RS-001"].ambiente == "lotico"
    assert by_id["RS-002"].ambiente == "lentico"
    assert by_id["RS-003"].ambiente is None


def test_lowercase_headers_parse_same():
    rows = read_rows(FIXTURES / "ecoli_sample.csv")
    stations, measurements = parse(rows, "ecoli")
    station_ids = {s.cd_estacao for s in stations}
    assert "RS-100" in station_ids
    assert "SP-100" not in station_ids
    rs100 = [m for m in measurements if m.cd_estacao == "RS-100"]
    years = {m.year for m in rs100}
    assert 2001 in years
    assert 2003 in years


def test_missing_year_from_header():
    rows = read_rows(FIXTURES / "ecoli_sample.csv")
    _, measurements = parse(rows, "ecoli")
    years = {m.year for m in measurements if m.cd_estacao == "RS-100"}
    assert 2002 not in years
    assert 2001 in years
    assert 2003 in years


def test_malformed_number_raises():
    rows = read_rows(FIXTURES / "od_sample.csv")
    # Inject a bad value
    rows[0]["MED_2020"] = "not_a_number"
    with pytest.raises(ValueError, match="not_a_number"):
        parse(rows, "od")


@pytest.mark.skipif(
    not os.path.exists("data/raw/od.csv"),
    reason="real data not downloaded",
)
def test_real_data_od_rs_2020():
    rows = read_rows(Path("data/raw/od.csv"))
    stations, measurements = parse(rows, "od")
    assert len(stations) == 233
    mean_2020 = [m for m in measurements if m.year == 2020 and m.stat == "mean"]
    assert len(mean_2020) == 185


@pytest.mark.skipif(
    not os.path.exists("data/raw/dbo.csv"),
    reason="real data not downloaded",
)
def test_real_data_dbo_rs_2020():
    rows = read_rows(Path("data/raw/dbo.csv"))
    _, measurements = parse(rows, "dbo")
    mean_2020 = [m for m in measurements if m.year == 2020 and m.stat == "mean"]
    assert len(mean_2020) == 176


@pytest.mark.skipif(
    not os.path.exists("data/raw/turbidez.csv"),
    reason="real data not downloaded",
)
def test_real_data_turbidez_rs_2020():
    rows = read_rows(Path("data/raw/turbidez.csv"))
    _, measurements = parse(rows, "turbidez")
    mean_2020 = [m for m in measurements if m.year == 2020 and m.stat == "mean"]
    assert len(mean_2020) == 185
