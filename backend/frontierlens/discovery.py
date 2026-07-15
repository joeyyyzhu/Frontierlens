from __future__ import annotations

import hashlib
import html as html_module
import json
import mimetypes
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from .config import DATA_DIR, MAX_DOWNLOAD_BYTES, USER_AGENT, SourceDefinition
from .database import Database, utc_now
from .parser import save_parsed_pdf


REPORT_TERMS = {
    "technical report": 6,
    "tech report": 6,
    "system card": 5,
    "model card": 4,
    "safety report": 4,
    "research paper": 3,
    "whitepaper": 3,
    "report": 2,
    "paper": 1,
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        self._href = attributes.get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            text = " ".join("".join(self._text).split())
            self.links.append((self._href, text))
            self._href = None
            self._text = []


@dataclass(frozen=True)
class Candidate:
    title: str
    url: str
    report_type: str
    score: int


def domain_allowed(url: str, allowed_domains: tuple[str, ...]) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed_domains)


def candidate_allowed(url: str, source: SourceDefinition) -> bool:
    if not domain_allowed(url, source.allowed_domains):
        return False
    if not source.allowed_path_prefixes:
        return True
    path = urllib.parse.urlparse(url).path
    return any(path.startswith(prefix) for prefix in source.allowed_path_prefixes)


def classify_candidate(title: str, url: str) -> tuple[str, int]:
    haystack = urllib.parse.unquote(f"{title} {url}").lower().replace("-", "_")
    normalized = haystack.replace("_", " ")
    score = sum(weight for term, weight in REPORT_TERMS.items() if term in normalized)
    path = urllib.parse.urlparse(url).path.lower()
    if path.endswith(".pdf"):
        score += 2
    if any(token in normalized for token in ("benchmark", "evaluation", "evals")):
        return "benchmark", max(score, 2)
    if "system card" in normalized or "safety" in normalized:
        return "safety_report", score
    if "model card" in normalized:
        return "model_card", score
    if "technical report" in normalized or "tech report" in normalized:
        return "technical_report", score
    return "research_report", score


def discover_links(html: str, base_url: str, source: SourceDefinition) -> list[Candidate]:
    parser = LinkParser()
    parser.feed(html)
    seen: set[str] = set()
    candidates: list[Candidate] = []
    raw_links = list(parser.links)
    for location in re.findall(r"<loc>(.*?)</loc>", html, flags=re.IGNORECASE | re.DOTALL):
        raw_links.append((html_module.unescape(location.strip()), ""))
    for href, text in raw_links:
        url = urllib.parse.urljoin(base_url, href).split("#", 1)[0]
        if url in seen or not candidate_allowed(url, source):
            continue
        seen.add(url)
        report_type, score = classify_candidate(text, url)
        if score < 3:
            continue
        title = text or Path(urllib.parse.urlparse(url).path).stem.replace("-", " ")
        candidates.append(Candidate(title=title[:300], url=url, report_type=report_type, score=score))
    return sorted(candidates, key=lambda candidate: (-candidate.score, candidate.title.lower()))


class Monitor:
    def __init__(self, database: Database):
        self.database = database

    def _request(self, url: str, headers: dict[str, str] | None = None) -> urllib.response.addinfourl:
        request_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8"}
        request_headers.update(headers or {})
        request = urllib.request.Request(url, headers=request_headers)
        return urllib.request.urlopen(request, timeout=30)

    def _fetch_index(self, source: SourceDefinition) -> tuple[str | None, dict[str, str]]:
        row = self.database.row("SELECT etag, last_modified FROM sources WHERE id=?", (source.id,)) or {}
        conditional: dict[str, str] = {}
        if row.get("etag"):
            conditional["If-None-Match"] = row["etag"]
        if row.get("last_modified"):
            conditional["If-Modified-Since"] = row["last_modified"]
        try:
            with self._request(source.index_url, conditional) as response:
                final_url = response.geturl()
                if not domain_allowed(final_url, source.allowed_domains):
                    raise ValueError(f"Redirected outside allowed domains: {final_url}")
                body = response.read(MAX_DOWNLOAD_BYTES + 1)
                if len(body) > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Index response exceeds size limit")
                charset = response.headers.get_content_charset() or "utf-8"
                metadata = {
                    "etag": response.headers.get("ETag") or "",
                    "last_modified": response.headers.get("Last-Modified") or "",
                    "final_url": final_url,
                }
                return body.decode(charset, errors="replace"), metadata
        except urllib.error.HTTPError as error:
            if error.code == 304:
                return None, {}
            raise

    def _download(self, candidate: Candidate, source: SourceDefinition, report_id: int) -> tuple[str, Path, str, int]:
        if not domain_allowed(candidate.url, source.allowed_domains):
            raise ValueError("Candidate URL is outside source allowlist")
        download_url = candidate.url
        parsed_candidate = urllib.parse.urlparse(candidate.url)
        if parsed_candidate.hostname == "github.com" and "/blob/" in parsed_candidate.path:
            raw_path = parsed_candidate.path.replace("/blob/", "/", 1)
            download_url = urllib.parse.urlunparse(("https", "raw.githubusercontent.com", raw_path, "", "", ""))
        with self._request(download_url) as response:
            final_url = response.geturl()
            if not domain_allowed(final_url, source.allowed_domains):
                raise ValueError(f"Download redirected outside allowed domains: {final_url}")
            content = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(content) > MAX_DOWNLOAD_BYTES:
                raise ValueError("Report exceeds download size limit")
            mime_type = response.headers.get_content_type() or mimetypes.guess_type(final_url)[0] or "application/octet-stream"
        content_hash = hashlib.sha256(content).hexdigest()
        suffix = ".pdf" if mime_type == "application/pdf" or final_url.lower().split("?", 1)[0].endswith(".pdf") else ".html"
        provider_dir = DATA_DIR / "raw" / re.sub(r"[^a-z0-9]+", "-", source.provider.lower()).strip("-")
        provider_dir.mkdir(parents=True, exist_ok=True)
        destination = provider_dir / f"{content_hash}{suffix}"
        if not destination.exists():
            destination.write_bytes(content)
        return content_hash, destination, mime_type, len(content)

    def scan(self, sources: list[SourceDefinition], download: bool = True, max_downloads: int | None = 10) -> dict:
        self.database.initialize()
        started_at = utc_now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO scan_runs(started_at, status, source_count) VALUES (?, 'running', ?)",
                (started_at, len([source for source in sources if source.enabled])),
            )
            run_id = int(cursor.lastrowid)

        summary = {
            "run_id": run_id,
            "started_at": started_at,
            "source_count": 0,
            "candidate_count": 0,
            "new_report_count": 0,
            "downloaded_count": 0,
            "parsed_count": 0,
            "error_count": 0,
            "sources": [],
        }

        for source in sources:
            if not source.enabled:
                continue
            summary["source_count"] += 1
            source_result = {"id": source.id, "provider": source.provider, "status": "ok", "candidates": 0, "new": 0}
            checked_at = utc_now()
            try:
                html, headers = self._fetch_index(source)
                if html is None:
                    source_result["status"] = "not_modified"
                    candidates: list[Candidate] = []
                else:
                    snapshot_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
                    snapshot = DATA_DIR / "snapshots" / f"{source.id}-{snapshot_hash}.html"
                    if not snapshot.exists():
                        snapshot.write_text(html, encoding="utf-8")
                    candidates = discover_links(html, headers.get("final_url", source.index_url), source)
                source_result["candidates"] = len(candidates)
                summary["candidate_count"] += len(candidates)

                with self.database.connect() as connection:
                    connection.execute(
                        """UPDATE sources SET etag=?, last_modified=?, last_checked_at=?,
                        last_status=?, last_error=NULL, updated_at=? WHERE id=?""",
                        (headers.get("etag"), headers.get("last_modified"), checked_at, source_result["status"], checked_at, source.id),
                    )

                for candidate in candidates:
                    now = utc_now()
                    try:
                        with self.database.connect() as connection:
                            cursor = connection.execute(
                                """INSERT OR IGNORE INTO reports(
                                source_id, provider, title, url, report_type, discovered_at,
                                parse_status, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                                (source.id, source.provider, candidate.title, candidate.url, candidate.report_type, now, now),
                            )
                            is_new = cursor.rowcount == 1
                            report_row = connection.execute("SELECT id, file_path FROM reports WHERE url=?", (candidate.url,)).fetchone()
                        if is_new:
                            summary["new_report_count"] += 1
                            source_result["new"] += 1
                        if not report_row or report_row["file_path"] or not download:
                            continue
                        if max_downloads is not None and summary["downloaded_count"] >= max_downloads:
                            continue
                        report_id = int(report_row["id"])
                        content_hash, file_path, mime_type, file_size = self._download(candidate, source, report_id)
                        summary["downloaded_count"] += 1
                        parse_status = "saved"
                        parsed_path: Path | None = None
                        page_count: int | None = None
                        if file_path.suffix.lower() == ".pdf":
                            parsed_path = save_parsed_pdf(file_path, content_hash, report_id=report_id)
                            parsed_payload = json.loads(parsed_path.read_text(encoding="utf-8"))
                            page_count = int(parsed_payload["page_count"])
                            parse_status = "parsed"
                            summary["parsed_count"] += 1
                        with self.database.connect() as connection:
                            connection.execute(
                                """UPDATE reports SET content_hash=?, file_path=?, mime_type=?, file_size=?,
                                page_count=?, parse_status=?, parsed_path=?, updated_at=? WHERE id=?""",
                                (
                                    content_hash,
                                    str(file_path),
                                    mime_type,
                                    file_size,
                                    page_count,
                                    parse_status,
                                    str(parsed_path) if parsed_path else None,
                                    utc_now(),
                                    report_id,
                                ),
                            )
                    except Exception as error:
                        summary["error_count"] += 1
                        source_result.setdefault("errors", []).append(f"{candidate.url}: {error}")
            except Exception as error:
                summary["error_count"] += 1
                source_result["status"] = "error"
                source_result["error"] = str(error)
                with self.database.connect() as connection:
                    connection.execute(
                        "UPDATE sources SET last_checked_at=?, last_status='error', last_error=?, updated_at=? WHERE id=?",
                        (checked_at, str(error)[:1000], checked_at, source.id),
                    )
            summary["sources"].append(source_result)

        finished_at = utc_now()
        status = "completed_with_errors" if summary["error_count"] else "completed"
        with self.database.connect() as connection:
            connection.execute(
                """UPDATE scan_runs SET finished_at=?, status=?, source_count=?, candidate_count=?,
                new_report_count=?, downloaded_count=?, parsed_count=?, error_count=?, details=? WHERE id=?""",
                (
                    finished_at,
                    status,
                    summary["source_count"],
                    summary["candidate_count"],
                    summary["new_report_count"],
                    summary["downloaded_count"],
                    summary["parsed_count"],
                    summary["error_count"],
                    json.dumps(summary["sources"], ensure_ascii=False),
                    run_id,
                ),
            )
        summary["finished_at"] = finished_at
        summary["status"] = status
        return summary
