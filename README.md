# RS Water Quality

Public screening of Rio Grande do Sul water-quality indicators against CONAMA 357/2005 class-2 fresh-water limits.

![CI](https://github.com/ar1vit0r/rs-water-quality/actions/workflows/ci.yml/badge.svg)

## Results (2020)

| Indicator | Stations screened | Stations in breach | % in breach |
|---|---|---|---|
| OD (dissolved oxygen) | 185 | 72 | 38.9% |
| DBO (BOD) | 176 | 10 | 5.7% |
| Turbidez | 185 | 21 | 11.4% |
| Fosforo total | 169 | 152 | 89.9% |

Phosphorus has the most breaches, and mostly in rivers: 137 of the 154 lotic stations screened in 2020 exceed the 0.1 mg/L river limit. All 15 lentic stations (lakes, reservoirs) exceed the stricter 0.030 mg/L limit.

## How it works

1. Download 6 public CSVs from the ANA open data portal (RNQA indicators).
2. Filter to RS stations, unpivot year columns into (station, indicator, year, stat, value) rows.
3. Load into PostgreSQL with upserts and a per-load audit trail.
4. Screen against CONAMA 357 limits via a SQL view; generate a Markdown report.

Schema: `station`, `measurement`, `limits`, `load_audit`, view `violation`.

## Run it

```bash
docker compose up -d --wait
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
DATABASE_URL=postgresql://rsw:rsw@localhost:5433/rsw .venv/bin/python -m rs_water_quality init
DATABASE_URL=postgresql://rsw:rsw@localhost:5433/rsw .venv/bin/python -m rs_water_quality fetch
DATABASE_URL=postgresql://rsw:rsw@localhost:5433/rsw .venv/bin/python -m rs_water_quality load
DATABASE_URL=postgresql://rsw:rsw@localhost:5433/rsw .venv/bin/python -m rs_water_quality report
DATABASE_URL=postgresql://rsw:rsw@localhost:5433/rsw .venv/bin/python -m rs_water_quality report-station <cd_estacao>  # requires pandoc for PDF
# or: python -m rs_water_quality all
```

`report-station` generates `reports/laudo_<cd_estacao>.md` and `.pdf`. The PDF step requires `pandoc` (an OS package, not a Python dependency).

## Limits used (CONAMA 357/2005, class 2 fresh water)

| Indicator | Limit | Stat compared |
|---|---|---|
| OD | >= 5 mg/L | yearly min |
| DBO | <= 5 mg/L | yearly max |
| Turbidez | <= 100 NTU | yearly max |
| Fosforo total (lotico) | <= 0.1 mg/L | yearly max |
| Fosforo total (lentico) | <= 0.03 mg/L | yearly max |

E. coli and IQA are reported for reference only. CONAMA 357 sets thermotolerant coliforms <= 1000/100 mL and allows E. coli as a substitute at the agency's discretion, but there is no direct E. coli limit in the regulation. IQA has no CONAMA limit.

## Limitations

- Values are yearly aggregates (mean/min/max), not individual samples. This is a screening, not a legal compliance verdict.
- The AMBIENTE mapping (1 = lotico, 2 = lentico) is inferred from water-body names, not from an official data dictionary.
- Data ends in 2021 for most indicators, 2020 for E. coli. Some years have gaps.
- Every station is screened against class 2 fresh water. The legal class (enquadramento) is set per river stretch (art. 2 XX), and salinity is not checked, so brackish stations (art. 2 II) may be held to fresh-water limits.
- CONAMA 357 limits apply at the reference flow (art. 10); the data do not identify the flow at sampling. Parameters such as pH, chlorophyll a and ammonia are not covered because the ANA datasets used here do not include them.
- No intermediate-environment phosphorus limit (0.050 mg/L) is used because no RS station is classified as intermediate.

## Data sources

- ANA open data portal: [Indicadores de Qualidade da Agua (RNQA)](https://dadosabertos.ana.gov.br/)
  - [OD](https://dadosabertos.ana.gov.br/datasets/5d7db6cd8caf4116b69fa8185fe74b96_2.csv)
  - [DBO](https://dadosabertos.ana.gov.br/datasets/d82c795398754609b0a8b4a550ef6c57_14.csv)
  - [Turbidez](https://dadosabertos.ana.gov.br/datasets/97e46167e18c4fb0bda9dd5f8ed7783b_8.csv)
  - [Fosforo total](https://dadosabertos.ana.gov.br/datasets/0419dd6718cb4be0a331c7589c57ea2b_5.csv)
  - [E. coli](https://dadosabertos.ana.gov.br/datasets/6a2d579dc3bd40838e7dbb9615324b93_17.csv)
  - [IQA](https://dadosabertos.ana.gov.br/datasets/7a278de90bd14330ab014c9b5db350e0_17.csv)
- FEPAM operates all RS stations.

## Stack

Python 3.12, PostgreSQL 16 (Docker Compose), psycopg 3, pytest. Stdlib csv for parsing, no pandas.
