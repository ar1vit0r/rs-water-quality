import os
from pathlib import Path

import psycopg

_SCHEMA_SQL = Path(__file__).parent / "schema.sql"
_LIMITS_CSV = Path(__file__).parent / "limits.csv"


def connect(dsn: str | None = None) -> psycopg.Connection:
    if dsn is None:
        dsn = os.environ["DATABASE_URL"]
    return psycopg.connect(dsn)


def init_schema(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute(_SCHEMA_SQL.read_text())


def load_limits(conn: psycopg.Connection, csv_path: Path = _LIMITS_CSV) -> int:
    import csv

    with conn.transaction():
        conn.execute("DELETE FROM limits")
        rows = list(csv.DictReader(csv_path.read_text().splitlines()))
        for row in rows:
            ambiente = row["ambiente"] or None
            conn.execute(
                "INSERT INTO limits (indicator, ambiente, op, value, unit, stat_checked, source) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (row["indicator"], ambiente, row["op"], float(row["value"]), row["unit"], row["stat_checked"], row["source"]),
            )
    return len(rows)
