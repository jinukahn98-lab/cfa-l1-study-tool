"""
Parse SchweserNotes PDFs into structured reading data.
Uses pymupdf (import fitz) to extract text page by page,
then splits by READING N headers.
"""

import re
from pathlib import Path

try:
    import fitz
except ImportError:
    fitz = None  # type: ignore

PDF_DIR = Path(__file__).parent / "data" / "pdfs"

PDF_FILES = {
    1: "Book 1 - QM, Economics.pdf",
    2: "Book 2 - PM, Corp Issuers.pdf",
    3: "Book 3 - FSA, Equity.pdf",
    4: "Book 4 - FI, Derivatives.pdf",
    5: "Book 5 - AI, PM, Ethics.pdf",
}

# Pages to skip at the start of each book (TOC, copyright, welcome)
SKIP_PAGES = 12


def _clean_text(text: str) -> str:
    """Remove noise: page numbers, headers, excess whitespace."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip very short lines that are likely page numbers or decorators
        if len(stripped) <= 2:
            continue
        # Skip lines that are just a number (page number)
        if re.fullmatch(r'\d+', stripped):
            continue
        cleaned.append(stripped)
    return '\n'.join(cleaned)


def _parse_book(book_num: int) -> list:
    """
    Parse a single book PDF.
    Returns list of dicts: [{reading_num, title, text}]
    """
    if fitz is None:
        return []

    path = PDF_DIR / PDF_FILES.get(book_num, "")
    if not path.exists():
        return []

    doc = fitz.open(str(path))
    pages_text = [doc[i].get_text() for i in range(doc.page_count)]

    # First pass: find all candidate reading-start pages
    candidates = {}  # reading_num -> (page_idx, title)

    for i, text in enumerate(pages_text):
        if i < SKIP_PAGES:
            continue

        # Skip TOC pages — they list many readings in one page
        reading_matches = re.findall(r'READING \d+', text)
        if len(reading_matches) > 4:
            continue

        m = re.search(r'READING (\d+)\n([A-Z][^\n]+(?:\n[A-Z][^\n]+)*)', text)
        if not m:
            continue

        num = int(m.group(1))
        if num in candidates:
            continue  # keep first occurrence only

        title_block = m.group(2)
        # Take up to 2 lines for title, join them
        title_lines = [ln.strip() for ln in title_block.splitlines()[:2] if ln.strip()]
        title = ' '.join(title_lines).title()
        candidates[num] = (i, title)

    if not candidates:
        return []

    sorted_nums = sorted(candidates.keys())
    readings = []

    for idx, num in enumerate(sorted_nums):
        start_page, title = candidates[num]
        end_page = candidates[sorted_nums[idx + 1]][0] if idx + 1 < len(sorted_nums) else len(pages_text)

        raw = '\n'.join(pages_text[start_page:end_page])
        text = _clean_text(raw)

        readings.append({
            "book_num": book_num,
            "reading_num": num,
            "title": title,
            "text": text,
        })

    return readings


def parse_book(book_num: int) -> list:
    """Parse one book. Returns [{book_num, reading_num, title, text}]."""
    return _parse_book(book_num)


def parse_all() -> dict:
    """
    Parse all 5 books.
    Returns {book_num: [{book_num, reading_num, title, text}]}
    """
    result = {}
    for book_num in PDF_FILES:
        result[book_num] = _parse_book(book_num)
    return result


def get_readings_for_range(book_num: int, reading_start: int, reading_end: int) -> list:
    """Return readings from a book that fall within [reading_start, reading_end]."""
    all_readings = _parse_book(book_num)
    return [r for r in all_readings if reading_start <= r["reading_num"] <= reading_end]
