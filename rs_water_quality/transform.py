import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Station:
    cd_estacao: str
    uf: str
    entidade: str | None
    corpo_dagua: str | None
    ambiente: str | None
    lat: float | None
    lon: float | None


@dataclass(frozen=True)
class Measurement:
    cd_estacao: str
    indicator: str
    year: int
    stat: str
    value: float


_AMBIENTE_MAP = {"1": "lotico", "2": "lentico"}
_STAT_PREFIX = {"MED_": "mean", "MIN_": "min", "MAX_": "max"}
_META_COLS = {"CDESTACAO", "SGUF", "ENTIDADE", "CORPODAGUA", "AMBIENTE", "LATITUDE", "LONGITUDE"}
_SKIP_COLS = {"X", "Y", "OBJECTID", "ID", "CD"}
_EMPTY_SENTINELS = {"", "Informação não disponível"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k.upper(): v for k, v in row.items()} for row in csv.DictReader(f)]


def _parse_float(val: str) -> float | None:
    if val.strip() in _EMPTY_SENTINELS or val.strip() == "":
        return None
    try:
        return float(val)
    except ValueError:
        raise ValueError(f"Not a valid number: {val!r}")


def _normalize_ambiente(val: str) -> str | None:
    return _AMBIENTE_MAP.get(val.strip())


def parse(rows: list[dict[str, str]], indicator: str, uf: str = "RS") -> tuple[list[Station], list[Measurement]]:
    station_map: dict[str, Station] = {}
    measurements: list[Measurement] = []

    # Discover year columns from header
    year_cols: list[tuple[str, str, int]] = []  # (column_name, stat, year)
    for col in rows[0].keys() if rows else []:
        for prefix, stat in _STAT_PREFIX.items():
            if col.startswith(prefix):
                try:
                    year = int(col[len(prefix):])
                    year_cols.append((col, stat, year))
                except ValueError:
                    pass

    for row in rows:
        if row.get("SGUF", "").strip() != uf:
            continue

        cd = row["CDESTACAO"].strip()
        if cd not in station_map:
            ambiente_raw = row.get("AMBIENTE", "").strip()
            corpo_raw = row.get("CORPODAGUA", "").strip()
            station_map[cd] = Station(
                cd_estacao=cd,
                uf=uf,
                entidade=row.get("ENTIDADE", "").strip() or None,
                corpo_dagua=corpo_raw if corpo_raw and corpo_raw not in _EMPTY_SENTINELS else None,
                ambiente=_normalize_ambiente(ambiente_raw) if ambiente_raw else None,
                lat=_parse_float(row.get("LATITUDE", "")),
                lon=_parse_float(row.get("LONGITUDE", "")),
            )

        for col_name, stat, year in year_cols:
            val = row.get(col_name, "")
            parsed = _parse_float(val)
            if parsed is not None:
                measurements.append(Measurement(
                    cd_estacao=cd,
                    indicator=indicator,
                    year=year,
                    stat=stat,
                    value=parsed,
                ))

    return list(station_map.values()), measurements
