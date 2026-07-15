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
MAX_DOWNLOAD_BYTES = int(os.getenv("FRONTIERLENS_MAX_DOWNLOAD_BYTES", 60 * 1024 * 1024))


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    provider: str
    name: str
    index_url: str
    allowed_domains: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...] = ()
    priority: int = 100
    enabled: bool = True


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
                priority=int(item.get("priority", 100)),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return sorted(sources, key=lambda source: source.priority)
