from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import backend.frontierlens.ai as ai_module
from backend.frontierlens.ai import AIService
from backend.frontierlens.config import SourceDefinition
from backend.frontierlens.catalog import infer_release, release_date_basis
from backend.frontierlens.database import Database
from backend.frontierlens.discovery import Candidate, canonicalize_url, classify_candidate, contextualize_candidate, discover_follow_links, discover_links, domain_allowed, enrich_candidates_from_official_page, extract_publication_date, preserve_specific_classification
from backend.frontierlens.server import humanize_report_title, report_matches_model, report_source_keys
from backend.frontierlens.audit import audit_catalog
from backend.frontierlens.briefs import BriefBuilder
from backend.frontierlens.knowledge import KnowledgeService


class DiscoveryTests(unittest.TestCase):
    def test_huggingface_pdf_links_use_the_direct_download_form(self) -> None:
        self.assertEqual(
            canonicalize_url("https://huggingface.co/org/model/blob/main/report.pdf"),
            "https://huggingface.co/org/model/resolve/main/report.pdf?download=true",
        )
        self.assertEqual(
            canonicalize_url("https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf"),
            "https://arxiv.org/pdf/2606.19348",
        )
        self.assertEqual(
            canonicalize_url("https://github.com/MiniMax-AI/MiniMax-M1/blob/main/MiniMax_M1_tech_report.pdf"),
            "https://arxiv.org/abs/2506.13585",
        )

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

    def test_model_release_pages_are_kept_without_polluting_github_navigation(self) -> None:
        report_type, score = classify_candidate(
            "Kimi K3", "https://www.kimi.com/blog/kimi-k3"
        )
        self.assertEqual(report_type, "official_blog")
        self.assertGreaterEqual(score, 3)
        _report_type, navigation_score = classify_candidate(
            "Sign in", "https://github.com/login?return_to=/MoonshotAI/Kimi-K2"
        )
        self.assertLess(navigation_score, 3)

    def test_github_readme_directories_are_not_report_candidates(self) -> None:
        source = SourceDefinition(
            id="qwen", provider="Qwen", name="Qwen", index_url="https://github.com/QwenLM/Qwen3",
            allowed_domains=("github.com",),
        )
        html = '''
        <a href="/QwenLM/Qwen3/blob/main">Qwen3</a>
        <a href="/QwenLM/Qwen3/blob/main/Qwen3_Technical_Report.pdf">Technical Report</a>
        '''
        candidates = discover_links(html, source.index_url, source)
        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0].url.endswith("Qwen3_Technical_Report.pdf"))

    def test_generic_official_paper_link_uses_nearby_technical_report_title(self) -> None:
        source = SourceDefinition(
            id="qwen", provider="Qwen", name="Qwen",
            index_url="https://github.com/QwenLM/Qwen3-Omni",
            allowed_domains=("github.com", "arxiv.org"),
            follow_path_patterns=(r"^/QwenLM/Qwen[A-Za-z0-9._-]+$",), max_follow_pages=10,
        )
        html = '''
        <a href="https://arxiv.org/abs/2509.17765">Paper</a>
        <pre>@article{qwen3omni, title={Qwen3-Omni Technical Report}, eprint={2509.17765}}</pre>
        '''
        discovered = discover_links(html, source.index_url, source)
        contextualized = [contextualize_candidate(item, source.index_url) for item in discovered]
        enriched = enrich_candidates_from_official_page(contextualized, html)
        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0].title, "Qwen3-Omni Technical Report")
        self.assertEqual(enriched[0].report_type, "technical_report")

    def test_github_repository_and_navigation_have_distinct_types(self) -> None:
        report_type, _score = classify_candidate("Qwen2.5-Omni", "https://github.com/QwenLM/Qwen2.5-Omni")
        self.assertEqual(report_type, "github_repository")
        source = SourceDefinition(
            id="qwen", provider="Qwen", name="Qwen", index_url="https://github.com/orgs/QwenLM/repositories",
            allowed_domains=("github.com",),
        )
        html = '''
        <a href="/topics/qwen2">qwen2</a>
        <a href="/search?q=topic%3Aqwen3+org%3AQwenLM&type=Repositories">qwen3</a>
        '''
        self.assertEqual(discover_links(html, source.index_url, source), [])

    def test_github_org_source_rejects_unmonitored_repositories(self) -> None:
        source = SourceDefinition(
            id="qwen", provider="Qwen", name="Qwen", index_url="https://github.com/orgs/QwenLM/repositories",
            allowed_domains=("github.com",),
            follow_path_patterns=(r"^/QwenLM/Qwen[A-Za-z0-9._-]+$",),
        )
        html = '''
        <a href="/QwenLM/Qwen2.5-Omni">Qwen2.5-Omni</a>
        <a href="/openai/whisper">Whisper</a>
        <a href="/features/actions">Actions</a>
        '''
        candidates = discover_links(html, source.index_url, source)
        self.assertEqual([candidate.url for candidate in candidates], ["https://github.com/QwenLM/Qwen2.5-Omni"])

    def test_frontier_safety_report_page_is_safety_evidence(self) -> None:
        report_type, _score = classify_candidate(
            "Learn more", "https://deepmind.google/models/fsf-reports/gemini-3-pro/"
        )
        self.assertEqual(report_type, "safety_report")

    def test_discovers_sitemap_entries(self) -> None:
        xml = "<urlset><url><loc>https://research.example.com/model-system-card/</loc></url></urlset>"
        candidates = discover_links(xml, self.source.index_url, self.source)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].report_type, "safety_report")

    def test_dynamic_repository_discovery_and_official_date(self) -> None:
        source = SourceDefinition(
            id="qwen", provider="Qwen", name="Qwen repos",
            index_url="https://github.com/orgs/QwenLM/repositories",
            allowed_domains=("github.com", "arxiv.org"),
            follow_path_patterns=(r"^/QwenLM/Qwen[A-Za-z0-9._-]+$",),
            max_follow_pages=10,
        )
        html = '<a href="/QwenLM/Qwen3.6">Qwen3.6</a><a href="/QwenLM/Qwen-VLA">Qwen-VLA</a>'
        self.assertEqual(len(discover_follow_links(html, source.index_url, source)), 2)
        report_html = '<li>[2026-05-12] <a href="https://arxiv.org/abs/2605.12345">Technical Report</a></li>'
        candidate = discover_links(report_html, "https://github.com/QwenLM/Qwen-VLA", source)[0]
        self.assertEqual(candidate.published_at, "2026-05-12T00:00:00+00:00")

    def test_github_api_repository_index_is_supported(self) -> None:
        source = SourceDefinition(
            id="deepseek", provider="DeepSeek", name="DeepSeek repos",
            index_url="https://api.github.com/orgs/deepseek-ai/repos",
            allowed_domains=("api.github.com", "github.com"),
            follow_path_patterns=(r"^/deepseek-ai/DeepSeek-[A-Za-z0-9._-]+$",), max_follow_pages=10,
        )
        payload = '[{"name":"DeepSeek-R2","html_url":"https://github.com/deepseek-ai/DeepSeek-R2"}]'
        self.assertEqual(discover_follow_links(payload, source.index_url, source), ["https://github.com/deepseek-ai/DeepSeek-R2"])

    def test_publication_date_normalization(self) -> None:
        self.assertEqual(extract_publication_date("Published 19 May 2026"), "2026-05-19T00:00:00+00:00")
        candidate = contextualize_candidate(
            Candidate("📑 Technical Report", "https://arxiv.org/abs/2606.12345", "technical_report", 8),
            "https://github.com/QwenLM/Qwen-VLA",
        )
        self.assertEqual(candidate.title, "Qwen-VLA Technical Report")

    def test_generic_paper_in_official_model_repo_stays_research_evidence(self) -> None:
        candidate = contextualize_candidate(
            Candidate("Research Paper", "https://arxiv.org/abs/2512.15603", "research_report", 3),
            "https://github.com/QwenLM/Qwen3-Omni",
        )
        self.assertEqual(candidate.report_type, "research_report")
        self.assertEqual(candidate.title, "Qwen3-Omni Research Paper")

    def test_generic_rediscovery_cannot_downgrade_technical_report(self) -> None:
        self.assertTrue(preserve_specific_classification("technical_report", "research_report"))
        self.assertTrue(preserve_specific_classification("technical_report", "model_card"))
        self.assertTrue(preserve_specific_classification("model_card", "official_blog"))
        self.assertFalse(preserve_specific_classification("research_report", "technical_report"))

    def test_embedded_official_publication_is_discovered(self) -> None:
        source = SourceDefinition(
            id="seed", provider="ByteDance Seed", name="Seed", index_url="https://seed.bytedance.com/en/public_papers",
            allowed_domains=("seed.bytedance.com", "arxiv.org"),
        )
        html = r'''<script>{"ArticleMeta":{"PublishDate":1770249600000,"ExternalLinks":[{"Link":"https:\u002F\u002Farxiv.org\u002Fpdf\u002F2602.12345"}]},"ArticleSubContentEn":{"Title":"Seedance 2.0 Technical Report"}}</script>'''
        candidates = discover_links(html, source.index_url, source)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Seedance 2.0 Technical Report")
        self.assertTrue(candidates[0].published_at.startswith("2026-02"))

    def test_numeric_minimax_and_seed_agent_reports_map_to_releases(self) -> None:
        minimax = infer_release("MiniMax", "MiniMax-01 Technical Report", "https://arxiv.org/abs/2501.08313")
        seed = infer_release("ByteDance Seed", "UI-TARS-2 Technical Report", "https://arxiv.org/abs/2509.02544")
        gr = infer_release("ByteDance Seed", "GR-3 Technical Report", "https://arxiv.org/pdf/2507.15493")
        self.assertEqual(minimax.release_slug, "minimax-01")
        self.assertEqual(seed.release_slug, "ui-tars-2")
        self.assertEqual(gr.release_slug, "gr-3")

    def test_feed_source_mapping_preserves_evidence_type_and_host(self) -> None:
        keys = report_source_keys({
            "report_type": "technical_report",
            "url": "https://github.com/example/model/report.pdf",
        })
        self.assertEqual(keys, ["tech-report", "github"])
        self.assertEqual(
            report_source_keys({"report_type": "safety_report", "url": "https://example.com/card"}),
            ["safety-report"],
        )
        self.assertEqual(
            report_source_keys({"report_type": "model_card", "url": "https://example.com/model"}),
            ["safety-report"],
        )
        self.assertEqual(
            report_source_keys({"report_type": "official_blog", "url": "https://www.kimi.com/blog/kimi-k3"}),
            ["official-blog"],
        )
        self.assertEqual(
            humanize_report_title({"title": "View model card", "url": "https://example.com/gemini-robotics-er-1-6/"}),
            "Gemini Robotics Er 1 6",
        )
        self.assertTrue(report_matches_model("gpt", {"provider": "OpenAI", "title": "GPT OSS", "url": "https://openai.com/gpt-oss"}))
        self.assertFalse(report_matches_model("gpt", {"provider": "OpenAI", "title": "Sora 2", "url": "https://openai.com/sora-2"}))
        self.assertFalse(report_matches_model("gemini", {"provider": "Google DeepMind", "title": "Veo 3", "url": "https://deepmind.google/veo-3"}))

    def test_release_identity_is_inferred_from_official_document(self) -> None:
        identity = infer_release("Moonshot AI", "Kimi K2 Technical Report", "https://github.com/MoonshotAI/Kimi-K2")
        self.assertIsNotNone(identity)
        self.assertEqual(identity.family_id, "kimi")
        self.assertEqual(identity.release_slug, "kimi-k2")
        self.assertIsNone(infer_release("OpenAI", "Sora System Card", "https://openai.com/sora"))
        self.assertEqual(infer_release("Qwen", "Qwen-VLA Technical Report", "https://github.com/QwenLM/Qwen-VLA").release_slug, "qwen-vla")
        self.assertEqual(
            infer_release("Qwen", "Qwen-RobotNav Technical Report", "https://github.com/QwenLM/Qwen-RobotNav").release_slug,
            "qwen-robotnav",
        )
        self.assertEqual(
            infer_release("Qwen", "Qwen-RobotManip Technical Report", "https://github.com/QwenLM/Qwen-RobotManip").release_slug,
            "qwen-robotmanip",
        )
        self.assertEqual(infer_release("Z.ai", "GLM-5 Technical Report", "https://github.com/zai-org/GLM-5").family_id, "glm")
        self.assertEqual(
            infer_release("Z.ai", "technical report(GLM-4.5)", "https://arxiv.org/abs/2508.06471").release_slug,
            "glm-4-5",
        )
        self.assertEqual(
            infer_release("Z.ai", "GLM-OCR Technical Report", "https://arxiv.org/abs/2603.10910").release_slug,
            "glm-ocr",
        )
        self.assertEqual(infer_release("MiniMax", "MiniMax M2.5: Built for Real-World Productivity", "https://minimax.io/blog/m25").release_name, "MiniMax M2.5")
        self.assertEqual(
            infer_release("Anthropic", "Sonnet 5 system card", "https://www.anthropic.com/claude-sonnet-5-system-card").release_slug,
            "claude-sonnet-5",
        )
        self.assertEqual(
            infer_release("Anthropic", "Read system card", "https://anthropic.com/claude-opus-4-8-system-card").release_slug,
            "claude-opus-4-8",
        )
        self.assertEqual(
            infer_release("Anthropic", "Read system card", "https://anthropic.com/claude-opus-4-7-system-card").release_slug,
            "claude-opus-4-7",
        )
        self.assertEqual(
            infer_release("Qwen", "Qwen3 ASR Toolkit", "https://github.com/QwenLM/Qwen3-ASR-Toolkit").release_slug,
            "qwen3-asr",
        )
        self.assertEqual(
            infer_release("Qwen", "Qwen3 Coder Tool Call Demo", "https://github.com/QwenLM/Qwen3-Coder-Tool-Call-Demo").release_slug,
            "qwen3-coder",
        )
        self.assertEqual(
            infer_release(
                "Google DeepMind",
                "Gemini Robotics 1.5 Technical Report",
                "https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-1-5-Tech-Report.pdf",
            ).release_slug,
            "gemini-robotics-1-5",
        )
        self.assertIsNone(
            infer_release("OpenAI", "GPT-5 lowers protein synthesis cost", "https://openai.com/index/gpt-5-lowers-protein-synthesis-cost/")
        )
        self.assertEqual(
            infer_release("Moonshot AI", "Kimi K2.6Advancing Open-Source Coding", "https://www.kimi.com/blog/kimi-k2-6").release_slug,
            "kimi-k2-6",
        )
        self.assertEqual(
            infer_release("ByteDance Seed", "Seed3D 2.0 Official Launch", "https://seed.bytedance.com/en/blog/seed3d-2-0").release_slug,
            "seed3d-2-0",
        )
        self.assertEqual(
            infer_release("ByteDance Seed", "Seeduplex Official Launch", "https://seed.bytedance.com/en/blog/seeduplex").release_slug,
            "seeduplex",
        )

    def test_date_basis_does_not_confuse_document_updates_with_model_launches(self) -> None:
        self.assertEqual(release_date_basis("gpt-5-6", {"official_blog"}), "official_release")
        self.assertEqual(release_date_basis("gemini-3-5-audio", {"model_card"}), "official_document_update")
        self.assertEqual(release_date_basis("unknown-release", {"official_blog"}), "official_source_published")
        self.assertEqual(
            infer_release("ByteDance Seed", "Seed2.1 Officially Released: Advancing AI Productivity", "https://seed.bytedance.com/en/seed2_1").release_slug,
            "seed2-1",
        )
        self.assertEqual(
            infer_release("ByteDance Seed", "Seed2.0 Seed2.0", "https://seed.bytedance.com/en/seed2").release_slug,
            "seed2-0",
        )
        self.assertEqual(
            infer_release("ByteDance Seed", "Seedream 5.0 Pro", "https://seed.bytedance.com/en/seedream5_0_pro").release_slug,
            "seedream-5-0-pro",
        )
        self.assertEqual(
            infer_release(
                "ByteDance Seed",
                "Seedream 5.0 ProSeedream 5.0 ProA multimodal image generation model",
                "https://seed.bytedance.com/en/seedream5_0_pro",
            ).release_slug,
            "seedream-5-0-pro",
        )


class DatabaseTests(unittest.TestCase):
    def test_empty_catalog_passes_integrity_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            result = audit_catalog(database)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["summary"]["errors"], 0)

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

    def test_user_preferences_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            saved = database.save_user_preferences(
                "demo-user",
                ["qwen", "claude"],
                ["tech-report", "safety-report"],
                [{"name": "MiniMax", "provider": "MiniMax"}],
                [{"name": "MiniMax Research", "url": "https://example.com/research", "status": "pending_verification"}],
            )
            self.assertEqual(saved["models"], ["qwen", "claude"])
            preference = database.get_user_preferences("demo-user")
            self.assertEqual(preference["sources"], ["tech-report", "safety-report"])
            self.assertEqual(preference["profile_id"], "demo-user")
            self.assertEqual(preference["customModels"][0]["name"], "MiniMax")
            self.assertEqual(preference["customSources"][0]["status"], "pending_verification")

    def test_profiles_are_private_and_token_authenticated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            profile = database.create_profile()
            self.assertTrue(database.authenticate_profile(profile["profileId"], profile["accessToken"]))
            self.assertFalse(database.authenticate_profile(profile["profileId"], "wrong-token"))

    def test_multiple_documents_coexist_under_one_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            source = SourceDefinition(
                id="qwen",
                provider="Qwen",
                name="Qwen",
                index_url="https://github.com/QwenLM/Qwen3",
                allowed_domains=("github.com",),
            )
            database.sync_sources([source])
            now = "2025-05-14T00:00:00+00:00"
            with database.connect() as connection:
                first = connection.execute(
                    """INSERT INTO reports(source_id, provider, title, url, report_type, discovered_at, parse_status, updated_at)
                    VALUES ('qwen', 'Qwen', 'Qwen3 Technical Report', 'https://github.com/QwenLM/Qwen3/report.pdf',
                    'technical_report', ?, 'parsed', ?)""", (now, now)
                ).lastrowid
                second = connection.execute(
                    """INSERT INTO reports(source_id, provider, title, url, report_type, discovered_at, parse_status, updated_at)
                    VALUES ('qwen', 'Qwen', 'Qwen3 Official Blog', 'https://github.com/QwenLM/Qwen3/blog',
                    'official_blog', ?, 'saved', ?)""", (now, now)
                ).lastrowid
            identity = infer_release("Qwen", "Qwen3 Technical Report", "https://github.com/QwenLM/Qwen3")
            database.associate_report_with_release(first, identity, "technical_report", "https://github.com/QwenLM/Qwen3/report.pdf")
            database.associate_report_with_release(second, identity, "official_blog", "https://github.com/QwenLM/Qwen3/blog")
            releases = database.list_releases()
            self.assertEqual(len(releases), 1)
            self.assertEqual(releases[0]["document_count"], 2)
            self.assertEqual(releases[0]["documents"][0]["is_primary"], 1)

    def test_release_brief_is_extracted_and_persisted_with_page_citation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "test.db")
            database.initialize()
            database.sync_sources([
                SourceDefinition(
                    id="qwen", provider="Qwen", name="Qwen",
                    index_url="https://github.com/QwenLM/Qwen3", allowed_domains=("github.com",),
                )
            ])
            parsed_path = root / "report.json"
            parsed_path.write_text(json.dumps({
                "sections": [{
                    "title": "Abstract", "first_page": 1, "last_page": 2,
                    "text": "The model uses a mixture-of-experts architecture to improve inference efficiency while preserving broad model capacity.",
                }]
            }), encoding="utf-8")
            now = "2025-05-14T00:00:00+00:00"
            with database.connect() as connection:
                report_id = connection.execute(
                    """INSERT INTO reports(source_id, provider, title, url, report_type, discovered_at,
                    content_hash, parsed_path, parse_status, updated_at)
                    VALUES ('qwen', 'Qwen', 'Qwen3 Technical Report', 'https://github.com/QwenLM/Qwen3/report.pdf',
                    'technical_report', ?, 'hash', ?, 'parsed', ?)""",
                    (now, str(parsed_path), now),
                ).lastrowid
            identity = infer_release("Qwen", "Qwen3 Technical Report", "https://github.com/QwenLM/Qwen3")
            release_id = database.associate_report_with_release(
                report_id, identity, "technical_report", "https://github.com/QwenLM/Qwen3/report.pdf"
            )
            result = BriefBuilder(database).build_all()
            self.assertEqual(result["built"], 1)
            brief = database.row("SELECT * FROM release_briefs WHERE release_id=?", (release_id,))
            highlights = json.loads(brief["highlights"])
            self.assertEqual(highlights[0]["label"], "Architecture")
            self.assertEqual(highlights[0]["firstPage"], 1)
            self.assertEqual(brief["generation_method"], "official_evidence_extraction_v2")

    def test_release_brief_rejects_pdf_caption_noise(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "test.db")
            database.initialize()
            database.sync_sources([
                SourceDefinition(
                    id="qwen", provider="Qwen", name="Qwen",
                    index_url="https://example.com/reports", allowed_domains=("example.com",),
                )
            ])
            parsed_path = root / "report.json"
            parsed_path.write_text(json.dumps({
                "sections": [{
                    "title": "Abstract", "first_page": 1, "last_page": 2,
                    "text": (
                        "Cross-EpisodeMemoryNavigationContextProtocol Diverse Tasks Q: Where should I go? "
                        "A: <think>The door is ahead.</think><act>A</act>. "
                        "We present a sparse transformer architecture that reduces inference latency by 35 percent while supporting long-context agent tasks."
                    ),
                }]
            }), encoding="utf-8")
            now = "2026-07-20T00:00:00+00:00"
            with database.connect() as connection:
                report_id = connection.execute(
                    """INSERT INTO reports(source_id, provider, title, url, report_type, discovered_at,
                    content_hash, parsed_path, parse_status, updated_at)
                    VALUES ('qwen', 'Qwen', 'Qwen4 Technical Report', 'https://example.com/report.pdf',
                    'technical_report', ?, 'hash', ?, 'parsed', ?)""",
                    (now, str(parsed_path), now),
                ).lastrowid
            identity = infer_release("Qwen", "Qwen4 Technical Report", "https://example.com/report.pdf")
            self.assertIsNotNone(identity)
            release_id = database.associate_report_with_release(
                report_id, identity, "technical_report", "https://example.com/report.pdf"
            )

            BriefBuilder(database).build_release(release_id, "Qwen4")
            brief = database.row("SELECT highlights FROM release_briefs WHERE release_id=?", (release_id,))
            highlights = json.loads(brief["highlights"])
            self.assertEqual(len(highlights), 1)
            self.assertNotIn("<think>", highlights[0]["text"])

    def test_knowledge_graph_indexes_release_concepts_with_page_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "test.db")
            database.initialize()
            database.sync_sources([SourceDefinition(
                id="qwen", provider="Qwen", name="Qwen",
                index_url="https://github.com/QwenLM/Qwen3", allowed_domains=("github.com",),
            )])
            parsed_path = root / "report.json"
            parsed_path.write_text(json.dumps({"sections": [{
                "title": "Architecture", "first_page": 3, "last_page": 5,
                "text": "Qwen3 uses a Mixture-of-Experts architecture with expert routing and sparse activation. A multi-modal approach was used only to extract training text from PDFs.",
            }]}), encoding="utf-8")
            now = "2025-05-14T00:00:00+00:00"
            with database.connect() as connection:
                report_id = connection.execute(
                    """INSERT INTO reports(source_id, provider, title, url, report_type, discovered_at,
                    content_hash, parsed_path, parse_status, updated_at)
                    VALUES ('qwen', 'Qwen', 'Qwen3 Technical Report', 'https://example.com/qwen3.pdf',
                    'technical_report', ?, 'knowledge-hash', ?, 'parsed', ?)""",
                    (now, str(parsed_path), now),
                ).lastrowid
            identity = infer_release("Qwen", "Qwen3 Technical Report", "https://github.com/QwenLM/Qwen3")
            release_id = database.associate_report_with_release(
                report_id, identity, "technical_report", "https://example.com/qwen3.pdf", now
            )
            graph = KnowledgeService(database).release_graph(release_id)
            moe = next(item for item in graph["primaryConcepts"] if item["id"] == "mixture-of-experts")
            self.assertEqual(graph["status"], "ready")
            self.assertEqual(moe["evidenceState"], "supported")
            self.assertEqual(moe["evidence"][0]["firstPage"], 3)
            self.assertEqual(moe["evidence"][0]["reportId"], report_id)
            self.assertTrue(any(edge["type"] == "contrasts_with" for edge in moe["relationships"]))
            self.assertNotIn("multimodal", {item["id"] for item in graph["primaryConcepts"]})

    def test_knowledge_alias_resolves_to_one_canonical_concept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            service = KnowledgeService(database)
            self.assertEqual(service.concept("MoE")["id"], "mixture-of-experts")
            self.assertEqual(service.concept("mixture of experts")["id"], "mixture-of-experts")

    def test_knowledge_graph_does_not_invent_evidence_for_unparsed_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            database.sync_sources([SourceDefinition(
                id="kimi", provider="Moonshot AI", name="Kimi",
                index_url="https://www.kimi.com/blog/kimi-k3", allowed_domains=("kimi.com",),
            )])
            now = "2026-07-17T00:00:00+00:00"
            with database.connect() as connection:
                report_id = connection.execute(
                    """INSERT INTO reports(source_id, provider, title, url, report_type, discovered_at,
                    parse_status, updated_at) VALUES ('kimi', 'Moonshot AI', 'Kimi K3',
                    'https://www.kimi.com/blog/kimi-k3', 'official_blog', ?, 'saved', ?)""",
                    (now, now),
                ).lastrowid
            identity = infer_release("Moonshot AI", "Kimi K3", "https://www.kimi.com/blog/kimi-k3")
            release_id = database.associate_report_with_release(
                report_id, identity, "official_blog", "https://www.kimi.com/blog/kimi-k3", now
            )
            graph = KnowledgeService(database).release_graph(release_id)
            self.assertEqual(graph["status"], "pending")
            self.assertEqual(graph["primaryConcepts"], [])


class AIServiceTests(unittest.TestCase):
    def test_grounded_response_is_normalized_with_citation(self) -> None:
        response_body = json.dumps({
            "output": [{
                "content": [{
                    "type": "output_text",
                    "text": json.dumps({
                        "answer": "本节介绍统一推理模式。",
                        "key_points": ["重点一", "重点二", "重点三", "不会返回第四条"],
                        "why_it_matters": "产品可以控制延迟与效果。",
                    }, ensure_ascii=False),
                }],
            }],
        }, ensure_ascii=False).encode("utf-8")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return response_body

        with patch.object(ai_module, "AI_API_KEY", "test-key"), patch.object(
            ai_module.urllib.request, "urlopen", return_value=FakeResponse()
        ):
            result = AIService().assist(
                task="summarize",
                source_text="Official source text",
                selected_text="",
                report_title="Qwen3 Technical Report",
                section_title="Abstract",
                first_page=1,
                last_page=2,
            )
        self.assertEqual(result["answer"], "本节介绍统一推理模式。")
        self.assertEqual(len(result["keyPoints"]), 3)
        self.assertEqual(result["citation"]["firstPage"], 1)


if __name__ == "__main__":
    unittest.main()
