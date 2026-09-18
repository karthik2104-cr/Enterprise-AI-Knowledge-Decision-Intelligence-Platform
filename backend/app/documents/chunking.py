import re


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_pages(
    pages: list[tuple[int | None, str, str | None]],
    chunk_size: int = 700,
    overlap: int = 120,
) -> list[dict]:
    chunks: list[dict] = []
    index = 0
    for page, raw, section in pages:
        text = clean_text(raw)
        if not text:
            continue
        current_section = section
        parts = _window(text, chunk_size, overlap)
        for part in parts:
            heading = _inline_heading(part) or current_section
            if heading:
                current_section = heading
            chunks.append(
                {
                    "chunk_index": index,
                    "content": part,
                    "page": page,
                    "section": heading,
                    "token_count": len(part.split()),
                }
            )
            index += 1
    return chunks


def _window(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [text]
    out: list[str] = []
    i = 0
    step = max(size - overlap, 1)
    while i < len(words):
        out.append(" ".join(words[i : i + size]))
        i += step
    return out


def _inline_heading(text: str) -> str | None:
    first = text.strip().splitlines()[0] if text.strip() else ""
    if first.startswith("#"):
        return first.lstrip("#").strip()[:120]
    if first.isupper() and 3 < len(first) < 80:
        return first.title()
    return None
