from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("FRONTIERLENS_DATA_DIR", ROOT / "data"))
DB_PATH = Path(os.getenv("FRONTIERLENS_DB_PATH", DATA_DIR / "frontierlens.db"))
SOURCE_CONFIG = Path(
    os.getenv("FRONTIERLENS_SOURCE_CONFIG", ROOT / "backend" / "sources.json")
)
USER_AGENT = "FrontierLensBot/0.1 (+local product prototype; evidence archival)"
MAX_DOWNLOAD_BYTES = int(os.getenv("FRONTIERLENS_MAX_DOWNLOAD_BYTES", 96 * 1024 * 1024))
ENVIRONMENT = os.getenv("FRONTIERLENS_ENV", "development").strip().lower()
ADMIN_TOKEN = os.getenv("FRONTIERLENS_ADMIN_TOKEN", "").strip()
PUBLIC_BASE_URL = os.getenv("FRONTIERLENS_PUBLIC_BASE_URL", "").strip().rstrip("/")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("FRONTIERLENS_REQUEST_TIMEOUT", "30"))
MAX_SCAN_DOWNLOADS = int(os.getenv("FRONTIERLENS_MAX_SCAN_DOWNLOADS", "10"))
AI_API_KEY = os.getenv("FRONTIERLENS_AI_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()
AI_BASE_URL = os.getenv("FRONTIERLENS_AI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
AI_MODEL = os.getenv("FRONTIERLENS_AI_MODEL", "gpt-5.6-luna").strip()


def validate_runtime_config() -> None:
    if ENVIRONMENT == "production" and len(ADMIN_TOKEN) < 24:
        raise RuntimeError(
            "FRONTIERLENS_ADMIN_TOKEN must contain at least 24 characters in production"
        )


@dataclass(frozen=True)
class SeedDocument:
    title: str
    url: str
    report_type: str
    published_at: str | None = None


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    provider: str
    name: str
    index_url: str
    allowed_domains: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...] = ()
    follow_path_patterns: tuple[str, ...] = ()
    max_follow_pages: int = 0
    priority: int = 100
    enabled: bool = True
    seed_documents: tuple[SeedDocument, ...] = ()
    request_headers: tuple[tuple[str, str], ...] = ()
    pagination: str | None = None


def ensure_data_dirs() -> None:
    for directory in (
        DATA_DIR,
        DATA_DIR / "raw",
        DATA_DIR / "parsed",
        DATA_DIR / "snapshots",
    ):
        directory.mkdir(parents=True, exist_ok=True)


def load_sources(path: Path = SOURCE_CONFIG) -> list[SourceDefinition]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources: list[SourceDefinition] = []
    for item in payload["sources"]:
        sources.append(
            SourceDefinition(
                id=item["id"],
                provider=item["provider"],
                name=item["name"],
                index_url=item["index_url"],
                allowed_domains=tuple(item["allowed_domains"]),
                allowed_path_prefixes=tuple(item.get("allowed_path_prefixes", [])),
                follow_path_patterns=tuple(item.get("follow_path_patterns", [])),
                # Large official model organisations can exceed 30 repositories.
                # The source file still opts into the limit explicitly, while a
                # hard ceiling prevents an accidental unbounded crawl.
                max_follow_pages=max(0, min(int(item.get("max_follow_pages", 0)), 120)),
                priority=int(item.get("priority", 100)),
                enabled=bool(item.get("enabled", True)),
                request_headers=tuple(
                    (str(key), str(value))
                    for key, value in item.get("request_headers", {}).items()
                ),
                pagination=item.get("pagination"),
                seed_documents=tuple(
                    SeedDocument(
                        title=document["title"],
                        url=document["url"],
                        report_type=document.get("report_type", "technical_report"),
                        published_at=document.get("published_at"),
                    )
                    for document in item.get("seed_documents", [])
                ),
            )
        )
    return sorted(sources, key=lambda source: source.priority)
