from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

CATALOG_VERSION = "2026-07-20.16"

URL_ALIASES = {
    # The repository PDF and arXiv entry are the same MiniMax-M1 report.
    "https://github.com/MiniMax-AI/MiniMax-M1/blob/main/MiniMax_M1_tech_report.pdf":
        "https://arxiv.org/abs/2506.13585",
}

# Corrections backed by the publisher's own repository or publication index.
# These are deliberately narrow: the scanner may discover a generic "Research
# Paper" anchor, but it must never inflate that into a Tech Report.
EVIDENCE_OVERRIDES = {
    "https://arxiv.org/abs/2512.15603": {
        "title": "Qwen-Image-Layered: Towards Inherent Editability via Layer Decomposition",
        "report_type": "research_report",
    },
    "https://storage.googleapis.com/deepmind-media/gemini/gemini_v1_5_report.pdf": {
        "title": "Gemini 1.5 Technical Report",
        "report_type": "technical_report",
    },
    "https://storage.googleapis.com/deepmind-media/gemini-robotics/Gemini-Robotics-1-5-Tech-Report.pdf": {
        "title": "Gemini Robotics 1.5 Technical Report",
        "report_type": "technical_report",
    },
}


@dataclass(frozen=True)
class ReleaseIdentity:
    family_id: str
    family_name: str
    provider: str
    release_slug: str
    release_name: str


FAMILIES = {
    "OpenAI": ("gpt", "GPT"),
    "Anthropic": ("claude", "Claude"),
    "Google DeepMind": ("gemini", "Gemini"),
    "Qwen": ("qwen", "Qwen"),
    "DeepSeek": ("deepseek", "DeepSeek"),
    "Moonshot AI": ("kimi", "Kimi"),
    "ByteDance Seed": ("seed", "Seed"),
    "Z.ai": ("glm", "GLM"),
    "MiniMax": ("minimax", "MiniMax"),
}

# Officially verified release metadata. Discovery remains automatic, while this
# small calibration layer prevents crawl timestamps or malformed page dates from
# being presented as model launch dates.
RELEASE_OVERRIDES = {
    "kimi-k3": {"name": "Kimi K3", "released_at": "2026-07-17T00:00:00+00:00"},
    "kimi-k2-6": {"name": "Kimi K2.6", "released_at": "2026-04-20T00:00:00+00:00"},
    "kimi-k2-5": {"name": "Kimi K2.5", "released_at": "2026-01-27T00:00:00+00:00"},
    "kimi-k2": {"name": "Kimi K2", "released_at": "2025-07-11T00:00:00+00:00"},
    "gpt-5-6": {"name": "GPT-5.6", "released_at": "2026-07-09T00:00:00+00:00"},
    "gpt-5-5-instant": {"name": "GPT-5.5 Instant", "released_at": "2026-05-05T00:00:00+00:00"},
    "claude-sonnet-5": {"name": "Claude Sonnet 5", "released_at": "2026-06-30T00:00:00+00:00"},
    "claude-fable-5": {"name": "Claude Fable 5", "released_at": "2026-06-09T00:00:00+00:00"},
    "claude-opus-4-8": {"name": "Claude Opus 4.8", "released_at": "2026-05-28T00:00:00+00:00"},
    "claude-opus-4-7": {"name": "Claude Opus 4.7", "released_at": "2026-04-16T00:00:00+00:00"},
    "claude-opus-4-6": {"name": "Claude Opus 4.6", "released_at": "2026-02-05T00:00:00+00:00"},
    "gemini-3-5-flash": {"name": "Gemini 3.5 Flash", "released_at": "2026-05-19T00:00:00+00:00"},
    "gemini-1": {"name": "Gemini 1", "released_at": "2023-12-06T00:00:00+00:00"},
    "gemini-1-5": {"name": "Gemini 1.5", "released_at": "2024-02-15T00:00:00+00:00"},
    "minimax-m3": {"name": "MiniMax M3", "released_at": "2026-06-01T00:00:00+00:00"},
    "glm-5-2": {"name": "GLM-5.2", "released_at": "2026-06-16T00:00:00+00:00"},
    "qwen3-6-max-preview": {"name": "Qwen3.6-Max-Preview", "released_at": "2026-04-18T00:00:00+00:00"},
    "qwen-vla": {"name": "Qwen-VLA", "released_at": "2026-05-29T00:00:00+00:00"},
    "qwen3-omni": {"name": "Qwen3-Omni", "released_at": "2025-09-21T00:00:00+00:00"},
    "deepseek-v4": {"name": "DeepSeek-V4", "released_at": "2026-04-24T00:00:00+00:00"},
    "deepseek-v3-2": {"name": "DeepSeek-V3.2", "released_at": "2025-12-01T00:00:00+00:00"},
    "seedream-5-0-pro": {"name": "Seedream 5.0 Pro", "released_at": "2026-07-08T00:00:00+00:00"},
    "seed2-1": {"name": "Seed2.1", "released_at": "2026-06-23T00:00:00+00:00"},
    "seed3d-2-0": {"name": "Seed3D 2.0", "released_at": "2026-04-23T00:00:00+00:00"},
    "seeduplex": {"name": "Seeduplex", "released_at": "2026-04-09T00:00:00+00:00"},
    "seed2-0": {"name": "Seed2.0", "released_at": "2026-02-14T00:00:00+00:00"},
    "seedream-5-0-lite": {"name": "Seedream 5.0 Lite", "released_at": "2026-02-13T00:00:00+00:00"},
    "seedance-2-0": {"name": "Seedance 2.0", "released_at": "2026-02-12T00:00:00+00:00"},
    "glm-5": {"name": "GLM-5", "released_at": "2026-02-12T00:00:00+00:00"},
}

# Official document URLs sometimes omit punctuation or append document names.
# Resolve those paths before the more permissive title/path parser runs, so one
# system card can never collapse Opus 4.6, 4.7 and 4.8 into a fake “Opus 4”.
PATH_RELEASE_ALIASES = {
    "claude-fable-5-mythos-5-system-card": "claude-fable-5",
    "claude-opus-4-8-system-card": "claude-opus-4-8",
    "claude-opus-4-7-system-card": "claude-opus-4-7",
    "claude-opus-4-6-system-card": "claude-opus-4-6",
}

RELEASE_NAME_OVERRIDES = {
    "gemini-3-1-flash-lite-image": "Gemini 3.1 Flash-Lite Image",
    "gemini-3-5-audio": "Gemini 3.5 Audio (Live Translate)",
    "gemini-3-1-flash-audio": "Gemini 3.1 Flash Audio",
    "gemini-3-1-flash-lite": "Gemini 3.1 Flash-Lite",
    "gemini-3-1-flash-image": "Gemini 3.1 Flash Image",
    "gemini-3-1-pro": "Gemini 3.1 Pro",
    "gemini-3-flash": "Gemini 3 Flash",
    "gemini-3-pro-image": "Gemini 3 Pro Image",
    "gemini-3-pro": "Gemini 3 Pro",
    "gemini-2-5-computer-use": "Gemini 2.5 Computer Use",
    "gemini-2-5-flash-lite": "Gemini 2.5 Flash-Lite",
    "gemini-2-5-flash": "Gemini 2.5 Flash",
    "gemini-2-5-deep-think": "Gemini 2.5 Deep Think",
    "gemini-2-5-pro": "Gemini 2.5 Pro",
    "gemini-2-0-flash": "Gemini 2.0 Flash",
    "gemini-2-0-flash-lite": "Gemini 2.0 Flash-Lite",
    "gemini-robotics-1-5": "Gemini Robotics 1.5",
}

RELEASE_PATTERNS = {
    "gpt": r"\b(?:gpt[-\s]?(?:oss|[0-9]+(?:\.[0-9]+)?(?:[-\s][a-z0-9]+)*))\b",
    "claude": r"\b(?:claude[-\s]?[0-9]+(?:\.[0-9]+)?(?:[-\s](?:opus|sonnet|haiku))?|(?:claude[-\s]?)?(?:opus|sonnet|haiku|fable|mythos)[-\s]?[0-9]+(?:\.[0-9]+)?)\b",
    "gemini": r"\bgemini(?:[-\s]robotics)?[-\s]?[0-9]+(?:\.[0-9]+)?(?:[-\s][a-z0-9]+)*\b",
    "qwen": r"\bqwen[-\s]?(?:[0-9]+(?:\.[0-9]+)?(?:[-\s][a-z0-9]+)*|(?:vla|image|omni|audio|tts|asr|robotnav|robotmanip)(?:[-\s][a-z0-9]+)*)\b",
    "deepseek": r"\bdeepseek[-\s]?(?:v|r)?[0-9]+(?:\.[0-9]+)?(?:[-\s][a-z0-9]+)*\b",
    "kimi": r"\bkimi[-\s]?[a-z]?[0-9]+(?:\.[0-9]+)?(?:[-\s][a-z0-9]+)*\b",
    "seed": r"\b(?:seeduplex|gr[-\s][0-9]+|ui[-\s]tars(?:[-\s][0-9]+)?|protenix[-\s]v?[0-9]+|seed(?:ream|ance|3d|[-\s]thinking)?[-\s]?(?:v)?[0-9]+(?:\.[0-9]+)*(?:[-\s][a-z0-9]+)*)\b",
    "glm": r"\bglm[-\s]?(?:[0-9]+(?:\.[0-9]+)*(?:[-\s][a-z0-9]+)*|ocr(?:[-\s][a-z0-9]+)*)\b",
    "minimax": r"\bminimax[-\s]?(?:[0-9]+|m[0-9]+(?:\.[0-9]+)?|(?:text|vl)[-\s]?[0-9]+)\b",
}

LAUNCH_PREFIXES = re.compile(r"^(?:introducing|previewing|announcing|meet|launching|release(?:d)?|new)\s+$", re.IGNORECASE)
NON_RELEASE_SUFFIX = re.compile(
    r"\s+(?:technical|tech|system|model|safety|official|report|card|repository|blog|paper|"
    r"tool\s+call|demo|toolkit|finetuning|fine\s+tuning|open\s+source|for\s+content|"
    r"advancing\b|visual\b|open\s+agentic\b|lowers\b|safe\s+completions\b).*$",
    re.IGNORECASE,
)
REJECT_CONTEXT_SUFFIX = re.compile(r"^\s+(?:lowers\b|for\s+content\b|safe\s+completions\b)", re.IGNORECASE)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:120]


def infer_release(provider: str, title: str, url: str) -> ReleaseIdentity | None:
    family = FAMILIES.get(provider)
    if not family:
        return None
    family_id, family_name = family
    clean_title = " ".join(title.replace("_", " ").split())
    clean_title = re.sub(
        r"^(?:technical|tech)\s+report\s*\(([^)]+)\)",
        r"\1 Technical Report",
        clean_title,
        flags=re.IGNORECASE,
    )
    # Some official indexes concatenate the release name and headline, e.g.
    # “Kimi K2.6Advancing…”. Restore the missing boundary before matching.
    clean_title = re.sub(r"(?<=\d)(?=[A-Z])", " ", clean_title)
    # Seed3D is a product name, not a concatenated headline boundary.
    clean_title = re.sub(r"\bSeed3\s+D\b", "Seed3D", clean_title, flags=re.IGNORECASE)
    if family_id == "gpt" and re.search(r"\b(?:lowers|safe\s+completions|for\s+content)\b", clean_title, re.IGNORECASE):
        return None
    parsed_path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    path_slug = slugify(parsed_path.rstrip("/").split("/")[-1])
    path_slug = re.sub(r"^(seedream|seedance)(?=\d)", r"\1-", path_slug)
    path_slug = {"seed2": "seed2-0"}.get(path_slug, path_slug)
    aliased_slug = PATH_RELEASE_ALIASES.get(path_slug)
    if aliased_slug:
        override = RELEASE_OVERRIDES[aliased_slug]
        return ReleaseIdentity(
            family_id=family_id,
            family_name=family_name,
            provider=provider,
            release_slug=aliased_slug,
            release_name=override["name"],
        )
    if path_slug in RELEASE_OVERRIDES:
        override = RELEASE_OVERRIDES[path_slug]
        return ReleaseIdentity(
            family_id=family_id,
            family_name=family_name,
            provider=provider,
            release_slug=path_slug,
            release_name=override["name"],
        )
    path = parsed_path.replace("-", " ")
    title_match = re.search(RELEASE_PATTERNS[family_id], clean_title, flags=re.IGNORECASE)
    if title_match:
        prefix = clean_title[:title_match.start()].strip(" :–—-·")
        if prefix and not LAUNCH_PREFIXES.match(f"{prefix} "):
            return None
        if REJECT_CONTEXT_SUFFIX.match(clean_title[title_match.end():]):
            return None
        match = title_match
        haystack = clean_title
    else:
        match = re.search(RELEASE_PATTERNS[family_id], path, flags=re.IGNORECASE)
        haystack = path
    if not match:
        return None
    raw_name = re.sub(r"(?i)(thinking)(open)", r"\1 \2", match.group(0))
    raw_name = " ".join(raw_name.replace("-", " ").split())
    raw_name = NON_RELEASE_SUFFIX.sub("", raw_name).strip()
    if not raw_name:
        return None
    if family_id == "claude" and not raw_name.lower().startswith("claude"):
        raw_name = f"Claude {raw_name}"
    release_name = re.sub(f"^{family_name}", family_name, raw_name, flags=re.IGNORECASE)
    release_slug = slugify(release_name)
    override = RELEASE_OVERRIDES.get(release_slug, {})
    release_name = override.get("name", RELEASE_NAME_OVERRIDES.get(release_slug, release_name))
    return ReleaseIdentity(
        family_id=family_id,
        family_name=family_name,
        provider=provider,
        release_slug=release_slug,
        release_name=release_name,
    )


def official_release_date(release_slug: str, discovered_date: str | None) -> str | None:
    override = RELEASE_OVERRIDES.get(release_slug)
    return override.get("released_at") if override else discovered_date


def release_date_basis(release_slug: str, report_types: set[str]) -> str:
    """Describe what the stored date actually proves; never overclaim a launch."""
    if release_slug in RELEASE_OVERRIDES:
        return "official_release"
    if report_types and report_types <= {"model_card", "safety_report"}:
        return "official_document_update"
    if report_types:
        return "official_source_published"
    return "pending"


def document_role(report_type: str, url: str) -> tuple[str, int]:
    hostname = urllib.parse.urlparse(url).hostname or ""
    if report_type == "technical_report":
        return "primary", 100
    if report_type in {"safety_report", "model_card"}:
        return "safety", 80
    if report_type == "benchmark":
        return "evaluation", 80
    if report_type == "official_blog":
        return "context", 80
    if report_type == "github_repository":
        return "implementation", 70
    if hostname in {"github.com", "raw.githubusercontent.com"}:
        return "implementation", 70
    return "supporting", 50
