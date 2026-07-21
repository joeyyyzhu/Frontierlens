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

from .config import DATA_DIR, MAX_DOWNLOAD_BYTES, REQUEST_TIMEOUT_SECONDS, USER_AGENT, SourceDefinition
from .catalog import infer_release
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
    "official blog": 4,
    "technical blog": 4,
    "blog": 3,
}

MODEL_RELEASE_PATTERN = re.compile(
    r"\b(?:gpt|claude|gemini|qwen|deepseek|kimi|seed(?:ream|ance)?|glm|minimax)"
    r"[-\s]?(?:[a-z]?\d+(?:\.\d+)?|oss)(?:[-\s][a-z0-9]+)*\b",
    re.IGNORECASE,
)


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
    published_at: str | None = None


SPECIFIC_REPORT_TYPES = {"technical_report", "safety_report", "model_card", "benchmark"}
GENERIC_REPORT_TYPES = {"research_report", "official_blog", "github_repository"}
REPORT_TYPE_AUTHORITY = {
    "technical_report": 5,
    "safety_report": 4,
    "model_card": 4,
    "benchmark": 4,
    "research_report": 2,
    "official_blog": 1,
    "github_repository": 1,
}


def preserve_specific_classification(existing_type: str | None, candidate_type: str) -> bool:
    """Never let a weaker link label overwrite stronger verified evidence."""
    if not existing_type:
        return False
    return REPORT_TYPE_AUTHORITY.get(existing_type, 0) > REPORT_TYPE_AUTHORITY.get(candidate_type, 0)


MONTHS = {
    month.lower(): index
    for index, month in enumerate(
        ("", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    ) if month
}


def extract_publication_date(text: str) -> str | None:
    """Return a normalized official publication date when a page exposes one."""
    cleaned = " ".join(html_module.unescape(re.sub(r"<[^>]+>", " ", text)).split())
    match = re.search(r"\b(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b", cleaned)
    if match:
        year, month, day = map(int, match.groups())
        return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
    month_names = "|".join(MONTHS)
    match = re.search(rf"\b(\d{{1,2}})\s+({month_names})\s+(20\d{{2}})\b", cleaned, re.IGNORECASE)
    if match:
        day, month, year = match.groups()
        return datetime(int(year), MONTHS[month.lower()], int(day), tzinfo=timezone.utc).isoformat()
    match = re.search(rf"\b({month_names})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b", cleaned, re.IGNORECASE)
    if match:
        month, day, year = match.groups()
        return datetime(int(year), MONTHS[month.lower()], int(day), tzinfo=timezone.utc).isoformat()
    return None


def infer_publication_date(url: str, html: str = "", raw_href: str = "") -> str | None:
    # Prefer the nearest table/list item, which usually contains the date for one document.
    if html and raw_href:
        index = html.find(raw_href)
        if index >= 0:
            for tag in ("tr", "li", "article"):
                start = html.rfind(f"<{tag}", 0, index)
                end = html.find(f"</{tag}>", index)
                if start >= 0 and end >= 0 and end - start < 8000:
                    date = extract_publication_date(html[start:end])
                    if date:
                        return date
            date = extract_publication_date(html[max(0, index - 500):index + len(raw_href) + 500])
            if date:
                return date
    # arXiv identifiers encode year and month (YYMM.xxxxx), useful when the link has no date label.
    match = re.search(r"/(?:abs|pdf)/(\d{2})(0[1-9]|1[0-2])\.\d+", url)
    if match:
        year, month = match.groups()
        return datetime(2000 + int(year), int(month), 1, tzinfo=timezone.utc).isoformat()
    return None


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


def canonicalize_url(url: str) -> str:
    """Normalize equivalent official document URLs before deduplication."""
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname == "huggingface.co" and parsed.path.endswith("/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf"):
        # This repository path was removed; the official model metadata points
        # to arXiv 2606.19348 for the same technical report.
        return "https://arxiv.org/pdf/2606.19348"
    if parsed.hostname == "github.com" and parsed.path.endswith("/MiniMax-AI/MiniMax-M1/blob/main/MiniMax_M1_tech_report.pdf"):
        return "https://arxiv.org/abs/2506.13585"
    if parsed.hostname == "huggingface.co" and "/blob/" in parsed.path and parsed.path.lower().endswith(".pdf"):
        path = parsed.path.replace("/blob/", "/resolve/", 1)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "download=true", ""))
    return url


def classify_candidate(title: str, url: str) -> tuple[str, int]:
    haystack = urllib.parse.unquote(f"{title} {url}").lower().replace("-", "_")
    normalized = haystack.replace("_", " ")
    score = sum(weight for term, weight in REPORT_TERMS.items() if term in normalized)
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    # A repository root is implementation evidence even when the anchor text
    # says “blog” or “report”; the URL itself is authoritative for this type.
    if parsed.hostname == "github.com" and len(path_parts) == 2:
        return "github_repository", max(score, 3)
    if "/models/fsf-reports/" in path:
        return "safety_report", max(score, 5)
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
    if "blog" in normalized:
        return "official_blog", score
    # Official launch indexes often name the model directly without saying "report".
    # Keep those pages as contextual evidence; release inference later rejects unrelated pages.
    title_has_release = bool(MODEL_RELEASE_PATTERN.search(title))
    path_has_release = bool(MODEL_RELEASE_PATTERN.search(urllib.parse.unquote(parsed.path)))
    shallow_official_path = parsed.hostname not in {"github.com", "raw.githubusercontent.com"} and len([part for part in parsed.path.split("/") if part]) <= 3
    if title_has_release or (path_has_release and shallow_official_path):
        return "official_blog", max(score, 3)
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
        url = canonicalize_url(urllib.parse.urljoin(base_url, href).split("#", 1)[0])
        if url in seen or not candidate_allowed(url, source):
            continue
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.hostname == "github.com" and parsed_url.path in {"/search", "/topics/qwen2", "/topics/qwen3"}:
            continue
        github_parts = [part for part in parsed_url.path.split("/") if part]
        if parsed_url.hostname == "github.com" and len(github_parts) == 2 and source.follow_path_patterns:
            if not any(re.fullmatch(pattern, parsed_url.path.rstrip("/")) for pattern in source.follow_path_patterns):
                continue
        # README navigation such as /blob/main or /tree/main is not evidence.
        # Keep only actual files from those routes; otherwise the downloader
        # wastes its limited report budget on GitHub directories and 404 pages.
        if parsed_url.hostname == "github.com" and any(marker in parsed_url.path for marker in ("/blob/", "/tree/")):
            if not re.search(r"\.(?:pdf|md|txt)$", parsed_url.path, re.IGNORECASE):
                continue
        seen.add(url)
        report_type, score = classify_candidate(text, url)
        # Official repositories frequently label an arXiv technical report only
        # as “Paper”. Keep that candidate long enough to inspect the repository's
        # citation metadata instead of dropping it at the link-scoring stage.
        normalized_text = " ".join(text.lower().split())
        if (
            score < 3
            and parsed_url.hostname == "arxiv.org"
            and normalized_text in {"paper", "report", "research paper"}
        ):
            score = 3
        if score < 3:
            continue
        title = text or Path(urllib.parse.urlparse(url).path).stem.replace("-", " ")
        candidates.append(Candidate(
            title=title[:300], url=url, report_type=report_type, score=score,
            published_at=infer_publication_date(url, html, href),
        ))
    candidates.extend(discover_embedded_publications(html, source, seen))
    return sorted(candidates, key=lambda candidate: (-candidate.score, candidate.title.lower()))


def enrich_candidates_from_official_page(candidates: list[Candidate], html: str) -> list[Candidate]:
    """Use nearby BibTeX metadata to recover report titles hidden behind generic “Paper” links."""
    decoded = html_module.unescape(html).replace(r"\u002F", "/")
    plain_text = " ".join(re.sub(r"<[^>]+>", " ", decoded).split())
    enriched: list[Candidate] = []
    for candidate in candidates:
        if candidate.report_type != "research_report" or "arxiv.org" not in candidate.url:
            enriched.append(candidate)
            continue
        identifier_match = re.search(r"/(?:abs|pdf)/(\d{4}\.\d+)", candidate.url)
        if not identifier_match:
            enriched.append(candidate)
            continue
        index = decoded.find(identifier_match.group(1))
        if index < 0:
            enriched.append(candidate)
            continue
        nearby = decoded[max(0, index - 5000):index + 1500]
        titles = re.findall(
            r"title\s*=\s*[\{\"]([^\}\"]{4,240}?technical report)\s*[\}\"]",
            nearby,
            flags=re.IGNORECASE,
        )
        if titles:
            title = re.sub(r"<[^>]+>", "", titles[-1]).strip()
        else:
            base_title = re.sub(r"\s+Research Paper$", "", candidate.title, flags=re.IGNORECASE).strip()
            phrase = re.search(
                rf"\b{re.escape(base_title)}\s+Technical Report\b",
                plain_text,
                flags=re.IGNORECASE,
            )
            if not phrase:
                enriched.append(candidate)
                continue
            title = phrase.group(0)
        enriched.append(Candidate(title, candidate.url, "technical_report", max(candidate.score, 8), candidate.published_at))
    return enriched


def discover_embedded_publications(html: str, source: SourceDefinition, seen: set[str] | None = None) -> list[Candidate]:
    """Extract official publications embedded as server-rendered JSON (for example Seed)."""
    if '"ArticleMeta"' not in html:
        return []
    seen = seen or set()
    candidates: list[Candidate] = []
    pattern = re.compile(
        r'"ArticleMeta":\{(?P<meta>.*?)\},"ArticleSubContentEn":\{"Title":"(?P<title>(?:\\.|[^"\\])*)"',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        meta = match.group("meta").replace(r"\u002F", "/").replace(r"\u0026", "&")
        link_match = re.search(r'"Link":"(https:[^"\\]+)"', meta)
        if not link_match:
            continue
        url = canonicalize_url(link_match.group(1).replace(r"\/", "/"))
        if url in seen or not candidate_allowed(url, source):
            continue
        try:
            title = json.loads(f'"{match.group("title")}"')
        except json.JSONDecodeError:
            title = match.group("title")
        model_publication = bool(re.search(r"\b(?:seed(?:ream|ance|[- ]thinking)?|technical report)\b", title, re.IGNORECASE))
        report_type, score = classify_candidate(title, url)
        if score < 3 and not model_publication:
            continue
        if score < 3:
            report_type, score = "research_report", 3
        timestamp_match = re.search(r'"PublishDate":(\d{10,13})', meta)
        published_at = None
        if timestamp_match:
            timestamp = int(timestamp_match.group(1))
            if timestamp > 10_000_000_000:
                timestamp //= 1000
            published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        seen.add(url)
        candidates.append(Candidate(str(title)[:300], url, report_type, score, published_at))
    return candidates


def discover_follow_links(html: str, base_url: str, source: SourceDefinition) -> list[str]:
    if not source.follow_path_patterns or source.max_follow_pages <= 0:
        return []
    parser = LinkParser()
    parser.feed(html)
    raw_links = list(parser.links)
    if html.lstrip().startswith("["):
        try:
            payload = json.loads(html)
            raw_links.extend(
                (str(item.get("html_url", "")), str(item.get("name", "")))
                for item in payload if isinstance(item, dict) and item.get("html_url")
            )
        except json.JSONDecodeError:
            pass
    discovered: list[str] = []
    seen: set[str] = set()
    for href, _text in raw_links:
        url = urllib.parse.urljoin(base_url, href).split("#", 1)[0].rstrip("/")
        path = urllib.parse.urlparse(url).path.rstrip("/")
        if url in seen or not domain_allowed(url, source.allowed_domains):
            continue
        if not any(re.fullmatch(pattern, path) for pattern in source.follow_path_patterns):
            continue
        seen.add(url)
        discovered.append(url)
        if len(discovered) >= source.max_follow_pages:
            break
    return discovered


def contextualize_candidate(candidate: Candidate, parent_url: str) -> Candidate:
    generic = {"technical report", "tech report", "research paper", "paper", "report", "official blog", "blog"}
    normalized_title = " ".join(re.sub(r"[^a-z]+", " ", candidate.title.lower()).split())
    if normalized_title not in generic:
        return candidate
    parts = [part for part in urllib.parse.urlparse(parent_url).path.split("/") if part]
    if len(parts) < 2:
        return candidate
    parent_name = parts[-1]
    is_explicit_technical_report = normalized_title in {"technical report", "tech report"}
    is_paper = normalized_title in {"technical report", "tech report", "research paper", "paper", "report"}
    report_type = "technical_report" if is_explicit_technical_report else candidate.report_type
    suffix = "Technical Report" if is_explicit_technical_report else ("Research Paper" if is_paper else "Official Blog")
    return Candidate(f"{parent_name} {suffix}", candidate.url, report_type, max(candidate.score, 6), candidate.published_at)


class Monitor:
    def __init__(self, database: Database):
        self.database = database

    def _request(self, url: str, headers: dict[str, str] | None = None) -> urllib.response.addinfourl:
        request_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8"}
        request_headers.update(headers or {})
        request = urllib.request.Request(url, headers=request_headers)
        return urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS)

    def _fetch_index(self, source: SourceDefinition) -> tuple[str | None, dict[str, str]]:
        row = self.database.row("SELECT etag, last_modified FROM sources WHERE id=?", (source.id,)) or {}
        conditional: dict[str, str] = {}
        if row.get("etag"):
            conditional["If-None-Match"] = row["etag"]
        if row.get("last_modified"):
            conditional["If-Modified-Since"] = row["last_modified"]
        try:
            request_headers = dict(source.request_headers)
            request_headers.update(conditional)
            with self._request(source.index_url, request_headers) as response:
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
                text = body.decode(charset, errors="replace")
                if source.pagination == "seed_article_list":
                    text = self._fetch_seed_article_pages(text, source)
                return text, metadata
        except urllib.error.HTTPError as error:
            if error.code == 304:
                return None, {}
            raise

    def _fetch_seed_article_pages(self, first_page: str, source: SourceDefinition) -> str:
        """Collect every page exposed by Seed's official publication API."""
        payload = json.loads(first_page)
        articles = list(payload.get("sub_article_list") or [])
        seen_tokens: set[str] = set()
        token = str(payload.get("next_page_token") or "")
        while payload.get("has_more") and token and token not in seen_tokens:
            seen_tokens.add(token)
            parsed = urllib.parse.urlparse(source.index_url)
            query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            query["page_token"] = token
            page_url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
            with self._request(page_url, dict(source.request_headers)) as response:
                final_url = response.geturl()
                if not domain_allowed(final_url, source.allowed_domains):
                    raise ValueError(f"Pagination redirected outside allowed domains: {final_url}")
                page_body = response.read(MAX_DOWNLOAD_BYTES + 1)
                if len(page_body) > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Paginated index response exceeds size limit")
                payload = json.loads(page_body.decode(response.headers.get_content_charset() or "utf-8", errors="replace"))
            articles.extend(payload.get("sub_article_list") or [])
            token = str(payload.get("next_page_token") or "")
        # Keep compact separators because the embedded-publication extractor
        # also consumes minified server-rendered JSON from the public website.
        return json.dumps({"sub_article_list": articles}, ensure_ascii=False, separators=(",", ":"))

    def _fetch_page(self, url: str, source: SourceDefinition) -> tuple[str, str]:
        with self._request(url) as response:
            final_url = response.geturl()
            if not domain_allowed(final_url, source.allowed_domains):
                raise ValueError(f"Redirected outside allowed domains: {final_url}")
            body = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(body) > MAX_DOWNLOAD_BYTES:
                raise ValueError("Followed page exceeds size limit")
            charset = response.headers.get_content_charset() or "utf-8"
            return body.decode(charset, errors="replace"), final_url

    def _download(self, candidate: Candidate, source: SourceDefinition, report_id: int) -> tuple[str, Path, str, int]:
        if not domain_allowed(candidate.url, source.allowed_domains):
            raise ValueError("Candidate URL is outside source allowlist")
        download_url = candidate.url
        parsed_candidate = urllib.parse.urlparse(candidate.url)
        if parsed_candidate.hostname == "github.com" and "/blob/" in parsed_candidate.path:
            raw_path = parsed_candidate.path.replace("/blob/", "/", 1)
            download_url = urllib.parse.urlunparse(("https", "raw.githubusercontent.com", raw_path, "", "", ""))
        elif parsed_candidate.hostname == "arxiv.org" and parsed_candidate.path.startswith("/abs/"):
            download_url = urllib.parse.urlunparse(("https", "arxiv.org", parsed_candidate.path.replace("/abs/", "/pdf/", 1), "", "", ""))
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
            source_result = {"id": source.id, "provider": source.provider, "status": "ok", "candidates": 0, "followed": 0, "new": 0}
            checked_at = utc_now()
            try:
                html, headers = self._fetch_index(source)
                if html is None:
                    source_result["status"] = "not_modified"
                    candidates = [
                        Candidate(row["title"], row["url"], row["report_type"], 100, row["published_at"])
                        for row in self.database.rows(
                            """SELECT title, url, report_type, published_at FROM reports
                            WHERE source_id=? AND file_path IS NULL
                            ORDER BY CASE WHEN report_type='technical_report' THEN 0 ELSE 1 END,
                                COALESCE(published_at, discovered_at) DESC LIMIT 100""",
                            (source.id,),
                        )
                    ]
                else:
                    snapshot_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
                    snapshot = DATA_DIR / "snapshots" / f"{source.id}-{snapshot_hash}.html"
                    if not snapshot.exists():
                        snapshot.write_text(html, encoding="utf-8")
                    final_index_url = headers.get("final_url", source.index_url)
                    candidates = discover_links(html, final_index_url, source)
                    for follow_url in discover_follow_links(html, final_index_url, source):
                        try:
                            followed_html, followed_url = self._fetch_page(follow_url, source)
                            source_result["followed"] += 1
                            followed_candidates = [
                                contextualize_candidate(candidate, followed_url)
                                for candidate in discover_links(followed_html, followed_url, source)
                            ]
                            candidates.extend(enrich_candidates_from_official_page(followed_candidates, followed_html))
                        except Exception as follow_error:
                            source_result.setdefault("warnings", []).append(f"{follow_url}: {follow_error}")
                seeded = [
                    Candidate(document.title, canonicalize_url(document.url), document.report_type, 100, document.published_at)
                    for document in source.seed_documents
                    if candidate_allowed(document.url, source)
                ]
                merged: dict[str, Candidate] = {}
                for candidate in [*seeded, *candidates]:
                    previous = merged.get(candidate.url)
                    if previous is None or candidate.score > previous.score or (candidate.published_at and not previous.published_at):
                        merged[candidate.url] = candidate
                # The scan budget must always save primary reports before
                # blogs, repositories, or supporting papers.
                candidates = sorted(
                    merged.values(),
                    key=lambda item: (
                        0 if item.report_type == "technical_report" else 1,
                        -item.score,
                        item.title.lower(),
                    ),
                )
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
                            existing_report = connection.execute(
                                "SELECT title, report_type FROM reports WHERE url=?", (candidate.url,)
                            ).fetchone()
                            cursor = connection.execute(
                                """INSERT OR IGNORE INTO reports(
                                source_id, provider, title, url, report_type, discovered_at,
                                published_at, parse_status, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                                (source.id, source.provider, candidate.title, candidate.url, candidate.report_type, now, candidate.published_at, now),
                            )
                            preserve_existing = bool(
                                existing_report
                                and preserve_specific_classification(existing_report["report_type"], candidate.report_type)
                            )
                            effective_title = existing_report["title"] if preserve_existing else candidate.title
                            effective_type = existing_report["report_type"] if preserve_existing else candidate.report_type
                            connection.execute(
                                """UPDATE reports SET title=?, report_type=?, published_at=COALESCE(?, published_at), updated_at=?
                                WHERE url=?""",
                                (effective_title, effective_type, candidate.published_at, now, candidate.url),
                            )
                            is_new = cursor.rowcount == 1
                            report_row = connection.execute("SELECT id, file_path FROM reports WHERE url=?", (candidate.url,)).fetchone()
                        if report_row:
                            identity = infer_release(source.provider, effective_title, candidate.url)
                            if identity:
                                self.database.associate_report_with_release(
                                    int(report_row["id"]), identity, effective_type, candidate.url, candidate.published_at
                                )
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
        # A scan can add or revise evidence under an existing release. Refresh
        # persisted briefs after all downloads and parsing have completed.
        from .briefs import BriefBuilder
        summary["briefs"] = BriefBuilder(self.database).build_all()
        return summary
