import argparse
import sys
from pathlib import Path

from rs_water_quality.datasets import DATASETS
from rs_water_quality.db import connect, init_schema, load_limits
from rs_water_quality.download import download


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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="rs_water_quality")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize schema and seed limits")
    sub.add_parser("fetch", help="Download all 6 ANA indicator CSVs")
    args = parser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    else:
        parser.print_help()
        sys.exit(1)
