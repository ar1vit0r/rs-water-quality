import argparse
import hashlib
import sys
from pathlib import Path

from rs_water_quality.datasets import DATASETS
from rs_water_quality.db import connect, init_schema, load_limits
from rs_water_quality.download import download
from rs_water_quality.load import load as do_load


def cmd_init(args: argparse.Namespace) -> None:
    conn = connect()
    init_schema(conn)
    n = load_limits(conn)
    print(f"Schema initialized, {n} limits loaded.")
    conn.close()


def cmd_fetch(args: argparse.Namespace) -> None:
    dest_dir = Path("data/raw")
    for ds in DATASETS:
        path, sha = download(ds, dest_dir)
        print(f"{ds.indicator}: {path} ({path.stat().st_size:,} bytes) sha256={sha[:16]}...")
    print(f"6 files downloaded to {dest_dir}/")


def cmd_load(args: argparse.Namespace) -> None:
    conn = connect()
    init_schema(conn)
    load_limits(conn)
    raw_dir = Path("data/raw")
    for ds in DATASETS:
        csv_path = raw_dir / f"{ds.indicator}.csv"
        sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        n = do_load(conn, ds, csv_path, sha256)
        print(f"{ds.indicator}: {n} measurements loaded")
    conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="rs_water_quality")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize schema and seed limits")
    sub.add_parser("fetch", help="Download all 6 ANA indicator CSVs")
    sub.add_parser("load", help="Load all 6 from data/raw/")
    args = parser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "load":
        cmd_load(args)
    else:
        parser.print_help()
        sys.exit(1)
