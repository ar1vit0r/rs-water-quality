import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

from rs_water_quality.datasets import DATASETS
from rs_water_quality.db import connect, init_schema, load_limits
from rs_water_quality.download import download
from rs_water_quality.load import load as do_load
from rs_water_quality.report import build_report, build_station_report


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


def cmd_report(args: argparse.Namespace) -> None:
    conn = connect()
    md = build_report(conn)
    conn.close()
    out = Path("reports/rs_2018_2020.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"Report written to {out}")


def cmd_report_station(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"[A-Za-z0-9]+", args.cd_estacao):
        raise ValueError(f"Invalid station code: {args.cd_estacao}")
    conn = connect()
    md = build_station_report(conn, args.cd_estacao)
    conn.close()
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"laudo_{args.cd_estacao}.md"
    pdf_path = out_dir / f"laudo_{args.cd_estacao}.pdf"
    md_path.write_text(md)
    try:
        subprocess.run(["pandoc", str(md_path), "-o", str(pdf_path)], check=True)
    except FileNotFoundError:
        print("pandoc not found; Markdown written but PDF not generated.")
        sys.exit(1)
    print(f"Written: {md_path} and {pdf_path}")


def cmd_all(args: argparse.Namespace) -> None:
    cmd_init(args)
    cmd_fetch(args)
    cmd_load(args)
    cmd_report(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="rs_water_quality")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize schema and seed limits")
    sub.add_parser("fetch", help="Download all 6 ANA indicator CSVs")
    sub.add_parser("load", help="Load all 6 from data/raw/")
    sub.add_parser("report", help="Write reports/rs_2018_2020.md")
    report_station_p = sub.add_parser("report-station", help="Write a per-station laudo (Markdown + PDF)")
    report_station_p.add_argument("cd_estacao", help="ANA station code")
    sub.add_parser("all", help="init, fetch, load, report")
    args = parser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "load":
        cmd_load(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "report-station":
        cmd_report_station(args)
    elif args.command == "all":
        cmd_all(args)
    else:
        parser.print_help()
        sys.exit(1)
