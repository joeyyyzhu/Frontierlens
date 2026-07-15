from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_sources
from .database import Database
from .discovery import Monitor
from .parser import parse_pdf
from .server import serve


def initialize() -> Database:
    database = Database()
    database.initialize()
    database.sync_sources(load_sources())
    return database


def main() -> None:
    parser = argparse.ArgumentParser(description="FrontierLens official source monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize SQLite and sync source registry")
    scan_parser = subparsers.add_parser("scan", help="Scan official sources now")
    scan_parser.add_argument("--no-download", action="store_true", help="Discover links without saving files")
    scan_parser.add_argument("--max-downloads", type=int, default=10, help="Maximum files saved in this run")
    scan_parser.add_argument("--source", help="Only scan one configured source id")
    parse_parser = subparsers.add_parser("parse", help="Parse one local PDF")
    parse_parser.add_argument("pdf", type=Path)
    parse_parser.add_argument("--output", type=Path)
    serve_parser = subparsers.add_parser("serve", help="Serve UI/API and run scheduled scans")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=4173)
    serve_parser.add_argument("--interval", type=int, default=3600, help="Scan interval in seconds; 0 disables")

    args = parser.parse_args()
    if args.command == "init":
        database = initialize()
        print(json.dumps({"status": "initialized", "database": str(database.path)}, ensure_ascii=False))
    elif args.command == "scan":
        database = initialize()
        sources = load_sources()
        if args.source:
            sources = [source for source in sources if source.id == args.source]
            if not sources:
                parser.error(f"unknown source id: {args.source}")
        result = Monitor(database).scan(sources, download=not args.no_download, max_downloads=args.max_downloads)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "parse":
        payload = parse_pdf(args.pdf)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(args.output)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.command == "serve":
        initialize()
        serve(host=args.host, port=args.port, interval_seconds=args.interval)
