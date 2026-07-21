from __future__ import annotations

import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .catalog import RELEASE_OVERRIDES, release_date_basis
from .config import load_sources
from .database import Database


def _domain_allowed(hostname: str, domains: tuple[str, ...]) -> bool:
    hostname = hostname.lower().rstrip(".")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def audit_catalog(database: Database) -> dict[str, Any]:
    """Run the integrity checks required by an evidence-first catalog."""
    sources = {source.id: source for source in load_sources()}
    issues: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    reports = database.rows(
        "SELECT id, source_id, provider, title, url, report_type, published_at, parse_status, file_path FROM reports"
    )
    releases = database.list_releases(1000)

    for report in reports:
        source = sources.get(report["source_id"])
        if not source:
            issues.append({"severity": "error", "code": "unknown_source", "reportId": report["id"]})
            continue
        parsed = urllib.parse.urlparse(report["url"])
        if parsed.scheme != "https" or not _domain_allowed(parsed.hostname or "", source.allowed_domains):
            issues.append({
                "severity": "error", "code": "source_domain_violation", "reportId": report["id"], "url": report["url"]
            })
        if report["published_at"]:
            try:
                published = datetime.fromisoformat(report["published_at"].replace("Z", "+00:00"))
                if published > now:
                    issues.append({
                        "severity": "error", "code": "future_publication_date", "reportId": report["id"],
                        "publishedAt": report["published_at"],
                    })
            except ValueError:
                issues.append({"severity": "error", "code": "invalid_publication_date", "reportId": report["id"]})

    basis_counts: Counter[str] = Counter()
    visible_release_count = 0
    quarantined_release_count = 0
    for release in releases:
        report_types = {document["report_type"] for document in release["documents"]}
        basis = release_date_basis(release["slug"], report_types)
        basis_counts[basis] += 1
        if not release["released_at"]:
            quarantined_release_count += 1
            issues.append({
                "severity": "review", "code": "undated_release_quarantined", "release": release["slug"],
            })
            continue
        visible_release_count += 1
        if release["slug"] in RELEASE_OVERRIDES and not release["documents"]:
            issues.append({"severity": "error", "code": "verified_release_without_evidence", "release": release["slug"]})

    source_health = database.rows(
        "SELECT id, provider, name, last_status, last_checked_at, last_error FROM sources ORDER BY priority, id"
    )
    for source in source_health:
        if source["last_status"] not in {"ok", "not_modified"}:
            issues.append({
                "severity": "warning", "code": "source_not_healthy", "source": source["id"],
                "status": source["last_status"], "error": source["last_error"],
            })

    severity_counts = Counter(issue["severity"] for issue in issues)
    return {
        "status": "pass" if not severity_counts["error"] else "fail",
        "checkedAt": now.isoformat(timespec="seconds"),
        "summary": {
            "sources": len(source_health), "reports": len(reports), "releases": len(releases),
            "visibleReleases": visible_release_count, "quarantinedReleases": quarantined_release_count,
            "verifiedReleaseDates": basis_counts["official_release"],
            "officialDocumentDates": basis_counts["official_document_update"],
            "officialSourceDates": basis_counts["official_source_published"],
            "errors": severity_counts["error"], "warnings": severity_counts["warning"],
            "reviews": severity_counts["review"],
        },
        "issues": issues,
    }
