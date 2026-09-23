from datetime import date
from pathlib import Path

import psycopg

INDICATOR_GLOSSARY: dict[str, tuple[str, str]] = {
    "od": (
        "Dissolved Oxygen",
        "Oxygen available in the water for aquatic life. Low values indicate pollution or organic overload.",
    ),
    "dbo": (
        "Biochemical Oxygen Demand (BOD)",
        "Oxygen consumed by microorganisms breaking down organic matter. High values indicate organic pollution such as sewage or effluents.",
    ),
    "turbidez": (
        "Turbidity",
        "Water cloudiness caused by suspended particles. High values reduce light penetration and can indicate erosion or runoff.",
    ),
    "fosforo_total": (
        "Total Phosphorus",
        "Nutrient commonly linked to agricultural or domestic runoff. Excess phosphorus causes eutrophication (excessive algae growth).",
    ),
    "ecoli": (
        "E. coli",
        "Fecal-indicator bacteria. High counts signal sewage contamination and a health risk for contact or consumption.",
    ),
    "iqa": (
        "Water Quality Index (IQA)",
        "A composite score from 0 to 100 combining several parameters into a single number; higher is better.",
    ),
}


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

    # Acronyms
    lines.append("## Acronyms")
    lines.append("")
    lines.append("- **CONAMA**: National Environment Council (Conselho Nacional do Meio Ambiente), the Brazilian body that sets the water-quality limits used in this screening.")
    lines.append("- **ANA**: National Water and Sanitation Agency (Agencia Nacional de Aguas e Saneamento Basico), Brazil's federal water regulator and the source of the raw data.")
    lines.append("- **RNQA**: National Water Quality Network (Rede Nacional de Qualidade da Agua), the monitoring program this data is published under.")
    lines.append("- **FEPAM**: Rio Grande do Sul State Environmental Protection Foundation (Fundacao Estadual de Protecao Ambiental), the agency that operates this station.")
    lines.append("- **NTU**: Nephelometric Turbidity Unit, the standard unit for turbidity.")
    lines.append("- **NMP/100 mL**: Most Probable Number per 100 mL, the standard unit for bacterial counts such as E. coli.")
    lines.append("- **Ambiente (lotico/lentico)**: lotico is flowing water (rivers, streams). Lentico is standing water (lakes, reservoirs). CONAMA 357 sets a stricter phosphorus limit for lentico environments, since still water eutrophies more easily.")
    lines.append("")

    # CONAMA 357 screening
    conama_indicators = ("od", "dbo", "turbidez", "fosforo_total")

    # Glossary
    lines.append("## Indicators")
    lines.append("")
    for code in (*conama_indicators, "ecoli", "iqa"):
        full_name, description = INDICATOR_GLOSSARY[code]
        lines.append(f"- **{code}** ({full_name}): {description}")
    lines.append("")

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

    # Data source
    sources = conn.execute(
        "SELECT DISTINCT ON (l.indicator) l.indicator, l.source "
        "FROM limits l "
        "JOIN station s ON s.cd_estacao = %s "
        "WHERE l.indicator = ANY(%s) "
        "AND (l.ambiente IS NULL OR l.ambiente = s.ambiente) "
        "ORDER BY l.indicator, l.ambiente NULLS LAST",
        (cd_estacao, list(conama_indicators)),
    ).fetchall()

    lines.append("## Data Source")
    lines.append("")
    lines.append(
        f"Raw measurements: ANA open data portal, Indicadores de Qualidade da Agua (RNQA). "
        f"Station operated by {entidade if entidade is not None else 'an unspecified agency'}."
    )
    lines.append("")
    lines.append("Legal limits:")
    for _, source in sources:
        lines.append(f"- {source}")
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

    # Tooling
    lines.append("## About This Report")
    lines.append("")
    lines.append(
        "Generated by rs_water_quality, an open-source Python and PostgreSQL pipeline that "
        "loads public ANA/RNQA water-quality data, screens it against CONAMA 357 limits, and "
        "produces this report automatically. Source code and methodology: "
        "https://github.com/ar1vit0r/rs-water-quality"
    )
    lines.append("")

    return "\n".join(lines)
