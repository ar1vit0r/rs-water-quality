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

    # Top 15 breaches
    lines.append("## Top 15 Breaches by Distance from Limit")
    lines.append("")
    lines.append("| Station | Indicator | Year | Value | Limit | Distance |")
    lines.append("|---|---|---|---|---|---|")

    rows = conn.execute(
        "SELECT cd_estacao, indicator, year, value, limit_value, "
        "  ABS(value - limit_value) AS distance "
        "FROM violation "
        "ORDER BY distance DESC LIMIT 15"
    ).fetchall()
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]:.3f} |")

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
