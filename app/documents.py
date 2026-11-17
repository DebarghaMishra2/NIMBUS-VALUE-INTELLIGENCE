from __future__ import annotations
from pathlib import Path
import re
import json
from typing import Iterable
import fitz
from docx import Document as DocxDocument

SECTION_ALIASES = {
    "overview", "objectives", "scope", "success measures", "benefits plan",
    "risks and mitigations", "stakeholders", "timeline"
}
INJECTION_MARKERS = [
    re.compile(r"NOTE TO ANY AI ASSISTANT READING THIS DOCUMENT:.*?(?=Mitigation:|$)", re.I | re.S),
    re.compile(r"ignore all previous instructions.*?(?=Mitigation:|$)", re.I | re.S),
]


def _extract_file(path: Path) -> list[tuple[str, int | None]]:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return [(path.read_text(encoding="utf-8", errors="replace"), None)]
    if suffix == ".pdf":
        doc = fitz.open(path)
        return [(page.get_text("text"), i + 1) for i, page in enumerate(doc)]
    if suffix == ".docx":
        doc = DocxDocument(path)
        parts = []
        current = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                current.append(text)
        return [("\n".join(current), None)]
    return []


def _find_initiative_id(text: str, filename: str, initiative_names: dict[str, str]) -> str | None:
    m = re.search(r"\b(INIT-\d{1,3})\b", text, re.I)
    if m:
        return f"INIT-{int(m.group(1).split('-')[1]):03d}"
    # Fall back to matching the canonical initiative name inside the extracted text.
    low = text.lower()
    for iid, name in initiative_names.items():
        if name.lower() in low:
            return iid
    # Filename fall back only for standard INIT-### names.
    m = re.search(r"INIT[-_ ]?(\d{1,3})", filename, re.I)
    return f"INIT-{int(m.group(1)):03d}" if m else None


def _split_into_sections(text: str, page: int | None) -> list[dict]:
    lines = text.replace("\r", "").splitlines()
    current = "Overview"
    buffers: dict[str, list[str]] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.sub(r"^#{1,6}\s*", "", stripped).strip().rstrip(":")
        heading_norm = heading.lower()
        if heading_norm in SECTION_ALIASES:
            current = next((s for s in ["Overview", "Objectives", "Scope", "Success Measures", "Benefits Plan", "Risks and Mitigations", "Stakeholders", "Timeline"] if s.lower() == heading_norm), heading)
            buffers.setdefault(current, [])
        else:
            buffers.setdefault(current, []).append(stripped)
    result = []
    for section, lines_ in buffers.items():
        body = "\n".join(lines_).strip()
        if body:
            result.append({"section": section, "text": body, "page_number": page})
    return result


def _sanitize_untrusted_text(text: str) -> tuple[str, bool]:
    cleaned = text
    flagged = False
    for pattern in INJECTION_MARKERS:
        cleaned, n = pattern.subn("[Embedded instruction-like text removed from model context.]", cleaned)
        flagged = flagged or n > 0
    # Also remove residual instruction fragments that may be phrased as imperatives.
    cleaned = re.sub(r"(?i)ignore all previous instructions[^\n]*", "[Instruction-like text removed.]", cleaned)
    return cleaned, flagged


def _chunk_text(text: str, max_words: int = 500, overlap: int = 75) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [text]
    chunks = []
    step = max(1, max_words - overlap)
    for start in range(0, len(words), step):
        part = words[start:start + max_words]
        if part:
            chunks.append(" ".join(part))
        if start + max_words >= len(words):
            break
    return chunks


def ingest_charters(dataset_dir: Path, initiatives) -> list[dict]:
    charter_dir = Path(dataset_dir) / "charters"
    name_map = {r.initiative_id: r["name"] for _, r in initiatives.iterrows()}
    chunks: list[dict] = []
    for path in sorted(charter_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".pdf", ".docx"}:
            continue
        extracted_pages = _extract_file(path)
        combined = "\n".join(t for t, _ in extracted_pages)
        iid = _find_initiative_id(combined, path.name, name_map)
        if not iid:
            continue
        for page_text, page_no in extracted_pages:
            for sec in _split_into_sections(page_text, page_no):
                for j, part in enumerate(_chunk_text(sec["text"])):
                    safe_text, injection_flag = _sanitize_untrusted_text(part)
                    if not safe_text.strip():
                        continue
                    chunks.append({
                        "chunk_id": f"{iid}-{path.stem}-{sec['section'].lower().replace(' ', '-')}-{page_no or 0}-{j+1}",
                        "initiative_id": iid,
                        "source_filename": path.name,
                        "section": sec["section"],
                        "page_number": page_no,
                        "content": safe_text,
                        "contains_instruction_like_text": injection_flag,
                    })
    return chunks


def persist_chunks(chunks: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in chunks), encoding="utf-8")
