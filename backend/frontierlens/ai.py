from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from .config import AI_API_KEY, AI_BASE_URL, AI_MODEL, REQUEST_TIMEOUT_SECONDS


TASKS = {
    "summarize": "用中文说明这一节在回答什么，并给出不超过三条重点。",
    "translate": "将原文忠实翻译为清晰中文，不补充原文没有的信息。",
    "explain": "用适合 AI 产品经理的中文解释所选术语：一句话定义、通俗类比、为什么重要。",
}


class AIUnavailable(RuntimeError):
    pass


class AIService:
    @property
    def available(self) -> bool:
        return bool(AI_API_KEY and AI_MODEL)

    def assist(
        self,
        *,
        task: str,
        source_text: str,
        selected_text: str,
        report_title: str,
        section_title: str,
        first_page: int,
        last_page: int,
    ) -> dict:
        if task not in TASKS:
            raise ValueError("unsupported AI task")
        if not self.available:
            raise AIUnavailable("AI assistance is not configured")
        source_text = source_text[:24_000]
        selected_text = selected_text[:500]
        instructions = (
            "你是 FrontierLens 的证据型阅读助手，核心用户是 AI 产品经理。"
            "只能根据所给官方报告原文回答；原文未说明时必须明确说‘本节原文未说明’，不得补充外部事实。"
            "回答应简洁、通俗，并区分原文事实与解释。"
            "只输出 JSON，格式为："
            '{"answer":"...","key_points":["..."],"why_it_matters":"..."}'
        )
        user_input = (
            f"任务：{TASKS[task]}\n"
            f"报告：{report_title}\n章节：{section_title}\n页码：{first_page}-{last_page}\n"
            f"所选文本：{selected_text or '无'}\n\n官方原文：\n{source_text}"
        )
        body = json.dumps({
            "model": AI_MODEL,
            "instructions": instructions,
            "input": user_input,
            "max_output_tokens": 900,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{AI_BASE_URL}/responses",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read(1000).decode("utf-8", errors="replace")
            raise AIUnavailable(f"AI provider returned HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise AIUnavailable("AI provider is temporarily unavailable") from error

        text = payload.get("output_text", "")
        if not text:
            text = "".join(
                item.get("text", "")
                for output in payload.get("output", [])
                for item in output.get("content", [])
                if item.get("type") == "output_text"
            )
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            result = {"answer": cleaned, "key_points": [], "why_it_matters": ""}
        return {
            "task": task,
            "answer": str(result.get("answer", "")).strip(),
            "keyPoints": [str(item) for item in result.get("key_points", [])[:3]],
            "whyItMatters": str(result.get("why_it_matters", "")).strip(),
            "citation": {
                "reportTitle": report_title,
                "sectionTitle": section_title,
                "firstPage": first_page,
                "lastPage": last_page,
            },
            "model": AI_MODEL,
        }
