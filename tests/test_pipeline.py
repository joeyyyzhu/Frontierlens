from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.frontierlens.config import SourceDefinition
from backend.frontierlens.database import Database
from backend.frontierlens.discovery import classify_candidate, discover_links, domain_allowed


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SourceDefinition(
            id="example",
            provider="Example AI",
            name="Example reports",
            index_url="https://research.example.com/reports",
            allowed_domains=("example.com",),
        )

    def test_domain_allowlist_rejects_http_and_lookalikes(self) -> None:
        self.assertTrue(domain_allowed("https://cdn.example.com/report.pdf", ("example.com",)))
        self.assertFalse(domain_allowed("http://cdn.example.com/report.pdf", ("example.com",)))
        self.assertFalse(domain_allowed("https://example.com.evil.test/report.pdf", ("example.com",)))

    def test_discovers_report_and_rejects_external_link(self) -> None:
        html = """
        <a href="/papers/model-1-technical-report.pdf">Model 1 Technical Report</a>
        <a href="https://evil.test/report.pdf">Technical Report</a>
        <a href="/about">About us</a>
        """
        candidates = discover_links(html, self.source.index_url, self.source)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].report_type, "technical_report")

    def test_report_classification(self) -> None:
        report_type, score = classify_candidate("Model System Card", "https://example.com/card.pdf")
        self.assertEqual(report_type, "safety_report")
        self.assertGreaterEqual(score, 5)

    def test_discovers_sitemap_entries(self) -> None:
        xml = "<urlset><url><loc>https://research.example.com/model-system-card/</loc></url></urlset>"
        candidates = discover_links(xml, self.source.index_url, self.source)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].report_type, "safety_report")


class DatabaseTests(unittest.TestCase):
    def test_initialization_and_source_sync(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            database.sync_sources(
                [
                    SourceDefinition(
                        id="example",
                        provider="Example AI",
                        name="Example",
                        index_url="https://example.com/reports",
                        allowed_domains=("example.com",),
                    )
                ]
            )
            row = database.row("SELECT provider, last_status FROM sources WHERE id='example'")
            self.assertEqual(row, {"provider": "Example AI", "last_status": "never"})


if __name__ == "__main__":
    unittest.main()
