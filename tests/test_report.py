import pytest

from rs_water_quality.report import build_report


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
