import csv
from pathlib import Path

import psycopg

from rs_water_quality.datasets import Dataset
from rs_water_quality.transform import Measurement, Station, parse, read_rows


def load(conn: psycopg.Connection, dataset: Dataset, csv_path: Path, sha256: str) -> int:
    rows = read_rows(csv_path)
    stations, measurements = parse(rows, dataset.indicator)

    with conn.transaction():
        for s in stations:
            conn.execute(
                "INSERT INTO station (cd_estacao, uf, entidade, corpo_dagua, ambiente, lat, lon) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (cd_estacao) DO UPDATE SET "
                "  entidade = COALESCE(station.entidade, EXCLUDED.entidade), "
                "  corpo_dagua = COALESCE(station.corpo_dagua, EXCLUDED.corpo_dagua), "
                "  ambiente = COALESCE(station.ambiente, EXCLUDED.ambiente), "
                "  lat = COALESCE(station.lat, EXCLUDED.lat), "
                "  lon = COALESCE(station.lon, EXCLUDED.lon)",
                (s.cd_estacao, s.uf, s.entidade, s.corpo_dagua, s.ambiente, s.lat, s.lon),
            )

        rows_loaded = 0
        for m in measurements:
            conn.execute(
                "INSERT INTO measurement (cd_estacao, indicator, year, stat, value) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (cd_estacao, indicator, year, stat) DO UPDATE SET value = EXCLUDED.value",
                (m.cd_estacao, m.indicator, m.year, m.stat, m.value),
            )
            rows_loaded += 1

        conn.execute(
            "INSERT INTO load_audit (dataset_id, indicator, url, sha256, rows_read, rows_loaded) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (dataset.dataset_id, dataset.indicator, dataset.url, sha256, len(rows), rows_loaded),
        )

    return rows_loaded
