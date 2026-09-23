import argparse
import sys

from rs_water_quality.datasets import DATASETS
from rs_water_quality.db import connect, init_schema, load_limits


def cmd_init(args: argparse.Namespace) -> None:
    conn = connect()
    init_schema(conn)
    n = load_limits(conn)
    print(f"Schema initialized, {n} limits loaded.")
    conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="rs_water_quality")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize schema and seed limits")
    # fetch, load, report added in later steps
    args = parser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    else:
        parser.print_help()
        sys.exit(1)
