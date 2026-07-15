from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

from .config import DATA_DIR


HEADING_NUMBER = re.compile(r"^(?:\d+(?:\.\d+)*|Appendix\s+[A-Z])(?:\s+|[.)]\s*)(.{2,120})$")
KNOWN_HEADINGS = {
    "abstract",
    "introduction",
    "background",
    "architecture",
    "method",
    "methods",
    "methodology",
    "experiments",
    "evaluation",
    "evaluations",
    "results",
    "limitations",
    "conclusion",
    "conclusions",
    "references",
    "appendix",
}


@dataclass
class Section:
    title: str
    first_page: int
    last_page: int
    text: str


def _looks_like_heading(line: str) -> bool:
    stripped = " ".join(line.split())
    if not 3 <= len(stripped) <= 120:
        return False
    numbered = HEADING_NUMBER.match(stripped)
    if numbered:
        heading_text = numbered.group(1).strip()
        return (
            2 <= len(heading_text) <= 100
            and len(heading_text.split()) <= 12
            and not heading_text.startswith("(")
            and not any(character in heading_text for character in ",%=+[]")
        )
    if stripped.lower() in KNOWN_HEADINGS:
        return True
    words = stripped.split()
    if len(words) > 8 or len(stripped) > 70 or stripped.endswith((".", ",", ";", ":")):
        return False
    if any(character.isdigit() for character in stripped) or any(character in stripped for character in ",()%=+[]"):
        return False
    return False


def _clean_title(line: str) -> str:
    line = " ".join(line.split())
    match = HEADING_NUMBER.match(line)
    return match.group(1).strip() if match else line


def parse_pdf(path: Path, report_id: int | None = None) -> dict:
    reader = PdfReader(str(path))
    metadata = reader.metadata or {}
    pages: list[dict] = []
    sections: list[Section] = []
    current_title = "Document"
    current_first_page = 1
    current_parts: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.replace("\x00", "").strip()
        pages.append({"page": page_number, "text": text, "char_count": len(text)})
        lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
        heading = next((line for line in lines[:12] if _looks_like_heading(line)), None)
        if heading and current_parts:
            sections.append(
                Section(
                    title=current_title,
                    first_page=current_first_page,
                    last_page=max(current_first_page, page_number - 1),
                    text="\n\n".join(current_parts).strip(),
                )
            )
            current_title = _clean_title(heading)
            current_first_page = page_number
            current_parts = []
        elif heading and current_title == "Document":
            current_title = _clean_title(heading)
            current_first_page = page_number
        current_parts.append(text)

    if current_parts:
        sections.append(
            Section(
                title=current_title,
                first_page=current_first_page,
                last_page=len(pages),
                text="\n\n".join(current_parts).strip(),
            )
        )

    outline = []
    try:
        for item in reader.outline:
            if hasattr(item, "title"):
                outline.append(str(item.title))
    except Exception:
        outline = []

    payload = {
        "schema_version": "1.0",
        "report_id": report_id,
        "source_file": str(path),
        "title": str(metadata.get("/Title") or path.stem),
        "author": str(metadata.get("/Author") or ""),
        "page_count": len(pages),
        "outline": outline,
        "sections": [asdict(section) | {"char_count": len(section.text)} for section in sections],
        "pages": pages,
    }
    return payload


def save_parsed_pdf(path: Path, content_hash: str, report_id: int | None = None) -> Path:
    parsed = parse_pdf(path, report_id=report_id)
    destination = DATA_DIR / "parsed" / f"{content_hash}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
