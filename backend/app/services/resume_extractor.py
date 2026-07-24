import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_bytes(data: bytes, filename: str, content_type: str | None = None) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        parts = [page.extract_text() or "" for page in reader.pages]
        return normalize_text("\n".join(parts))
    if ext == ".docx" or (
        content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        doc = Document(io.BytesIO(data))
        return normalize_text("\n".join(p.text for p in doc.paragraphs))
    if ext == ".txt" or (content_type and content_type.startswith("text/")):
        return normalize_text(data.decode("utf-8", errors="ignore"))
    raise ValueError(f"Unsupported file type: {ext or content_type}")


def detect_ats_issues(text: str) -> dict:
    """Heuristic ATS checks used alongside LLM ATS notes."""
    issues: list[str] = []
    score = 10

    if re.search(r"\|.+\|", text):
        issues.append("Possible table or pipe-delimited layout detected")
        score -= 2
    if re.search(r"[\u2500-\u257F]", text):
        issues.append("Box-drawing characters may confuse ATS parsers")
        score -= 1
    date_formats = set(re.findall(r"\b(?:\d{1,2}[/-]\d{4}|\w+\s+\d{4}|\d{4})\b", text))
    slash_dates = re.findall(r"\b\d{1,2}[/-]\d{4}\b", text)
    word_dates = re.findall(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", text, re.I)
    if slash_dates and word_dates:
        issues.append("Inconsistent date formatting across sections")
        score -= 2
    unusual = re.findall(r"(?im)^(my journey|about me|who i am|life story)\s*$", text)
    if unusual:
        issues.append("Unusual section headings may reduce ATS keyword matching")
        score -= 1
    if len(text) < 400:
        issues.append("Resume text appears very short; content may not have extracted cleanly")
        score -= 2
    if re.search(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\u024F]", text):
        issues.append("Unsupported or unusual characters detected")
        score -= 1

    return {"ats_score": max(0, min(10, score)), "issues": issues, "date_sample_count": len(date_formats)}
