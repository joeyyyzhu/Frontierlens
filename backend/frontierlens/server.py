from __future__ import annotations

import json
import mimetypes
import hmac
import re
import threading
import time
import urllib.parse
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import ADMIN_TOKEN, DATA_DIR, ENVIRONMENT, MAX_SCAN_DOWNLOADS, ROOT, load_sources, validate_runtime_config
from .catalog import CATALOG_VERSION, release_date_basis
from .database import Database
from .discovery import Monitor
from .ai import AIService, AIUnavailable
from .knowledge import KnowledgeService


MODEL_PROFILES = {
    "qwen": {"name": "Qwen", "provider": "Qwen", "mark": "Q"},
    "gpt": {"name": "GPT", "provider": "OpenAI", "mark": "O"},
    "claude": {"name": "Claude", "provider": "Anthropic", "mark": "A"},
    "gemini": {"name": "Gemini", "provider": "Google DeepMind", "mark": "G"},
    "deepseek": {"name": "DeepSeek", "provider": "DeepSeek", "mark": "D"},
    "kimi": {"name": "Kimi", "provider": "Moonshot AI", "mark": "K"},
    "seed": {"name": "Seed", "provider": "ByteDance Seed", "mark": "S"},
    "glm": {"name": "GLM", "provider": "Z.ai", "mark": "G"},
    "minimax": {"name": "MiniMax", "provider": "MiniMax", "mark": "M"},
}

SOURCE_LABELS = {
    "tech-report": "Tech Report",
    "official-blog": "Official Blog",
    "benchmark": "Benchmark",
    "github": "GitHub",
    "safety-report": "Safety Report",
}

RELEASE_TRACKS = {
    "seedream-5-0-pro": "Image",
    "seed2-1": "Foundation",
    "seed3d-2-0": "3D",
    "seeduplex": "Speech",
    "seed2-0": "Foundation",
    "seedream-5-0-lite": "Image",
    "seedance-2-0": "Video",
}

VERIFIED_RELEASE_HIGHLIGHTS = {
    "kimi-k3": [
        {"label": "Architecture", "text": "KDA、Attention Residuals 与 Stable LatentMoE 共同支撑 3T 级扩展。"},
        {"label": "Scale", "text": "总参数 2.8T，每次有效激活 16 / 896 个专家。"},
        {"label": "Product", "text": "原生视觉与 1M 上下文，重点面向长周期 Coding 与知识工作。"},
    ],
    "gpt-5-6": [
        {"label": "Model family", "text": "Sol、Terra、Luna 三档覆盖旗舰、均衡与高性价比场景。"},
        {"label": "Efficiency", "text": "强调每 token 智能效率与复杂知识工作的持续执行能力。"},
        {"label": "Product", "text": "已覆盖 ChatGPT、Codex 与 API，可按任务价值选择能力档位。"},
    ],
    "claude-sonnet-5": [
        {"label": "Agents", "text": "重点提升 Coding、Agent 与专业工作场景的持续执行表现。"},
        {"label": "Safety", "text": "系统卡单列提示注入、Agentic safety 与网络安全评测。"},
        {"label": "Positioning", "text": "Sonnet 级性能升级，但官方并未将其描述为最高能力边界。"},
    ],
    "gemini-3-5-flash": [
        {"label": "Reasoning", "text": "支持 thinking levels，在质量、成本和延迟之间调节。"},
        {"label": "Context", "text": "支持最高 1M token 的多模态输入上下文。"},
        {"label": "Product", "text": "适合需要推理控制、长上下文与多模态理解的高频产品。"},
    ],
    "glm-5-2": [
        {"label": "Long horizon", "text": "把 1M 上下文作为长周期 Coding 与 Agent 任务的工程能力。"},
        {"label": "Architecture", "text": "IndexShare 降低稀疏注意力在长上下文下的计算开销。"},
        {"label": "Inference", "text": "改进 MTP 推测解码层，以提高接受长度和生成效率。"},
    ],
    "minimax-m3": [
        {"label": "Architecture", "text": "引入 MiniMax Sparse Attention，面向超长上下文效率。"},
        {"label": "Context", "text": "API 支持最高 1M token 上下文。"},
        {"label": "Product", "text": "原生多模态，并聚焦 Coding、Agent 与长周期任务。"},
    ],
    "qwen3-6-max-preview": [
        {"label": "Coding", "text": "预览版重点提升 Agentic Coding 与真实开发任务表现。"},
        {"label": "Knowledge", "text": "强化世界知识与指令遵循。"},
        {"label": "Status", "text": "仍属于 Preview，产品决策应保留稳定性与可用性验证。"},
    ],
    "seed3d-2-0": [
        {"label": "Generation", "text": "两阶段 DiT 将整体结构与高频细节解耦，提升 3D 资产生成质量。"},
        {"label": "Materials", "text": "统一 PBR 材质生成，并用 MoE 与语义条件提升材质精度。"},
        {"label": "Product", "text": "面向可仿真 3D 内容，覆盖部件拆分、关节化与场景构建。"},
    ],
    "seed2-0": [
        {"label": "Multimodal", "text": "强化视觉理解、知识推理和复杂多模态任务表现。"},
        {"label": "Agents", "text": "面向复杂指令、长周期规划与工具协作能力。"},
        {"label": "Product", "text": "Pro、Lite、Mini 与 Code 组成面向不同成本和场景的模型族。"},
    ],
    "seed2-1": [
        {"label": "Agents", "text": "强化跨工具、跨环境的多步骤任务交付，重点面向真实生产力场景。"},
        {"label": "Coding", "text": "覆盖需求理解、架构设计、实现、调试和结果验证的端到端工程流程。"},
        {"label": "Multimodal", "text": "继续提升复杂文档、图表、长视频与空间信息理解。"},
    ],
    "seedream-5-0-pro": [
        {"label": "Design", "text": "强化高密度信息图、复杂排版与专业视觉生产。"},
        {"label": "Editing", "text": "支持标注和草图引导的交互式编辑与图层分离。"},
        {"label": "Product", "text": "面向广告、教育、办公和创意工作流的高质量图像交付。"},
    ],
}


def release_highlight_payload(release_slug: str, documents: list[dict], brief: dict | None = None) -> dict:
    curated = VERIFIED_RELEASE_HIGHLIGHTS.get(release_slug, [])
    extracted = (brief or {}).get("highlights", [])
    highlights = curated or extracted
    if not highlights:
        return {
            "highlights": [], "highlightBasis": None, "evidenceState": "unstructured",
            "briefSummary": (brief or {}).get("summary"), "productImplications": [],
        }
    has_report = any(document["reportType"] == "technical_report" for document in documents)
    if curated:
        basis = "Human-verified · official evidence"
        evidence_state = "primary_verified" if has_report else "supporting_only"
    else:
        basis = "Extracted from official Tech Report" if has_report else "Extracted from official evidence"
        evidence_state = "evidence_extracted"
    return {
        "highlights": highlights,
        "highlightBasis": basis,
        "evidenceState": evidence_state,
        "briefSummary": (brief or {}).get("summary"),
        "productImplications": (brief or {}).get("product_implications", []),
        "briefMethod": (brief or {}).get("generation_method"),
    }


def report_source_keys(report: dict) -> list[str]:
    report_type = report.get("report_type")
    keys: list[str] = []
    if report_type == "technical_report":
        keys.append("tech-report")
    elif report_type in {"safety_report", "model_card"}:
        keys.append("safety-report")
    elif report_type == "official_blog":
        keys.append("official-blog")
    elif report_type == "benchmark":
        keys.append("benchmark")
    hostname = urllib.parse.urlparse(report.get("url") or "").hostname or ""
    if hostname in {"github.com", "raw.githubusercontent.com"}:
        keys.append("github")
    return list(dict.fromkeys(keys))


def humanize_report_title(report: dict) -> str:
    title = (report.get("title") or "").replace("_", " ").removesuffix(".pdf").strip()
    if title.lower() in {"view model card", "model card", "view system card", "read system card"}:
        parts = [part for part in urllib.parse.urlparse(report.get("url") or "").path.split("/") if part]
        if parts:
            title = parts[-1].replace("-", " ")
    special = {"gpt": "GPT", "oss": "OSS", "qwen": "Qwen", "claude": "Claude", "gemini": "Gemini", "sora": "Sora", "codex": "Codex"}
    words = title.split()
    return " ".join(special.get(word.lower(), word.capitalize() if word.islower() else word) for word in words)


def report_matches_model(model_key: str, report: dict) -> bool:
    haystack = f"{report.get('title', '')} {report.get('url', '')}".lower()
    if model_key == "qwen":
        return report.get("provider") == "Qwen" or "qwen" in haystack
    keywords = {
        "gpt": ("gpt",),
        "claude": ("claude",),
        "gemini": ("gemini",),
        "deepseek": ("deepseek",),
        "kimi": ("kimi", "moonshot"),
        "seed": ("seed", "seedream", "seedance"),
        "glm": ("glm", "z.ai"),
        "minimax": ("minimax",),
    }
    return any(keyword in haystack for keyword in keywords.get(model_key, (model_key,)))


class FrontierLensHandler(BaseHTTPRequestHandler):
    database: Database
    monitor: Monitor
    ai_service: AIService
    knowledge_service: KnowledgeService
    sources = []
    scan_lock = threading.Lock()
    allowed_models = {"qwen", "gpt", "claude", "gemini", "deepseek", "kimi", "seed", "glm", "minimax"}
    allowed_preference_sources = {"tech-report", "official-blog", "benchmark", "github", "safety-report"}
    ai_usage: dict[str, list[float]] = {}
    ai_rate_lock = threading.Lock()

    def log_message(self, format: str, *args) -> None:
        print(json.dumps({
            "service": "frontierlens",
            "request_id": getattr(self, "request_id", ""),
            "remote": self.client_address[0],
            "message": format % args,
        }, ensure_ascii=False))

    def _common_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        self.send_header("X-Request-ID", self.request_id)

    def handle_one_request(self) -> None:
        self.request_id = uuid.uuid4().hex[:16]
        super().handle_one_request()

    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._common_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, *, inline: bool = False) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        file_size = path.stat().st_size
        start, end = 0, file_size - 1
        range_header = self.headers.get("Range") if inline else None
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            if match.group(1):
                start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))
            if start > end or start >= file_size:
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            end = min(end, file_size - 1)
        length = end - start + 1
        self.send_response(HTTPStatus.PARTIAL_CONTENT if range_header else HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        if inline:
            self.send_header("Cache-Control", "private, max-age=3600")
        elif path.suffix.lower() in {".html", ".js", ".css"}:
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        else:
            self.send_header("Cache-Control", "public, max-age=86400")
        if inline:
            self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
            self.send_header("Accept-Ranges", "bytes")
            if range_header:
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self._common_headers()
        self.end_headers()
        with path.open("rb") as file:
            file.seek(start)
            remaining = length
            while remaining:
                chunk = file.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > 64_000:
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _profile_id(self, path: str, prefix: str) -> str | None:
        if not path.startswith(prefix):
            return None
        profile_id = urllib.parse.unquote(path[len(prefix):])
        return profile_id if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", profile_id) else None

    def _bearer_token(self) -> str:
        authorization = self.headers.get("Authorization", "")
        return authorization[7:].strip() if authorization.startswith("Bearer ") else ""

    def _authenticated_profile(self, path: str, prefix: str) -> str | None:
        profile_id = self._profile_id(path, prefix)
        if not profile_id or not self.database.authenticate_profile(profile_id, self._bearer_token()):
            return None
        return profile_id

    def _admin_authorized(self) -> bool:
        if ENVIRONMENT != "production" and not ADMIN_TOKEN:
            return True
        token = self.headers.get("X-FrontierLens-Admin", "")
        return bool(ADMIN_TOKEN) and hmac.compare_digest(token, ADMIN_TOKEN)

    def _ai_rate_allowed(self, profile_id: str) -> bool:
        now = time.time()
        with self.ai_rate_lock:
            recent = [timestamp for timestamp in self.ai_usage.get(profile_id, []) if now - timestamp < 60]
            if len(recent) >= 20:
                self.ai_usage[profile_id] = recent
                return False
            recent.append(now)
            self.ai_usage[profile_id] = recent
            return True

    def _report_payload(self, report: dict) -> dict:
        if report.get("parsed_path") and Path(report["parsed_path"]).exists():
            report["parsed"] = json.loads(Path(report["parsed_path"]).read_text(encoding="utf-8"))
        report["original_pdf_url"] = f"/api/reports/{report['id']}/original"
        return report

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/health":
            return self._json({
                "status": "ok",
                "service": "frontierlens",
                "version": "0.2.0",
                "environment": ENVIRONMENT,
                "ai_assistance": self.ai_service.available,
            })
        if path == "/api/ready":
            try:
                self.database.row("SELECT 1 AS ready")
                return self._json({"status": "ready"})
            except Exception:
                return self._json({"status": "not_ready"}, 503)
        if path == "/api/sources":
            return self._json(self.database.rows("SELECT * FROM sources ORDER BY priority, provider"))
        if path == "/api/reports":
            return self._json(self.database.rows("SELECT * FROM reports ORDER BY discovered_at DESC LIMIT 200"))
        if path == "/api/releases":
            return self._json(self.database.list_releases())
        release_knowledge_match = re.fullmatch(r"/api/releases/(\d+)/knowledge", path)
        if release_knowledge_match:
            payload = self.knowledge_service.release_graph(int(release_knowledge_match.group(1)))
            return self._json(payload, 200) if payload else self._json({"error": "release not found"}, 404)
        if path.startswith("/api/concepts/"):
            identifier = urllib.parse.unquote(path[len("/api/concepts/"):])
            release_id = None
            if parsed.query:
                query = urllib.parse.parse_qs(parsed.query)
                try:
                    release_id = int(query.get("releaseId", [""])[0])
                except ValueError:
                    return self._json({"error": "invalid release id"}, 400)
            payload = self.knowledge_service.concept(identifier, release_id=release_id)
            return self._json(payload, 200) if payload else self._json({"error": "concept not found"}, 404)
        if path == "/api/reports/featured":
            report = self.database.row(
                """SELECT * FROM reports
                WHERE parse_status='parsed' AND report_type='technical_report'
                ORDER BY CASE WHEN title LIKE '%Qwen3%' THEN 0 ELSE 1 END,
                         discovered_at DESC LIMIT 1"""
            )
            if not report:
                return self._json({"error": "no parsed technical report found"}, 404)
            return self._json(self._report_payload(report))
        if path.startswith("/api/reports/") and path.endswith("/original"):
            parts = path.strip("/").split("/")
            try:
                report_id = int(parts[2])
            except (ValueError, IndexError):
                return self._json({"error": "invalid report id"}, 400)
            report = self.database.row("SELECT file_path, mime_type FROM reports WHERE id=?", (report_id,))
            if not report or not report.get("file_path"):
                return self._json({"error": "original file not found"}, 404)
            file_path = Path(report["file_path"]).resolve()
            data_root = DATA_DIR.resolve()
            if data_root not in file_path.parents:
                return self._json({"error": "invalid original file path"}, 403)
            return self._serve_file(file_path, inline=True)
        if path.startswith("/api/reports/"):
            try:
                report_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self._json({"error": "invalid report id"}, 400)
            report = self.database.row("SELECT * FROM reports WHERE id=?", (report_id,))
            if not report:
                return self._json({"error": "report not found"}, 404)
            return self._json(self._report_payload(report))
        if path == "/api/runs":
            return self._json(self.database.rows("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 50"))
        if path == "/api/monitor/summary":
            sources = self.database.rows("SELECT id, provider, name, index_url, last_checked_at, last_status, last_error FROM sources WHERE enabled=1 ORDER BY priority")
            latest_run = self.database.row("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1")
            counts = self.database.row(
                """SELECT COUNT(*) AS reports,
                SUM(CASE WHEN parse_status='parsed' THEN 1 ELSE 0 END) AS parsed,
                COUNT(DISTINCT provider) AS providers FROM reports"""
            ) or {"reports": 0, "parsed": 0, "providers": 0}
            recent = self.database.rows(
                """SELECT p.id, p.provider, p.title, p.url, p.report_type, p.discovered_at,
                    p.page_count, p.parse_status, r.id AS release_id, r.slug AS release_slug,
                    r.name AS release_name, r.family_id
                FROM reports p
                LEFT JOIN release_documents d ON d.report_id=p.id
                LEFT JOIN model_releases r ON r.id=d.release_id
                ORDER BY p.discovered_at DESC LIMIT 10"""
            )
            return self._json({
                "sources": sources,
                "latest_run": latest_run,
                "counts": counts,
                "recent_reports": recent,
                "manual_scan_available": ENVIRONMENT != "production",
            })
        if path.startswith("/api/preferences/"):
            profile_id = self._authenticated_profile(path, "/api/preferences/")
            if not profile_id:
                return self._json({"error": "unauthorized"}, 401)
            preference = self.database.get_user_preferences(profile_id)
            if not preference:
                return self._json({"error": "preferences not found"}, 404)
            return self._json(preference)
        if path.startswith("/api/feed/"):
            profile_id = self._authenticated_profile(path, "/api/feed/")
            if not profile_id:
                return self._json({"error": "unauthorized"}, 401)
            preference = self.database.get_user_preferences(profile_id)
            if not preference:
                return self._json({"error": "preferences not found"}, 404)
            tracked_models = [key for key in preference["models"] if key in MODEL_PROFILES]
            tracked_sources = set(preference["sources"])
            releases = self.database.list_releases(200)
            items = []
            models_with_items = set()
            for release in releases:
                model_key = release["family_id"]
                if model_key not in tracked_models:
                    continue
                documents = []
                combined_source_keys: list[str] = []
                for document in release["documents"]:
                    source_keys = report_source_keys(document)
                    matching_sources = [key for key in preference["sources"] if key in source_keys and key in tracked_sources]
                    if not matching_sources:
                        continue
                    combined_source_keys.extend(matching_sources)
                    documents.append({
                        "id": document["id"],
                        "title": humanize_report_title(document),
                        "url": document["url"],
                        "reportType": document["report_type"],
                        "sourceKeys": matching_sources,
                        "sourceLabels": [
                            "Model Card" if document["report_type"] == "model_card" and key == "safety-report" else SOURCE_LABELS[key]
                            for key in matching_sources
                        ],
                        "role": document["role"],
                        "isPrimary": bool(document["is_primary"]),
                        "parseStatus": document["parse_status"],
                        "pageCount": document["page_count"],
                    })
                if not documents:
                    continue
                profile = MODEL_PROFILES[model_key]
                models_with_items.add(model_key)
                primary = next((document for document in documents if document["isPrimary"]), documents[0])
                technical_reports = [document for document in documents if document["reportType"] == "technical_report"]
                # An official report can be authentic even when its exact model
                # launch date is not stated. Keep it searchable without promoting
                # it into the chronological release feed.
                evidence_only = not release["released_at"]
                if evidence_only and not technical_reports:
                    continue
                readable_report = next(
                    (document for document in technical_reports if document["parseStatus"] == "parsed" and document["pageCount"]),
                    None,
                )
                source_keys = list(dict.fromkeys(combined_source_keys))
                source_labels = list(dict.fromkeys(
                    label for document in documents for label in document["sourceLabels"]
                ))
                date_basis = release_date_basis(
                    release["slug"], {document["reportType"] for document in documents}
                )
                if evidence_only:
                    date_basis = "official_report_undated"
                items.append({
                    "id": f"release-{release['id']}",
                    "releaseId": release["id"],
                    "releaseSlug": release["slug"],
                    "releaseTrack": RELEASE_TRACKS.get(release["slug"]),
                    "modelKey": model_key,
                    "modelName": profile["name"],
                    "provider": release["provider"],
                    "mark": profile["mark"],
                    "title": release["name"],
                    "url": primary["url"],
                    "sourceKeys": source_keys,
                    "sourceLabels": source_labels,
                    "publishedAt": release["released_at"],
                    "discoveredAt": release["last_document_at"],
                    "dateBasis": date_basis,
                    "catalogStatus": "evidence_only" if evidence_only else "verified_release",
                    "pageCount": primary["pageCount"],
                    "parseStatus": primary["parseStatus"],
                    "documentCount": len(documents),
                    "documents": documents,
                    "workspaceReady": bool(documents),
                    "hasTechReport": bool(technical_reports),
                    "techReportCount": len(technical_reports),
                    "techReportId": technical_reports[0]["id"] if technical_reports else None,
                    "readableReportId": readable_report["id"] if readable_report else None,
                    "canReadTechReport": bool(readable_report),
                    **release_highlight_payload(release["slug"], documents, release.get("brief")),
                })
                if len(items) >= 120:
                    break
            watching = [
                {"modelKey": key, "modelName": MODEL_PROFILES[key]["name"], "provider": MODEL_PROFILES[key]["provider"]}
                for key in tracked_models if key not in models_with_items
            ]
            watching.extend(
                {
                    "modelKey": f"custom-{index}",
                    "modelName": item["name"],
                    "provider": item.get("provider", "自定义厂商"),
                    "custom": True,
                }
                for index, item in enumerate(preference.get("customModels", []))
            )
            return self._json({
                "profileId": profile_id,
                "preferences": preference,
                "items": items,
                "watching": watching,
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (ROOT / relative).resolve()
        if ROOT.resolve() not in candidate.parents and candidate != ROOT.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        self._serve_file(candidate)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if path == "/api/profiles":
            return self._json(self.database.create_profile(), 201)
        if path == "/api/ai/assist":
            payload = self._read_json()
            if payload is None:
                return self._json({"error": "invalid JSON body"}, 400)
            profile_id = str(payload.get("profileId", ""))
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", profile_id) or not self.database.authenticate_profile(profile_id, self._bearer_token()):
                return self._json({"error": "unauthorized"}, 401)
            if not self._ai_rate_allowed(profile_id):
                return self._json({"error": "rate limit exceeded"}, 429)
            try:
                report_id = int(payload.get("reportId"))
                section_index = int(payload.get("sectionIndex", 0))
            except (TypeError, ValueError):
                return self._json({"error": "invalid report or section"}, 400)
            task = str(payload.get("task", ""))
            selected_text = str(payload.get("selectedText", "")).strip()
            report = self.database.row("SELECT title, parsed_path FROM reports WHERE id=?", (report_id,))
            if not report or not report.get("parsed_path") or not Path(report["parsed_path"]).exists():
                return self._json({"error": "parsed report not found"}, 404)
            parsed_report = json.loads(Path(report["parsed_path"]).read_text(encoding="utf-8"))
            sections = parsed_report.get("sections", [])
            if not 0 <= section_index < len(sections):
                return self._json({"error": "section not found"}, 404)
            section = sections[section_index]
            try:
                result = self.ai_service.assist(
                    task=task,
                    source_text=section.get("text", ""),
                    selected_text=selected_text,
                    report_title=report["title"],
                    section_title=section.get("title", "Document"),
                    first_page=int(section.get("first_page", 1)),
                    last_page=int(section.get("last_page", 1)),
                )
            except ValueError as error:
                return self._json({"error": str(error)}, 400)
            except AIUnavailable as error:
                return self._json({"error": str(error)}, 503)
            return self._json(result)
        if path != "/api/scan":
            return self._json({"error": "not found"}, 404)
        if not self._admin_authorized():
            return self._json({"error": "admin authorization required"}, 401)
        if not self.scan_lock.acquire(blocking=False):
            return self._json({"error": "scan already running"}, 409)
        try:
            result = self.monitor.scan(self.sources, download=True, max_downloads=MAX_SCAN_DOWNLOADS)
            return self._json(result)
        finally:
            self.scan_lock.release()

    def do_PUT(self) -> None:
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        profile_id = self._authenticated_profile(path, "/api/preferences/")
        if not profile_id:
            return self._json({"error": "unauthorized"}, 401)
        payload = self._read_json()
        if payload is None:
            return self._json({"error": "invalid JSON body"}, 400)
        models = payload.get("models")
        sources = payload.get("sources")
        custom_models = payload.get("customModels", [])
        custom_sources = payload.get("customSources", [])
        if not isinstance(models, list) or not isinstance(sources, list) or not isinstance(custom_models, list) or not isinstance(custom_sources, list):
            return self._json({"error": "invalid preference lists"}, 400)
        if not models and not custom_models:
            return self._json({"error": "at least one model is required"}, 400)
        if not sources and not custom_sources:
            return self._json({"error": "at least one source is required"}, 400)
        if any(not isinstance(item, str) or item not in self.allowed_models for item in models):
            return self._json({"error": "unsupported model"}, 400)
        if any(not isinstance(item, str) or item not in self.allowed_preference_sources for item in sources):
            return self._json({"error": "unsupported source"}, 400)
        cleaned_models = []
        for item in custom_models[:20]:
            if not isinstance(item, dict):
                return self._json({"error": "invalid custom model"}, 400)
            name = str(item.get("name", "")).strip()[:80]
            provider = str(item.get("provider", "")).strip()[:80]
            if not name:
                return self._json({"error": "custom model name is required"}, 400)
            cleaned_models.append({"name": name, "provider": provider or "自定义厂商"})
        cleaned_sources = []
        for item in custom_sources[:20]:
            if not isinstance(item, dict):
                return self._json({"error": "invalid custom source"}, 400)
            name = str(item.get("name", "")).strip()[:80]
            url = str(item.get("url", "")).strip()[:500]
            parsed_url = urllib.parse.urlparse(url)
            if not name or parsed_url.scheme != "https" or not parsed_url.hostname:
                return self._json({"error": "custom source requires a name and HTTPS URL"}, 400)
            cleaned_sources.append({"name": name, "url": url, "status": "pending_verification"})
        preference = self.database.save_user_preferences(
            profile_id,
            list(dict.fromkeys(models)),
            list(dict.fromkeys(sources)),
            cleaned_models,
            cleaned_sources,
        )
        return self._json(preference)


def scheduler_loop(monitor: Monitor, sources, interval_seconds: int, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            monitor.scan(sources, download=True, max_downloads=10)
        except Exception as error:
            print(f"[frontierlens] scheduled scan failed: {error}")
        if stop_event.wait(interval_seconds):
            break


def serve(host: str = "127.0.0.1", port: int = 4173, interval_seconds: int = 300) -> None:
    validate_runtime_config()
    database = Database()
    database.initialize()
    sources = load_sources()
    database.sync_sources(sources)
    database.rebuild_release_index(CATALOG_VERSION)
    monitor = Monitor(database)
    FrontierLensHandler.database = database
    FrontierLensHandler.monitor = monitor
    FrontierLensHandler.ai_service = AIService()
    FrontierLensHandler.knowledge_service = KnowledgeService(database)
    FrontierLensHandler.knowledge_service.seed_catalog()
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
