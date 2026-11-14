"""Read a CV (PDF, Word or text) on this machine and remove contact details before any of it goes to the LLM."""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 20_000


class CVError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    """Plain text of a .pdf, .docx, .txt or .md file."""
    if len(data) > MAX_BYTES:
        raise CVError("The file is larger than 5 MB.")
    name = filename.lower()
    if name.endswith(".pdf"):
        text = _pdf(data)
    elif name.endswith(".docx"):
        text = _docx(data)
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise CVError("Use a PDF, Word (.docx) or text file.")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) < 80:
        raise CVError("No text could be read from this file. If it's a scanned PDF, paste the text instead.")
    return text[:MAX_CHARS]


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:12])
    except Exception as exc:  # broken or encrypted PDF
        raise CVError(f"Couldn't read the PDF: {exc}") from exc


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
    except Exception as exc:
        raise CVError(f"Couldn't read the Word file: {exc}") from exc
    lines = []
    for para in root.iter(f"{_W}p"):
        lines.append("".join(t.text or "" for t in para.iter(f"{_W}t")))
    return "\n".join(lines)


# ---------------------------------------------------------------- privacy

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\w])(\+?\d[\d\s().-]{7,}\d)(?![\w])")
_LINKS = re.compile(r"(https?://)?(www\.)?(linkedin\.com|github\.com|twitter\.com|x\.com)/[\w\-./%]+", re.I)
_ADDRESS = re.compile(r"^.*\b(address|street|road|nagar|apartment|flat no|pin ?code|zip)\b.*$", re.I | re.M)
_YEAR_RANGE = re.compile(r"^\s*(19|20)\d{2}\s*[-–]\s*((19|20)\d{2}|present|now)\s*$", re.I)


def strip_contacts(text: str) -> str:
    """Remove the name line, email, phone, profile links and address lines. Skills and experience stay."""
    text = _EMAIL.sub("[email removed]", text)
    text = _LINKS.sub("[profile link removed]", text)
    text = _PHONE.sub(lambda m: m.group(0) if _YEAR_RANGE.match(m.group(0)) or _looks_like_years(m.group(0))
                      else "[phone removed]", text)
    text = _ADDRESS.sub("[address removed]", text)
    lines = text.split("\n")
    # The first non-empty short line of a CV is almost always the person's name.
    for i, line in enumerate(lines[:3]):
        s = line.strip()
        if s and len(s.split()) <= 4 and not re.search(r"\d|engineer|architect|developer|manager|scientist|lead",
                                                        s, re.I):
            lines[i] = "[name removed]"
            break
    return "\n".join(lines).strip()


def _looks_like_years(s: str) -> bool:
    return bool(re.fullmatch(r"\s*(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\s*", s))
