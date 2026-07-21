from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .database import Database, utc_now


CONCEPTS: tuple[dict[str, Any], ...] = (
    {
        "id": "transformer",
        "name": "Transformer",
        "aliases": ["transformer architecture", "transformers"],
        "one_liner": "一种让每个 token 根据上下文关注其他 token，并逐层形成表示的模型架构。",
        "why": "序列中的信息并不独立。Transformer 用注意力并行建模远距离关系，成为现代大模型的通用底座。",
        "analogy": "像一场圆桌讨论：每位参与者都能先听取其他人的发言，再更新自己的判断。",
        "impact": "它决定模型可扩展性、上下文处理方式，以及多数后续优化可以插入的位置。",
        "role": "prerequisite", "priority": 90,
    },
    {
        "id": "attention",
        "name": "Attention",
        "aliases": ["attention mechanism", "self-attention", "self attention"],
        "one_liner": "让模型为当前 token 动态选择上下文中更值得关注的信息。",
        "why": "不同上下文片段的重要程度不同，固定压缩会丢失关键关系。",
        "analogy": "像阅读长合同：看到一个代词时，会回看与它最相关的定义条款。",
        "impact": "注意力效率直接影响长上下文、延迟和可承载的输入规模。",
        "role": "mechanism", "priority": 70,
    },
    {
        "id": "mixture-of-experts",
        "name": "Mixture-of-Experts",
        "aliases": ["mixture of experts", "mixture-of-experts", "moe", "sparse moe"],
        "one_liner": "模型拥有许多专家网络，但每个 token 只激活最合适的一小部分。",
        "why": "Dense 模型扩大容量时，每次推理都要调用全部参数；MoE 用稀疏激活控制单次计算量。",
        "analogy": "像综合医院先分诊，再让最相关的几位医生接诊，而不是全院同时会诊。",
        "impact": "产品可获得更大模型容量，但必须评估路由、显存、吞吐和部署复杂度。",
        "role": "core_change", "priority": 10,
    },
    {
        "id": "dense-model",
        "name": "Dense Model",
        "aliases": ["dense model", "dense models", "dense transformer"],
        "one_liner": "每次处理 token 时，模型主体的全部参数都会参与计算。",
        "why": "全参数激活结构更直接，训练和服务行为通常更稳定、容易预测。",
        "analogy": "像每个项目都由同一支完整团队共同处理。",
        "impact": "选型更简单，但参数规模增长会直接推高每次调用成本。",
        "role": "mechanism", "priority": 30,
    },
    {
        "id": "sparse-activation",
        "name": "Sparse Activation",
        "aliases": ["sparse activation", "sparsely activated", "sparse model"],
        "one_liner": "一次计算只启用模型中的部分组件，而不是让全部组件同时工作。",
        "why": "总容量与单次计算成本不必同步增长。",
        "analogy": "像排班制度：公司拥有很多员工，但每个班次只安排需要的人。",
        "impact": "可降低活跃计算量，但会增加调度和负载均衡要求。",
        "role": "mechanism", "priority": 35,
    },
    {
        "id": "expert-routing",
        "name": "Expert Routing",
        "aliases": ["expert routing", "router", "routing network", "routing mechanism"],
        "one_liner": "为每个 token 选择应该由哪些专家网络处理的机制。",
        "why": "MoE 的收益取决于是否把任务分给合适的专家并避免少数专家过载。",
        "analogy": "像医院导诊台：判断病情后分配科室，同时避免某个门诊挤爆。",
        "impact": "路由质量会影响模型效果、吞吐稳定性和集群利用率。",
        "role": "mechanism", "priority": 40,
    },
    {
        "id": "thinking-mode",
        "name": "Thinking Mode",
        "aliases": ["thinking mode", "thinking-mode", "reasoning mode", "non-thinking mode"],
        "one_liner": "让同一模型按任务选择深入推理或快速回答的工作模式。",
        "why": "复杂问题需要更多计算，日常问题则更在意响应速度和成本。",
        "analogy": "像相机同时提供自动模式和专业模式：日常快速拍，复杂场景再精细控制。",
        "impact": "产品可用一个模型入口覆盖快答与深度任务，但需要设计清晰的模式策略。",
        "role": "core_change", "priority": 8,
    },
    {
        "id": "thinking-budget",
        "name": "Thinking Budget",
        "aliases": ["thinking budget", "reasoning budget", "test-time compute", "test time compute"],
        "one_liner": "控制模型在回答前最多投入多少推理计算。",
        "why": "推理投入越多，通常延迟和成本越高，且简单任务不一定因此受益。",
        "analogy": "像为不同考题分配答题时间：选择题快速作答，压轴题留更多草稿时间。",
        "impact": "质量、延迟和成本从模型差异变成可配置的产品参数。",
        "role": "core_change", "priority": 12,
    },
    {
        "id": "reinforcement-learning",
        "name": "Reinforcement Learning",
        "aliases": ["reinforcement learning", "general rl", "rl training"],
        "one_liner": "模型根据奖励信号学习哪些行为更能完成目标。",
        "why": "仅模仿训练数据不能直接优化正确性、工具使用或复杂任务结果。",
        "analogy": "像通过反复练习和得分反馈调整解题策略，而不只是背标准答案。",
        "impact": "可提升推理与 Agent 行为，但奖励设计会决定模型真正学会什么。",
        "role": "mechanism", "priority": 25,
    },
    {
        "id": "rlhf",
        "name": "RLHF",
        "aliases": ["rlhf", "reinforcement learning from human feedback"],
        "one_liner": "利用人类偏好反馈形成奖励，再用强化学习调整模型行为。",
        "why": "语言模型需要把“更有帮助、更安全、更符合偏好”转化为可优化信号。",
        "analogy": "像老师不仅给标准答案，还持续评价哪种表达和解题方式更好。",
        "impact": "影响产品语气与对齐表现，同时带来反馈成本和奖励偏差风险。",
        "role": "mechanism", "priority": 45,
    },
    {
        "id": "grpo",
        "name": "GRPO",
        "aliases": ["grpo", "group relative policy optimization"],
        "one_liner": "通过比较同一问题的一组候选答案来估计相对优势的强化学习方法。",
        "why": "减少对独立价值模型的依赖，并让可验证任务的相对好坏更容易用于训练。",
        "analogy": "像不先规定绝对分数，而是在同组作品中比较谁做得更好。",
        "impact": "可能降低推理训练复杂度，但结果仍高度依赖奖励与采样设计。",
        "role": "mechanism", "priority": 35,
    },
    {
        "id": "long-context",
        "name": "Long Context",
        "aliases": ["long context", "long-context", "context window", "1m context", "128k context"],
        "one_liner": "模型能在一次任务中接收并利用更长的输入内容。",
        "why": "代码库、长文档和长期 Agent 任务常常超出普通上下文窗口。",
        "analogy": "像把整本项目档案放在桌上，而不是每次只递一页。",
        "impact": "可减少切分与检索，但标称长度不等于信息能被可靠利用。",
        "role": "core_change", "priority": 18,
    },
    {
        "id": "kv-cache",
        "name": "KV Cache",
        "aliases": ["kv cache", "key-value cache", "key value cache"],
        "one_liner": "保存已读 token 的注意力中间结果，生成新 token 时避免重复计算。",
        "why": "自回归生成会反复访问旧上下文，全部重算会浪费大量时间。",
        "analogy": "像会议秘书保留前文笔记，新讨论只补增量内容。",
        "impact": "直接影响长对话的显存占用、吞吐和服务成本。",
        "role": "prerequisite", "priority": 75,
    },
    {
        "id": "speculative-decoding",
        "name": "Speculative Decoding",
        "aliases": ["speculative decoding", "speculative decode", "draft model"],
        "one_liner": "先由较快方法批量猜测 token，再由主模型一次验证。",
        "why": "逐 token 等待主模型计算会限制生成速度。",
        "analogy": "像助理先起草几句，负责人一次审阅并接受正确部分。",
        "impact": "可降低交互等待，但收益取决于猜测命中率和服务实现。",
        "role": "mechanism", "priority": 30,
    },
    {
        "id": "multimodal",
        "name": "Multimodal Model",
        "aliases": ["multimodal", "multi-modal", "vision-language", "native vision"],
        "one_liner": "在同一模型中理解或生成文本、图像、音频等多种信息。",
        "why": "真实工作流并不只包含文本，跨模态信息需要在共同语境中推理。",
        "analogy": "像一个人既能读邮件，也能看图表、听录音并综合判断。",
        "impact": "可减少多模型拼接，但要重新验证输入质量、延迟和安全边界。",
        "role": "core_change", "priority": 20,
    },
    {
        "id": "agentic-coding",
        "name": "Agentic Coding",
        "aliases": ["agentic coding", "coding agent", "software engineering agent"],
        "one_liner": "模型不只补全代码，而是规划、使用工具、修改项目并验证结果。",
        "why": "真实软件任务需要跨文件、跨工具和多轮反馈，单次代码生成无法完成闭环。",
        "analogy": "像从代码助手升级为能接任务、动手修改并跑测试的工程搭档。",
        "impact": "产品价值从内容生成转向任务交付，同时放大权限、可靠性和可观测性要求。",
        "role": "capability", "priority": 15,
    },
)


RELATIONSHIPS: tuple[tuple[str, str, str, str], ...] = (
    ("attention", "transformer", "prerequisite", "Attention is a core mechanism inside Transformer models."),
    ("mixture-of-experts", "transformer", "prerequisite", "MoE commonly replaces or augments Transformer feed-forward blocks."),
    ("mixture-of-experts", "sparse-activation", "related", "MoE achieves efficiency through sparse expert activation."),
    ("mixture-of-experts", "expert-routing", "prerequisite", "A router selects the experts used for each token."),
    ("mixture-of-experts", "dense-model", "contrasts_with", "Dense models activate all main parameters for each token."),
    ("thinking-budget", "thinking-mode", "related", "A budget controls how much compute a reasoning mode may use."),
    ("thinking-mode", "reinforcement-learning", "related", "Post-training teaches when and how to use reasoning behavior."),
    ("rlhf", "reinforcement-learning", "prerequisite", "RLHF is one way to supply reward feedback for RL."),
    ("grpo", "reinforcement-learning", "prerequisite", "GRPO is a policy-optimization method used in RL training."),
    ("long-context", "attention", "prerequisite", "Long-context cost and quality depend heavily on attention."),
    ("long-context", "kv-cache", "related", "Longer contexts increase KV-cache memory pressure during generation."),
    ("speculative-decoding", "kv-cache", "related", "Verified draft tokens must integrate with the target model's cached state."),
    ("agentic-coding", "long-context", "enables_capability", "Long context helps agents operate across larger repositories and histories."),
    ("agentic-coding", "thinking-budget", "related", "Long-horizon coding tasks benefit from controllable reasoning investment."),
    ("multimodal", "attention", "prerequisite", "Cross-modal information is connected through attention-based representations."),
)


class KnowledgeService:
    def __init__(self, database: Database):
        self.database = database

    def seed_catalog(self) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            for concept in CONCEPTS:
                aliases = list(dict.fromkeys([concept["name"], *concept["aliases"]]))
                connection.execute(
                    """INSERT INTO concepts(id, name, aliases, one_liner, why_it_exists, analogy,
                    product_impact, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET name=excluded.name, aliases=excluded.aliases,
                    one_liner=excluded.one_liner, why_it_exists=excluded.why_it_exists,
                    analogy=excluded.analogy, product_impact=excluded.product_impact,
                    updated_at=excluded.updated_at""",
                    (
                        concept["id"], concept["name"], json.dumps(aliases, ensure_ascii=False),
                        concept["one_liner"], concept["why"], concept["analogy"], concept["impact"], now, now,
                    ),
                )
            for source, target, relationship_type, explanation in RELATIONSHIPS:
                connection.execute(
                    """INSERT INTO concept_relationships(source_concept_id, target_concept_id,
                    relationship_type, explanation, evidence_state, created_at)
                    VALUES (?, ?, ?, ?, 'background', ?)
                    ON CONFLICT(source_concept_id, target_concept_id, relationship_type)
                    DO UPDATE SET explanation=excluded.explanation""",
                    (source, target, relationship_type, explanation, now),
                )

    @staticmethod
    def _contains_alias(text: str, aliases: list[str]) -> str | None:
        normalized = re.sub(r"[-_]+", " ", text.lower())
        for alias in sorted(aliases, key=len, reverse=True):
            candidate = re.sub(r"[-_]+", " ", alias.lower()).strip()
            if len(candidate) <= 3:
                if re.search(rf"(?<![a-z0-9]){re.escape(candidate)}(?![a-z0-9])", normalized):
                    return alias
            elif candidate in normalized:
                return alias
        return None

    @staticmethod
    def _meaningful_match(concept_id: str, text: str) -> bool:
        normalized = re.sub(r"[-_]+", " ", " ".join(text.lower().split()))
        if concept_id == "multimodal":
            return bool(re.search(r"(?:multimodal|multi modal) (?:model|capabil|input|understand|reason)|vision language model|native vision", normalized))
        if concept_id == "agentic-coding":
            return bool(re.search(r"agentic coding|coding agent|software engineering agent", normalized))
        return True

    @staticmethod
    def _context_summary(text: str, alias: str, fallback: str) -> str:
        sentences = re.split(r"(?<=[.!?。！？])\s+", " ".join(text.split()))
        match = next((sentence for sentence in sentences if alias.lower().replace("-", " ") in sentence.lower().replace("-", " ")), "")
        if not match:
            return fallback
        return match[:260].strip()

    def index_release(self, release_id: int) -> dict[str, Any] | None:
        self.seed_catalog()
        release = self.database.row("SELECT id, slug, name FROM model_releases WHERE id=?", (release_id,))
        if not release:
            return None
        documents = self.database.rows(
            """SELECT p.id, p.title, p.report_type, p.parsed_path, p.parse_status, p.file_path
            FROM release_documents d JOIN reports p ON p.id=d.report_id
            WHERE d.release_id=? ORDER BY d.is_primary DESC, d.evidence_weight DESC, p.id DESC""",
            (release_id,),
        )
        sections: list[dict[str, Any]] = []
        for document in documents:
            parsed_path = document.get("parsed_path")
            if document.get("parse_status") != "parsed" or not parsed_path or not Path(parsed_path).exists():
                continue
            try:
                parsed = json.loads(Path(parsed_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for section in parsed.get("sections", []):
                sections.append({**section, "report_id": document["id"], "report_title": document["title"]})

        brief = self.database.row("SELECT summary, highlights, product_implications FROM release_briefs WHERE release_id=?", (release_id,))
        brief_text = ""
        if brief:
            parts = [brief.get("summary") or ""]
            for field in ("highlights", "product_implications"):
                try:
                    parts.extend(item.get("text", "") for item in json.loads(brief.get(field) or "[]"))
                except json.JSONDecodeError:
                    pass
            brief_text = " ".join(parts)

        now = utc_now()
        matches: list[tuple[dict[str, Any], dict[str, Any] | None, str, str]] = []
        for concept in CONCEPTS:
            aliases = [concept["name"], *concept["aliases"]]
            section_match = next(
                ((section, alias) for section in sections
                 if self._meaningful_match(concept["id"], section.get("text", ""))
                 and (alias := self._contains_alias(section.get("text", ""), aliases))),
                None,
            )
            if section_match:
                section, alias = section_match
                context = self._context_summary(section.get("text", ""), alias, concept["one_liner"])
                matches.append((concept, section, "supported", context))
                continue
            alias = self._contains_alias(brief_text, aliases) if brief_text and self._meaningful_match(concept["id"], brief_text) else None
            if alias:
                matches.append((concept, None, "inferred", self._context_summary(brief_text, alias, concept["one_liner"])))

        with self.database.connect() as connection:
            connection.execute("DELETE FROM concept_evidence WHERE release_id=?", (release_id,))
            connection.execute("DELETE FROM release_concepts WHERE release_id=?", (release_id,))
            for concept, section, evidence_state, context in matches:
                connection.execute(
                    """INSERT INTO release_concepts(release_id, concept_id, role, priority,
                    evidence_state, context_summary, indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (release_id, concept["id"], concept["role"], concept["priority"], evidence_state, context, now),
                )
                if section:
                    connection.execute(
                        """INSERT INTO concept_evidence(release_id, concept_id, report_id, first_page,
                        last_page, quote_hint, evidence_state, created_at) VALUES (?, ?, ?, ?, ?, ?, 'supported', ?)""",
                        (
                            release_id, concept["id"], section["report_id"], section.get("first_page"),
                            section.get("last_page"), section.get("title", ""), now,
                        ),
                    )
        return {"releaseId": release_id, "matched": len(matches), "supported": sum(1 for item in matches if item[2] == "supported")}

    def _relationships(self, concept_id: str) -> list[dict[str, Any]]:
        rows = self.database.rows(
            """SELECT r.target_concept_id AS id, c.name, r.relationship_type, r.explanation,
                r.evidence_state
            FROM concept_relationships r JOIN concepts c ON c.id=r.target_concept_id
            WHERE r.source_concept_id=? ORDER BY r.relationship_type, c.name""",
            (concept_id,),
        )
        return [
            {
                "id": row["id"], "name": row["name"], "type": row["relationship_type"],
                "explanation": row["explanation"], "evidenceState": row["evidence_state"],
            }
            for row in rows
        ]

    def _evidence(self, release_id: int, concept_id: str) -> list[dict[str, Any]]:
        rows = self.database.rows(
            """SELECT e.report_id, p.title, p.url, p.parse_status, p.file_path, e.first_page,
                e.last_page, e.quote_hint, e.evidence_state
            FROM concept_evidence e JOIN reports p ON p.id=e.report_id
            WHERE e.release_id=? AND e.concept_id=? ORDER BY e.report_id DESC""",
            (release_id, concept_id),
        )
        return [
            {
                "reportId": row["report_id"], "title": row["title"], "url": row["url"],
                "firstPage": row["first_page"], "lastPage": row["last_page"],
                "section": row["quote_hint"],
                "evidenceState": "unavailable" if row["file_path"] and not Path(row["file_path"]).exists() else row["evidence_state"],
                "readable": row["parse_status"] == "parsed",
            }
            for row in rows
        ]

    def release_graph(self, release_id: int) -> dict[str, Any] | None:
        indexed = self.index_release(release_id)
        if indexed is None:
            return None
        release = self.database.row("SELECT id, slug, name FROM model_releases WHERE id=?", (release_id,))
        rows = self.database.rows(
            """SELECT rc.concept_id AS id, c.name, c.aliases, c.one_liner, c.why_it_exists,
                c.analogy, c.product_impact, rc.role, rc.priority, rc.evidence_state,
                rc.context_summary
            FROM release_concepts rc JOIN concepts c ON c.id=rc.concept_id
            WHERE rc.release_id=? ORDER BY rc.priority, c.name LIMIT 6""",
            (release_id,),
        )
        concepts = []
        for row in rows:
            concepts.append({
                "id": row["id"], "name": row["name"], "aliases": json.loads(row["aliases"]),
                "oneLiner": row["one_liner"], "why": row["why_it_exists"], "analogy": row["analogy"],
                "productImpact": row["product_impact"], "role": row["role"], "priority": row["priority"],
                "evidenceState": row["evidence_state"], "contextSummary": row["context_summary"],
                "relationships": self._relationships(row["id"]),
                "evidence": self._evidence(release_id, row["id"]),
            })
        supported = sum(1 for concept in concepts if concept["evidenceState"] == "supported")
        return {
            "releaseId": release_id, "releaseSlug": release["slug"], "releaseName": release["name"],
            "status": "ready" if supported else ("limited" if concepts else "pending"),
            "primaryConcepts": concepts,
            "principle": "Evidence is authoritative. Understanding is generated.",
        }

    def concept(self, identifier: str, release_id: int | None = None) -> dict[str, Any] | None:
        self.seed_catalog()
        normalized = identifier.strip().lower()
        row = self.database.row("SELECT * FROM concepts WHERE id=?", (normalized,))
        if not row:
            for candidate in self.database.rows("SELECT * FROM concepts ORDER BY name"):
                aliases = [candidate["name"], *json.loads(candidate["aliases"])]
                if normalized in {alias.lower() for alias in aliases}:
                    row = candidate
                    break
        if not row:
            return None
        evidence = self._evidence(release_id, row["id"]) if release_id is not None else []
        return {
            "id": row["id"], "name": row["name"], "aliases": json.loads(row["aliases"]),
            "oneLiner": row["one_liner"], "why": row["why_it_exists"], "analogy": row["analogy"],
            "productImpact": row["product_impact"], "relationships": self._relationships(row["id"]),
            "evidence": evidence,
            "evidenceState": "supported" if evidence else "background",
        }
