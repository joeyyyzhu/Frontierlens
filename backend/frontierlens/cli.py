from __future__ import annotations

import argparse
import json
import signal
import threading
from pathlib import Path

from .config import load_sources
from .catalog import CATALOG_VERSION
from .database import Database
from .discovery import Monitor
from .parser import parse_pdf
from .server import serve
from .audit import audit_catalog
from .briefs import BriefBuilder


def initialize() -> Database:
    database = Database()
    database.initialize()
    database.sync_sources(load_sources())
    database.rebuild_release_index(CATALOG_VERSION)
    BriefBuilder(database).build_all()
    return database


def main() -> None:
    parser = argparse.ArgumentParser(description="FrontierLens official source monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize SQLite and sync source registry")
    subparsers.add_parser("audit", help="Audit provenance, dates and release visibility")
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
    serve_parser.add_argument("--interval", type=int, default=300, help="Scan interval in seconds; 0 disables")
    worker_parser = subparsers.add_parser("worker", help="Continuously scan official sources in a separate process")
    worker_parser.add_argument("--interval", type=int, default=300, help="Seconds between scans")
    worker_parser.add_argument("--max-downloads", type=int, default=10, help="Maximum files saved in each scan")

    args = parser.parse_args()
    if args.command == "init":
        database = initialize()
        print(json.dumps({"status": "initialized", "database": str(database.path)}, ensure_ascii=False))
    elif args.command == "audit":
        database = initialize()
        result = audit_catalog(database)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] != "pass":
            raise SystemExit(1)
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
    elif args.command == "worker":
        if args.interval < 60:
            parser.error("worker interval must be at least 60 seconds")
        database = initialize()
        sources = load_sources()
        monitor = Monitor(database)
        stop_event = threading.Event()

        def stop_worker(*_args) -> None:
            stop_event.set()

        signal.signal(signal.SIGINT, stop_worker)
        signal.signal(signal.SIGTERM, stop_worker)
        while not stop_event.is_set():
            result = monitor.scan(sources, download=True, max_downloads=args.max_downloads)
            print(json.dumps({"event": "scan_complete", **result}, ensure_ascii=False), flush=True)
            stop_event.wait(args.interval)
