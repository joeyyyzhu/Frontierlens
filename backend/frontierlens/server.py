from __future__ import annotations

import json
import mimetypes
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import ROOT, load_sources
from .database import Database
from .discovery import Monitor


class FrontierLensHandler(BaseHTTPRequestHandler):
    database: Database
    monitor: Monitor
    sources = []
    scan_lock = threading.Lock()

    def log_message(self, format: str, *args) -> None:
        print(f"[frontierlens] {self.address_string()} - {format % args}")

    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/health":
            return self._json({"status": "ok", "service": "frontierlens", "version": "0.1.0"})
        if path == "/api/sources":
            return self._json(self.database.rows("SELECT * FROM sources ORDER BY priority, provider"))
        if path == "/api/reports":
            return self._json(self.database.rows("SELECT * FROM reports ORDER BY discovered_at DESC LIMIT 200"))
        if path.startswith("/api/reports/"):
            try:
                report_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self._json({"error": "invalid report id"}, 400)
            report = self.database.row("SELECT * FROM reports WHERE id=?", (report_id,))
            if not report:
                return self._json({"error": "report not found"}, 404)
            if report.get("parsed_path") and Path(report["parsed_path"]).exists():
                report["parsed"] = json.loads(Path(report["parsed_path"]).read_text(encoding="utf-8"))
            return self._json(report)
        if path == "/api/runs":
            return self._json(self.database.rows("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 50"))
        if path == "/api/monitor/summary":
            sources = self.database.rows("SELECT id, provider, name, last_checked_at, last_status, last_error FROM sources WHERE enabled=1 ORDER BY priority")
            latest_run = self.database.row("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1")
            counts = self.database.row(
                """SELECT COUNT(*) AS reports,
                SUM(CASE WHEN parse_status='parsed' THEN 1 ELSE 0 END) AS parsed,
                COUNT(DISTINCT provider) AS providers FROM reports"""
            ) or {"reports": 0, "parsed": 0, "providers": 0}
            recent = self.database.rows(
                "SELECT id, provider, title, report_type, discovered_at, page_count, parse_status FROM reports ORDER BY discovered_at DESC LIMIT 10"
            )
            return self._json({"sources": sources, "latest_run": latest_run, "counts": counts, "recent_reports": recent})

        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (ROOT / relative).resolve()
        if ROOT.resolve() not in candidate.parents and candidate != ROOT.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        self._serve_file(candidate)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if path != "/api/scan":
            return self._json({"error": "not found"}, 404)
        if not self.scan_lock.acquire(blocking=False):
            return self._json({"error": "scan already running"}, 409)
        try:
            result = self.monitor.scan(self.sources, download=True, max_downloads=10)
            return self._json(result)
        finally:
            self.scan_lock.release()


def scheduler_loop(monitor: Monitor, sources, interval_seconds: int, stop_event: threading.Event) -> None:
    while not stop_event.wait(interval_seconds):
        try:
            monitor.scan(sources, download=True, max_downloads=10)
        except Exception as error:
            print(f"[frontierlens] scheduled scan failed: {error}")


def serve(host: str = "127.0.0.1", port: int = 4173, interval_seconds: int = 3600) -> None:
    database = Database()
    database.initialize()
    sources = load_sources()
    database.sync_sources(sources)
    monitor = Monitor(database)
    FrontierLensHandler.database = database
    FrontierLensHandler.monitor = monitor
    FrontierLensHandler.sources = sources
    server = ThreadingHTTPServer((host, port), FrontierLensHandler)
    stop_event = threading.Event()
    scheduler = None
    if interval_seconds > 0:
        scheduler = threading.Thread(
            target=scheduler_loop,
            args=(monitor, sources, interval_seconds, stop_event),
            daemon=True,
            name="frontierlens-scheduler",
        )
        scheduler.start()
    print(f"FrontierLens running at http://{host}:{port} (scan every {interval_seconds}s)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()
