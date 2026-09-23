from datetime import date

import pytest

from rs_water_quality.report import build_report, build_station_report


def _add(conn, cd: str, ambiente: str, indicator: str, year: int, stat: str, value: float) -> None:
    conn.execute(
        "INSERT INTO station (cd_estacao, uf, ambiente) VALUES (%s, 'RS', %s) ON CONFLICT DO NOTHING",
        (cd, ambiente),
    )
    conn.execute(
        "INSERT INTO measurement (cd_estacao, indicator, year, stat, value) VALUES (%s, %s, %s, %s, %s)",
        (cd, indicator, year, stat, value),
    )


def _worst(report: str) -> list[list[str]]:
    section = report.split("## Worst 5")[1].split("\n## ")[0]
    rows = [line for line in section.splitlines() if line.startswith("| ") and not line.startswith("| Indicator")]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]


@pytest.mark.db
def test_worst_excludes_years_outside_window(conn):
    _add(conn, "OLD", "lotico", "turbidez", 2006, "max", 700.0)
    _add(conn, "NEW", "lotico", "turbidez", 2020, "max", 150.0)
    assert [r[1] for r in _worst(build_report(conn))] == ["NEW"]


@pytest.mark.db
def test_worst_ranks_within_indicator_in_the_breach_direction(conn):
    # od is a floor (lower is worse), turbidez a ceiling (higher is worse)
    _add(conn, "OD_BAD", "lotico", "od", 2020, "min", 1.0)
    _add(conn, "OD_MID", "lotico", "od", 2020, "min", 4.0)
    _add(conn, "TB_BAD", "lotico", "turbidez", 2019, "max", 400.0)
    _add(conn, "TB_MID", "lotico", "turbidez", 2019, "max", 120.0)
    rows = _worst(build_report(conn))
    assert [(r[0], r[1]) for r in rows] == [
        ("od", "OD_BAD"), ("od", "OD_MID"), ("turbidez", "TB_BAD"), ("turbidez", "TB_MID"),
    ]


@pytest.mark.db
def test_worst_keeps_at_most_five_per_indicator(conn):
    for i in range(7):
        _add(conn, f"S{i}", "lotico", "dbo", 2020, "max", 6.0 + i)
    rows = _worst(build_report(conn))
    assert len(rows) == 5
    assert rows[0][1] == "S6"


@pytest.mark.db
def test_station_report_breach_and_ok(conn):
    _add(conn, "S_BREACH", "lotico", "od", 2020, "min", 4.9)
    _add(conn, "S_OK", "lotico", "od", 2020, "min", 5.0)
    md_breach = build_station_report(conn, "S_BREACH", years=(2020,))
    md_ok = build_station_report(conn, "S_OK", years=(2020,))
    assert "| od | 2020 | 4.9 | mg/L | 5.0 | Breach |" in md_breach
    assert "| od | 2020 | 5.0 | mg/L | 5.0 | OK |" in md_ok


@pytest.mark.db
def test_station_report_no_data(conn):
    conn.execute(
        "INSERT INTO station (cd_estacao, uf, ambiente) VALUES ('S_NODATA', 'RS', 'lotico')",
    )
    md = build_station_report(conn, "S_NODATA", years=(2020,))
    assert "| od | 2020 | - | - | - | no data |" in md


@pytest.mark.db
def test_station_report_ecoli_iqa_reference_only(conn):
    _add(conn, "S_REF", "lotico", "ecoli", 2020, "mean", 9999.0)
    _add(conn, "S_REF", "lotico", "iqa", 2020, "mean", 1.0)
    md = build_station_report(conn, "S_REF", years=(2020,))
    assert "## Reference only (no CONAMA 357 limit)" in md
    assert "| ecoli | 2020 | 9999.0 | NMP/100 mL |" in md
    assert "| iqa | 2020 | 1.0 | index |" in md
    # ecoli/iqa never get a Verdict line
    assert "Verdict" not in md.split("## Reference only")[1]


@pytest.mark.db
def test_station_report_unknown_cd_raises(conn):
    with pytest.raises(ValueError, match="unknown station"):
        build_station_report(conn, "NONEXISTENT")


@pytest.mark.db
def test_station_report_fixed_date(conn):
    conn.execute(
        "INSERT INTO station (cd_estacao, uf, ambiente) VALUES ('S_DATE', 'RS', 'lotico')",
    )
    md = build_station_report(conn, "S_DATE", years=(2020,), report_date=date(2026, 9, 23))
    assert "2026-09-23" in md
