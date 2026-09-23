from datetime import date
from pathlib import Path

import psycopg


def build_report(conn: psycopg.Connection, years: tuple[int, ...] = (2018, 2019, 2020)) -> str:
    lines: list[str] = []
    lines.append("# RS Water Quality Screening Report (2018-2020)")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Indicator | Year | Stations screened | Stations in breach | % in breach |")
    lines.append("|---|---|---|---|---|")

    for year in years:
        for indicator in ("od", "dbo", "turbidez", "fosforo_total"):
            screened = conn.execute(
                "SELECT count(DISTINCT m.cd_estacao) "
                "FROM measurement m "
                "JOIN limits l ON l.indicator = m.indicator AND l.stat_checked = m.stat "
                "AND (l.ambiente IS NULL OR l.ambiente = (SELECT ambiente FROM station WHERE cd_estacao = m.cd_estacao)) "
                "WHERE m.indicator = %s AND m.year = %s",
                (indicator, year),
            ).fetchone()[0]

            breached = conn.execute(
                "SELECT count(DISTINCT cd_estacao) FROM violation "
                "WHERE indicator = %s AND year = %s",
                (indicator, year),
            ).fetchone()[0]

            pct = (breached / screened * 100) if screened > 0 else 0.0
            lines.append(f"| {indicator} | {year} | {screened} | {breached} | {pct:.1f}% |")

    lines.append("")

    # Worst breaches ranked within each indicator: units differ, so there is no fair cross-indicator ranking
    lines.append(f"## Worst 5 Breaches per Indicator ({min(years)}-{max(years)})")
    lines.append("")
    lines.append("| Indicator | Station | Year | Value | Limit |")
    lines.append("|---|---|---|---|---|")

    rows = conn.execute(
        "SELECT indicator, cd_estacao, year, value, limit_value FROM ("
        "  SELECT *, row_number() OVER ("
        "    PARTITION BY indicator "
        "    ORDER BY CASE WHEN op = 'max' THEN value ELSE -value END DESC, year DESC, cd_estacao"
        "  ) AS rank "
        "  FROM violation WHERE year = ANY(%s)"
        ") ranked WHERE rank <= 5 ORDER BY indicator, rank",
        (list(years),),
    ).fetchall()
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")

    lines.append("")

    # E. coli and IQA report-only tables
    for indicator, label in (("ecoli", "E. coli"), ("iqa", "IQA")):
        lines.append(f"## {label} (report only)")
        lines.append("")
        lines.append("| Year | Median | p90 | n |")
        lines.append("|---|---|---|---|")

        for year in years:
            stats = conn.execute(
                "SELECT "
                "  percentile_cont(0.5) WITHIN GROUP (ORDER BY value) AS median, "
                "  percentile_cont(0.9) WITHIN GROUP (ORDER BY value) AS p90, "
                "  count(*) AS n "
                "FROM measurement "
                "WHERE indicator = %s AND year = %s AND stat = 'mean'",
                (indicator, year),
            ).fetchone()
            if stats and stats[2] > 0:
                lines.append(f"| {year} | {stats[0]:.1f} | {stats[1]:.1f} | {stats[2]} |")
            else:
                lines.append(f"| {year} | - | - | 0 |")

        lines.append("")

    # Limitations
    lines.append("## Limitations")
    lines.append("")
    lines.append("- Values are yearly aggregates (mean/min/max), not individual samples. This is a screening, not a legal compliance verdict.")
    lines.append("- The AMBIENTE mapping (1 = lotico, 2 = lentico) is inferred from water-body names, not from an official data dictionary.")
    lines.append("- Data ends in 2021 for most indicators, 2020 for E. coli. Some years have gaps.")
    lines.append("- E. coli and IQA are reported for reference only; no direct CONAMA 357 limit applies.")
    lines.append("")

    return "\n".join(lines)


def build_station_report(
    conn: psycopg.Connection,
    cd_estacao: str,
    years: tuple[int, ...] = (2018, 2019, 2020),
    report_date: date | None = None,
) -> str:
    if report_date is None:
        report_date = date.today()

    row = conn.execute(
        "SELECT cd_estacao, corpo_dagua, ambiente, uf, entidade, lat, lon "
        "FROM station WHERE cd_estacao = %s",
        (cd_estacao,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown station: {cd_estacao}")

    station_cd, corpo_dagua, ambiente, uf, entidade, lat, lon = row

    lines: list[str] = []
    lines.append(f"# Water Quality Report - Station {station_cd}")
    lines.append(str(report_date))
    lines.append("")

    # Station facts
    lines.append("## Station Information")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for label, val in [
        ("Corpo d'agua", corpo_dagua),
        ("Ambiente", ambiente),
        ("UF", uf),
        ("Entidade", entidade),
        ("Latitude", lat),
        ("Longitude", lon),
    ]:
        lines.append(f"| {label} | {val if val is not None else '-'} |")
    lines.append("")

    # CONAMA 357 screening
    conama_indicators = ("od", "dbo", "turbidez", "fosforo_total")

    violations = set()
    for r in conn.execute(
        "SELECT indicator, year FROM violation WHERE cd_estacao = %s AND year = ANY(%s)",
        (cd_estacao, list(years)),
    ).fetchall():
        violations.add((r[0], r[1]))

    lines.append("## CONAMA 357/2005 class 2 screening")
    lines.append("")
    lines.append("| Indicator | Year | Value | Unit | Limit | Verdict |")
    lines.append("|---|---|---|---|---|---|")

    for indicator in conama_indicators:
        for year in years:
            result = conn.execute(
                "SELECT DISTINCT ON (m.indicator, m.year) "
                "m.value, l.unit, l.value AS limit_value "
                "FROM measurement m "
                "JOIN station s USING (cd_estacao) "
                "JOIN limits l ON l.indicator = m.indicator "
                "AND l.stat_checked = m.stat "
                "AND (l.ambiente IS NULL OR l.ambiente = s.ambiente) "
                "WHERE m.cd_estacao = %s AND m.indicator = %s AND m.year = %s "
                "ORDER BY m.indicator, m.year, l.ambiente NULLS LAST",
                (cd_estacao, indicator, year),
            ).fetchone()

            if result is None:
                lines.append(f"| {indicator} | {year} | - | - | - | no data |")
            else:
                value, unit, limit_value = result
                verdict = "Breach" if (indicator, year) in violations else "OK"
                lines.append(
                    f"| {indicator} | {year} | {value} | {unit} | {limit_value} | {verdict} |"
                )

    lines.append("")

    # Reference only (ecoli, iqa)
    lines.append("## Reference only (no CONAMA 357 limit)")
    lines.append("")
    lines.append("| Indicator | Year | Value | Unit |")
    lines.append("|---|---|---|---|")

    for indicator in ("ecoli", "iqa"):
        for year in years:
            result = conn.execute(
                "SELECT value FROM measurement "
                "WHERE cd_estacao = %s AND indicator = %s AND year = %s AND stat = 'mean'",
                (cd_estacao, indicator, year),
            ).fetchone()
            if result is None:
                lines.append(f"| {indicator} | {year} | - | - |")
            else:
                unit = "NMP/100 mL" if indicator == "ecoli" else "index"
                lines.append(f"| {indicator} | {year} | {result[0]} | {unit} |")

    lines.append("")

    # Notes
    lines.append("## Notes")
    lines.append("")
    lines.append("- Values are yearly aggregates (mean/min/max), not individual samples. This is a screening, not a legal compliance verdict.")
    lines.append("- The AMBIENTE mapping (1 = lotico, 2 = lentico) is inferred from water-body names, not from an official data dictionary.")
    lines.append("- Data ends in 2021 for most indicators, 2020 for E. coli. Some years have gaps.")
    lines.append("- E. coli and IQA are reported for reference only; no direct CONAMA 357 limit applies.")
    lines.append("- This is a single-station extract of the same screening, not an independent lab analysis.")
    lines.append("")

    return "\n".join(lines)
