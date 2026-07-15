from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, SourceDefinition, ensure_data_dirs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        ensure_data_dirs()
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    name TEXT NOT NULL,
                    index_url TEXT NOT NULL UNIQUE,
                    allowed_domains TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    etag TEXT,
                    last_modified TEXT,
                    last_checked_at TEXT,
                    last_status TEXT NOT NULL DEFAULT 'never',
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    source_count INTEGER NOT NULL DEFAULT 0,
                    candidate_count INTEGER NOT NULL DEFAULT 0,
                    new_report_count INTEGER NOT NULL DEFAULT 0,
                    downloaded_count INTEGER NOT NULL DEFAULT 0,
                    parsed_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    details TEXT
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL REFERENCES sources(id),
                    provider TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    report_type TEXT NOT NULL,
                    discovered_at TEXT NOT NULL,
                    published_at TEXT,
                    content_hash TEXT,
                    file_path TEXT,
                    mime_type TEXT,
                    file_size INTEGER,
                    page_count INTEGER,
                    parse_status TEXT NOT NULL DEFAULT 'pending',
                    parsed_path TEXT,
                    metadata TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS reports_provider_idx ON reports(provider);
                CREATE INDEX IF NOT EXISTS reports_hash_idx ON reports(content_hash);
                CREATE INDEX IF NOT EXISTS reports_discovered_idx ON reports(discovered_at DESC);
                """
            )

    def sync_sources(self, sources: list[SourceDefinition]) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute("UPDATE sources SET enabled=0, updated_at=?", (now,))
            for source in sources:
                connection.execute(
                    """
                    INSERT INTO sources (
                        id, provider, name, index_url, allowed_domains, priority,
                        enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        provider=excluded.provider,
                        name=excluded.name,
                        index_url=excluded.index_url,
                        allowed_domains=excluded.allowed_domains,
                        priority=excluded.priority,
                        enabled=excluded.enabled,
                        updated_at=excluded.updated_at
                    """,
                    (
                        source.id,
                        source.provider,
                        source.name,
                        source.index_url,
                        json.dumps(source.allowed_domains),
                        source.priority,
                        int(source.enabled),
                        now,
                        now,
                    ),
                )

    def rows(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]

    def row(self, sql: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as connection:
            result = connection.execute(sql, parameters).fetchone()
            return dict(result) if result else None
