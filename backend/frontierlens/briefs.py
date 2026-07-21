from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .database import Database, utc_now


SIGNALS = (
    ("Architecture", ("architecture", "mixture-of-experts", "mixture of experts", "moe", "attention", "transformer")),
    ("Reasoning", ("reasoning", "thinking", "reinforcement learning", "rlhf", "grpo", "reward")),
    ("Context", ("context window", "long context", "token context", "context length")),
    ("Multimodal", ("multimodal", "vision", "image", "audio", "video", "speech")),
    ("Efficiency", ("efficiency", "latency", "throughput", "inference cost", "memory", "sparse")),
    ("Coding & Agents", ("coding", "software engineering", "agent", "tool use", "function calling")),
    ("Safety", ("safety", "risk", "alignment", "harm", "red team")),
)

PRODUCT_PROMPTS = {
    "Architecture": "核对部署复杂度、推理框架兼容性与单位请求成本。",
    "Reasoning": "重点验证复杂任务质量，同时测量延迟、token 消耗和可控性。",
    "Context": "用真实长文档或长周期 Agent 任务验证有效上下文，而不只看标称长度。",
    "Multimodal": "评估新的输入输出形态是否能简化现有产品工作流。",
    "Efficiency": "把官方效率结论转化为真实并发、延迟和成本测试。",
    "Coding & Agents": "优先使用真实代码库、工具调用和长链路任务做产品评测。",
    "Safety": "在上线前核对能力边界、滥用风险和产品侧防护要求。",
}

GENERATION_METHOD = "official_evidence_extraction_v2"
CLAIM_CUES = (
    "we present", "we introduce", "we propose", "we train", "we develop",
    "we demonstrate", "we achieve", "we find", "our model", "our approach",
    "enables", "improves", "reduces", "supports", "outperforms", "built upon",
)


def _sentences(text: str) -> list[str]:
    cleaned = " ".join(text.replace("\x00", " ").split())
    return [item.strip() for item in re.split(r"(?<=[.!?。！？])\s+", cleaned) if 45 <= len(item.strip()) <= 420]


def _quality_score(sentence: str, section_title: str) -> int | None:
    """Reject PDF extraction noise and rank explicit author claims above background prose."""
    lowered = sentence.lower()
    if any(marker in lowered for marker in ("<think>", "<act>", " q:", " a:", "references")):
        return None
    if lowered.count("et al.") >= 2 or sentence.count("…") >= 2:
        return None
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", sentence)
    if not 8 <= len(words) <= 75 or any(len(word) > 38 for word in words):
        return None
    score = 0
    normalized_title = section_title.strip().lower()
    if normalized_title == "abstract":
        score += 5
    elif normalized_title in {"introduction", "conclusion", "conclusions"}:
        score += 3
    if any(cue in lowered for cue in CLAIM_CUES):
        score += 4
    if re.search(r"\b\d+(?:\.\d+)?(?:%|[bmk])?\b", lowered):
        score += 1
    if sentence.startswith(("We ", "Our ", "This work", "In this work")):
        score += 2
    return score


def _fingerprint(documents: list[dict[str, Any]]) -> str:
    raw = "|".join(f"{item['id']}:{item.get('updated_at') or ''}:{item.get('content_hash') or ''}" for item in documents)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class BriefBuilder:
    """Build conservative release briefs from locally archived official evidence."""

    def __init__(self, database: Database):
        self.database = database

    def build_all(self) -> dict[str, int]:
        built = skipped = 0
        releases = self.database.rows("SELECT id, name FROM model_releases ORDER BY id")
        for release in releases:
            if self.build_release(int(release["id"]), release["name"]):
                built += 1
            else:
                skipped += 1
        return {"built": built, "skipped": skipped}

    def build_release(self, release_id: int, release_name: str | None = None) -> bool:
        documents = self.database.rows(
            """SELECT p.id, p.title, p.report_type, p.parsed_path, p.page_count,
                p.updated_at, p.content_hash, d.is_primary, d.evidence_weight
            FROM release_documents d JOIN reports p ON p.id=d.report_id
            WHERE d.release_id=? ORDER BY d.is_primary DESC, d.evidence_weight DESC, p.id DESC""",
            (release_id,),
        )
        if not documents:
            return False
        fingerprint = _fingerprint(documents)
        existing = self.database.row(
            "SELECT evidence_fingerprint, generation_method FROM release_briefs WHERE release_id=?",
            (release_id,),
        )
        if (
            existing
            and existing["evidence_fingerprint"] == fingerprint
            and existing["generation_method"] == GENERATION_METHOD
        ):
            return False
        if not release_name:
            row = self.database.row("SELECT name FROM model_releases WHERE id=?", (release_id,))
            release_name = row["name"] if row else "Model release"

        candidates: list[dict[str, Any]] = []
        for document in documents:
            parsed_path = document.get("parsed_path")
            if not parsed_path or not Path(parsed_path).exists():
                continue
            try:
                payload = json.loads(Path(parsed_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            sections = payload.get("sections", [])
            preferred = sorted(
                sections,
                key=lambda section: 0 if str(section.get("title", "")).lower() in {"abstract", "introduction", "conclusion", "conclusions"} else 1,
            )
            for section in preferred[:8]:
                section_title = str(section.get("title", ""))
                for sentence in _sentences(str(section.get("text", ""))):
                    quality_score = _quality_score(sentence, section_title)
                    if quality_score is None:
                        continue
                    lowered = sentence.lower()
                    for label, terms in SIGNALS:
                        if any(term in lowered for term in terms):
                            candidates.append({
                                "label": label,
                                "text": sentence[:360],
                                "reportId": document["id"],
                                "reportTitle": document["title"],
                                "firstPage": int(section.get("first_page", 1)),
                                "lastPage": int(section.get("last_page", section.get("first_page", 1))),
                                "qualityScore": quality_score,
                            })
                            break

        highlights: list[dict[str, Any]] = []
        used_labels: set[str] = set()
        used_text: set[str] = set()
        candidates.sort(key=lambda item: item["qualityScore"], reverse=True)
        for candidate in candidates:
            normalized = re.sub(r"\W+", " ", candidate["text"].lower())[:160]
            if candidate["label"] in used_labels or normalized in used_text:
                continue
            highlights.append(candidate)
            highlights[-1].pop("qualityScore", None)
            used_labels.add(candidate["label"])
            used_text.add(normalized)
            if len(highlights) == 4:
                break

        types = list(dict.fromkeys(item["report_type"] for item in documents))
        has_report = "technical_report" in types
        parsed_count = sum(bool(item.get("parsed_path")) for item in documents)
        summary = (
            f"{release_name} 已归档 {len(documents)} 份官方证据，其中 {parsed_count} 份可结构化阅读。"
            + ("以下变化直接摘自官方 Tech Report，可按页码回到原文核验。" if has_report else "当前尚无 Tech Report，以下内容仅依据现有官方资料。")
        )
        implications = [
            {"label": item["label"], "text": PRODUCT_PROMPTS[item["label"]]}
            for item in highlights if item["label"] in PRODUCT_PROMPTS
        ][:3]
        now = utc_now()
        self.database.upsert_release_brief(
            release_id=release_id,
            summary=summary,
            highlights=highlights,
            product_implications=implications,
            evidence_ids=[int(item["id"]) for item in documents],
            evidence_fingerprint=fingerprint,
            generation_method=GENERATION_METHOD,
            status="ready" if highlights else "evidence_only",
            generated_at=now,
        )
        return True
