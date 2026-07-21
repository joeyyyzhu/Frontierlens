from __future__ import annotations

import json
import hashlib
import secrets
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
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 30000")
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

                CREATE TABLE IF NOT EXISTS user_preferences (
                    profile_id TEXT PRIMARY KEY,
                    tracked_models TEXT NOT NULL,
                    tracked_sources TEXT NOT NULL,
                    custom_models TEXT NOT NULL DEFAULT '[]',
                    custom_sources TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_families (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_releases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL REFERENCES model_families(id),
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    released_at TEXT,
                    status TEXT NOT NULL DEFAULT 'published',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS release_documents (
                    release_id INTEGER NOT NULL REFERENCES model_releases(id) ON DELETE CASCADE,
                    report_id INTEGER NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    evidence_weight INTEGER NOT NULL,
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (release_id, report_id)
                );

                CREATE TABLE IF NOT EXISTS release_briefs (
                    release_id INTEGER PRIMARY KEY REFERENCES model_releases(id) ON DELETE CASCADE,
                    summary TEXT NOT NULL,
                    highlights TEXT NOT NULL DEFAULT '[]',
                    product_implications TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_fingerprint TEXT NOT NULL,
                    generation_method TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'evidence_only',
                    generated_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    aliases TEXT NOT NULL DEFAULT '[]',
                    one_liner TEXT NOT NULL,
                    why_it_exists TEXT NOT NULL,
                    analogy TEXT NOT NULL,
                    product_impact TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS concept_relationships (
                    source_concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
                    target_concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
                    relationship_type TEXT NOT NULL,
                    explanation TEXT NOT NULL DEFAULT '',
                    evidence_state TEXT NOT NULL DEFAULT 'background',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (source_concept_id, target_concept_id, relationship_type)
                );

                CREATE TABLE IF NOT EXISTS release_concepts (
                    release_id INTEGER NOT NULL REFERENCES model_releases(id) ON DELETE CASCADE,
                    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    evidence_state TEXT NOT NULL,
                    context_summary TEXT NOT NULL DEFAULT '',
                    indexed_at TEXT NOT NULL,
                    PRIMARY KEY (release_id, concept_id)
                );

                CREATE TABLE IF NOT EXISTS concept_evidence (
                    release_id INTEGER NOT NULL REFERENCES model_releases(id) ON DELETE CASCADE,
                    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
                    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                    first_page INTEGER,
                    last_page INTEGER,
                    quote_hint TEXT NOT NULL DEFAULT '',
                    evidence_state TEXT NOT NULL DEFAULT 'supported',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (release_id, concept_id, report_id)
                );

                CREATE INDEX IF NOT EXISTS reports_provider_idx ON reports(provider);
                CREATE INDEX IF NOT EXISTS reports_hash_idx ON reports(content_hash);
                CREATE INDEX IF NOT EXISTS reports_discovered_idx ON reports(discovered_at DESC);
                CREATE INDEX IF NOT EXISTS releases_family_idx ON model_releases(family_id, released_at DESC);
                CREATE INDEX IF NOT EXISTS release_documents_release_idx ON release_documents(release_id, evidence_weight DESC);
                CREATE INDEX IF NOT EXISTS concept_relationship_source_idx ON concept_relationships(source_concept_id);
                CREATE INDEX IF NOT EXISTS release_concepts_release_idx ON release_concepts(release_id, priority);
                CREATE INDEX IF NOT EXISTS concept_evidence_release_idx ON concept_evidence(release_id, concept_id);

                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            preference_columns = {row[1] for row in connection.execute("PRAGMA table_info(user_preferences)")}
            if "custom_models" not in preference_columns:
                connection.execute("ALTER TABLE user_preferences ADD COLUMN custom_models TEXT NOT NULL DEFAULT '[]'")
            if "custom_sources" not in preference_columns:
                connection.execute("ALTER TABLE user_preferences ADD COLUMN custom_sources TEXT NOT NULL DEFAULT '[]'")

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_profile(self) -> dict[str, str]:
        profile_id = secrets.token_urlsafe(18)
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO profiles(profile_id, token_hash, created_at, last_seen_at) VALUES (?, ?, ?, ?)",
                (profile_id, self._token_hash(token), now, now),
            )
        return {"profileId": profile_id, "accessToken": token, "createdAt": now}

    def authenticate_profile(self, profile_id: str, token: str) -> bool:
        if not token:
            return False
        expected = self.row("SELECT token_hash FROM profiles WHERE profile_id=?", (profile_id,))
        if not expected or not secrets.compare_digest(expected["token_hash"], self._token_hash(token)):
            return False
        with self.connect() as connection:
            connection.execute("UPDATE profiles SET last_seen_at=? WHERE profile_id=?", (utc_now(), profile_id))
        return True

    def associate_report_with_release(self, report_id: int, identity, report_type: str, url: str, published_at: str | None = None) -> int:
        from .catalog import document_role, official_release_date

        now = utc_now()
        role, weight = document_role(report_type, url)
        published_at = official_release_date(identity.release_slug, published_at)
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO model_families(id, provider, name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET provider=excluded.provider, name=excluded.name, updated_at=excluded.updated_at""",
                (identity.family_id, identity.provider, identity.family_name, now, now),
            )
            connection.execute(
                """INSERT INTO model_releases(family_id, slug, name, released_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET name=excluded.name,
                    released_at=CASE
                        WHEN model_releases.released_at IS NULL THEN excluded.released_at
                        WHEN excluded.released_at IS NULL THEN model_releases.released_at
                        WHEN excluded.released_at < model_releases.released_at THEN excluded.released_at
                        ELSE model_releases.released_at END,
                    updated_at=excluded.updated_at""",
                (identity.family_id, identity.release_slug, identity.release_name, published_at, now, now),
            )
            release = connection.execute("SELECT id FROM model_releases WHERE slug=?", (identity.release_slug,)).fetchone()
            release_id = int(release["id"])
            connection.execute(
                """INSERT INTO release_documents(release_id, report_id, role, evidence_weight, is_primary, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET release_id=excluded.release_id, role=excluded.role,
                    evidence_weight=excluded.evidence_weight, is_primary=excluded.is_primary""",
                (release_id, report_id, role, weight, int(role == "primary"), now),
            )
        return release_id

    def rebuild_release_index(self, catalog_version: str, *, force: bool = False) -> int:
        """Rebuild derived release relationships when catalog rules change."""
        from .catalog import EVIDENCE_OVERRIDES, URL_ALIASES, document_role, infer_release, official_release_date

        current = self.row("SELECT value FROM app_metadata WHERE key='catalog_version'")
        if not force and current and current["value"] == catalog_version:
            return 0
        with self.connect() as connection:
            for old_url, canonical_url in URL_ALIASES.items():
                old = connection.execute("SELECT id FROM reports WHERE url=?", (old_url,)).fetchone()
                canonical = connection.execute("SELECT id FROM reports WHERE url=?", (canonical_url,)).fetchone()
                if old and canonical:
                    connection.execute("DELETE FROM reports WHERE id=?", (old["id"],))
                elif old:
                    connection.execute("UPDATE reports SET url=?, updated_at=? WHERE id=?", (canonical_url, utc_now(), old["id"]))
            for url, override in EVIDENCE_OVERRIDES.items():
                connection.execute(
                    "UPDATE reports SET title=?, report_type=?, updated_at=? WHERE url=?",
                    (override["title"], override["report_type"], utc_now(), url),
                )
        reports = self.rows("SELECT id, provider, title, url, report_type, published_at FROM reports ORDER BY id")
        now = utc_now()
        associated = 0
        with self.connect() as connection:
            connection.execute("DELETE FROM release_documents")
            connection.execute("DELETE FROM model_releases")
            connection.execute("DELETE FROM model_families")
            for report in reports:
                identity = infer_release(report["provider"], report["title"], report["url"])
                if not identity:
                    continue
                role, weight = document_role(report["report_type"], report["url"])
                release_date = official_release_date(identity.release_slug, report["published_at"])
                connection.execute(
                    """INSERT INTO model_families(id, provider, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET provider=excluded.provider, name=excluded.name, updated_at=excluded.updated_at""",
                    (identity.family_id, identity.provider, identity.family_name, now, now),
                )
                connection.execute(
                    """INSERT INTO model_releases(family_id, slug, name, released_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET name=excluded.name,
                        released_at=CASE
                            WHEN model_releases.released_at IS NULL THEN excluded.released_at
                            WHEN excluded.released_at IS NULL THEN model_releases.released_at
                            WHEN excluded.released_at < model_releases.released_at THEN excluded.released_at
                            ELSE model_releases.released_at END,
                        updated_at=excluded.updated_at""",
                    (identity.family_id, identity.release_slug, identity.release_name, release_date, now, now),
                )
                release = connection.execute("SELECT id FROM model_releases WHERE slug=?", (identity.release_slug,)).fetchone()
                connection.execute(
                    """INSERT INTO release_documents(release_id, report_id, role, evidence_weight, is_primary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (int(release["id"]), report["id"], role, weight, int(role == "primary"), now),
                )
                associated += 1
            connection.execute(
                """INSERT INTO app_metadata(key, value, updated_at) VALUES ('catalog_version', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (catalog_version, now),
            )
        return associated

    def list_releases(self, limit: int = 100) -> list[dict[str, Any]]:
        releases = self.rows(
            """SELECT r.id, r.slug, r.name, r.released_at, r.status,
                f.id AS family_id, f.name AS family_name, f.provider,
                COUNT(d.report_id) AS document_count,
                SUM(CASE WHEN d.is_primary=1 THEN 1 ELSE 0 END) AS primary_document_count,
                MAX(p.discovered_at) AS last_document_at
            FROM model_releases r
            JOIN model_families f ON f.id=r.family_id
            LEFT JOIN release_documents d ON d.release_id=r.id
            LEFT JOIN reports p ON p.id=d.report_id
            GROUP BY r.id
            ORDER BY (r.released_at IS NULL) ASC, r.released_at DESC, last_document_at DESC
            LIMIT ?""",
            (limit,),
        )
        for release in releases:
            release["documents"] = self.rows(
                """SELECT p.id, p.title, p.url, p.report_type, p.published_at, p.discovered_at,
                    p.parse_status, p.page_count, d.role, d.evidence_weight, d.is_primary
                FROM release_documents d JOIN reports p ON p.id=d.report_id
                WHERE d.release_id=? ORDER BY d.is_primary DESC, d.evidence_weight DESC, p.id DESC""",
                (release["id"],),
            )
            brief = self.row(
                """SELECT summary, highlights, product_implications, evidence_ids,
                    generation_method, status, generated_at
                FROM release_briefs WHERE release_id=?""",
                (release["id"],),
            )
            if brief:
                for field in ("highlights", "product_implications", "evidence_ids"):
                    brief[field] = json.loads(brief[field])
            release["brief"] = brief
        return releases

    def upsert_release_brief(
        self, *, release_id: int, summary: str, highlights: list[dict[str, Any]],
        product_implications: list[dict[str, Any]], evidence_ids: list[int],
        evidence_fingerprint: str, generation_method: str, status: str, generated_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO release_briefs(
                    release_id, summary, highlights, product_implications, evidence_ids,
                    evidence_fingerprint, generation_method, status, generated_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(release_id) DO UPDATE SET summary=excluded.summary,
                    highlights=excluded.highlights, product_implications=excluded.product_implications,
                    evidence_ids=excluded.evidence_ids, evidence_fingerprint=excluded.evidence_fingerprint,
                    generation_method=excluded.generation_method, status=excluded.status,
                    generated_at=excluded.generated_at, updated_at=excluded.updated_at""",
                (
                    release_id, summary, json.dumps(highlights, ensure_ascii=False),
                    json.dumps(product_implications, ensure_ascii=False), json.dumps(evidence_ids),
                    evidence_fingerprint, generation_method, status, generated_at, utc_now(),
                ),
            )

    def get_user_preferences(self, profile_id: str) -> dict[str, Any] | None:
        preference = self.row(
            "SELECT profile_id, tracked_models, tracked_sources, custom_models, custom_sources, updated_at FROM user_preferences WHERE profile_id=?",
            (profile_id,),
        )
        if not preference:
            return None
        return {
            "profile_id": preference["profile_id"],
            "models": json.loads(preference["tracked_models"]),
            "sources": json.loads(preference["tracked_sources"]),
            "customModels": json.loads(preference["custom_models"]),
            "customSources": json.loads(preference["custom_sources"]),
            "updatedAt": preference["updated_at"],
        }

    def save_user_preferences(
        self,
        profile_id: str,
        models: list[str],
        sources: list[str],
        custom_models: list[dict[str, str]] | None = None,
        custom_sources: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        custom_models = custom_models or []
        custom_sources = custom_sources or []
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO user_preferences (
                    profile_id, tracked_models, tracked_sources, custom_models, custom_sources, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    tracked_models=excluded.tracked_models,
                    tracked_sources=excluded.tracked_sources,
                    custom_models=excluded.custom_models,
                    custom_sources=excluded.custom_sources,
                    updated_at=excluded.updated_at
                """,
                (profile_id, json.dumps(models), json.dumps(sources), json.dumps(custom_models), json.dumps(custom_sources), now, now),
            )
        return {"profile_id": profile_id, "models": models, "sources": sources, "customModels": custom_models, "customSources": custom_sources, "updatedAt": now}

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
