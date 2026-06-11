"""
ConceptLoader: Extracts study content for each CFA L1 module.

Priority:
  1. SQLite cache (parsed once, reused)
  2. SchweserNotes PDFs (via pdf_parser)
  3. Hardcoded Korean fallback (concept_data.py)
"""

import re
from pathlib import Path
from typing import Optional

import db
from concept_data import CONCEPT_DATA
from modules_l1 import module_names, MODULE_BOOK_MAP

# concept_data.py uses "FSA" but modules_l1 uses the full name
_FSA_ALIAS = {"Financial Statement Analysis": "FSA"}


def _fallback(module: str) -> dict:
    """Return hardcoded Korean data from concept_data.py."""
    key = _FSA_ALIAS.get(module, module)
    data = CONCEPT_DATA.get(key) or CONCEPT_DATA.get(module, {})
    return {
        "summary": data.get("summary", f"{module} 개념 정리를 불러오는 중 오류가 발생했습니다."),
        "key_concepts": data.get("key_concepts", []),
        "formulas": data.get("formulas", []),
        "exam_tips": data.get("exam_tips", []),
        "los": data.get("los", []),
    }


# ── PDF text extraction helpers ───────────────────────────────────────────────

def _extract_los(text: str) -> list:
    """Extract LOS items from raw reading text."""
    los = []
    # LOS lines look like:  "LOS 1.a: Calculate ..."
    for m in re.finditer(r'LOS\s+\d+\.[a-z][\.:]\s*(.+?)(?=\nLOS|\nModule|\nKey Concept|\Z)',
                         text, re.DOTALL | re.IGNORECASE):
        item = ' '.join(m.group(1).split())
        if len(item) > 10:
            los.append(item[:200])
    return los[:30]


def _extract_key_concepts_section(text: str) -> list:
    """Extract bullet points from 'KEY CONCEPTS' section."""
    items = []
    m = re.search(r'KEY CONCEPTS\s*\n(.*?)(?=\nANSWER KEY|\nMODULE \d|\Z)',
                  text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    block = m.group(1)
    for line in block.splitlines():
        stripped = line.strip()
        # Bullet-style lines: start with LOS ref, a dash, or a capital letter
        if re.match(r'(LOS \d+|[A-Z][^a-z]{0,3}\.|•|[-–])\s+\S', stripped):
            clean = re.sub(r'^(LOS \d+\.[a-z][\.:]\s*|[-•–]\s*)', '', stripped)
            if len(clean) > 15:
                items.append(clean[:200])
    return items[:20]


def _extract_formulas(text: str) -> list:
    """Heuristic: find lines that look like mathematical formulas."""
    formulas = []
    seen = set()
    # Lines containing = and at least one math symbol or variable pattern
    pattern = re.compile(
        r'^(?!.*(?:LOS|Copyright|ISBN|www\\.|©)).{5,80}\s*=\s*.{3,60}$',
        re.MULTILINE
    )
    for m in pattern.finditer(text):
        line = m.group(0).strip()
        # Skip lines that look like plain English sentences
        if re.search(r'\b(the|and|or|of|for|is|are|was|were|be|been|being)\b', line, re.I):
            continue
        # Must have some math-looking content
        if not re.search(r'[+\-×÷/*^√∑Σ()₀₁₂αβσμλ]|[A-Z]{2,}|[A-Z][₀₁₂]|\d', line):
            continue
        key = line[:40]
        if key not in seen:
            seen.add(key)
            # Try to split into name and formula parts
            parts = re.split(r'\s*[=:]\s*', line, maxsplit=1)
            if len(parts) == 2 and len(parts[0]) < 50:
                formulas.append((parts[0].strip(), line))
            else:
                formulas.append(("공식", line))
        if len(formulas) >= 15:
            break
    return formulas


def _build_summary(text: str, module: str) -> str:
    """Extract a meaningful intro summary from reading text."""
    # Strip header boilerplate
    text = re.sub(r'Video covering\s*\nthis content is\s*\navailable online\.?\n', '', text)
    text = re.sub(r'READING \d+\n[A-Z ]+\n', '', text)

    # Find first substantive paragraph (not LOS, not module header)
    paragraphs = re.split(r'\n{2,}', text)
    intro_parts = []
    word_count = 0
    for para in paragraphs:
        stripped = para.strip()
        # Skip short fragments and structural headers
        if len(stripped) < 60:
            continue
        if re.match(r'^(LOS|MODULE|READING|Key Concepts|PROFESSOR|VIDEO|©)', stripped, re.I):
            continue
        intro_parts.append(stripped)
        word_count += len(stripped.split())
        if word_count >= 120:
            break

    summary = ' '.join(' '.join(p.split()) for p in intro_parts)
    return summary[:800] if summary else f"{module} 개요"


def _parse_from_pdf(module: str) -> Optional[dict]:
    """
    Parse PDF content for a module.
    Returns structured dict or None if PDFs are unavailable.
    """
    try:
        from pdf_parser import get_readings_for_range
    except ImportError:
        return None

    info = MODULE_BOOK_MAP.get(module)
    if not info:
        return None

    book_num = info["book"]
    r_start, r_end = info["readings"]

    readings = get_readings_for_range(book_num, r_start, r_end)
    if not readings:
        return None

    # Concatenate all reading texts for this module
    combined_text = '\n\n'.join(r["text"] for r in readings)

    summary = _build_summary(combined_text, module)
    los_items = _extract_los(combined_text)
    key_concepts = _extract_key_concepts_section(combined_text)
    formulas = _extract_formulas(combined_text)

    # If key_concepts are sparse, derive from LOS
    if len(key_concepts) < 3 and los_items:
        key_concepts = [lo[:150] for lo in los_items[:15]]

    # Exam tips: use Key Concepts section items that are tip-like
    fallback = _fallback(module)
    exam_tips = fallback["exam_tips"]  # always use curated tips
    if not exam_tips:
        exam_tips = key_concepts[:5]

    # Augment with fallback if PDF content is thin
    if len(summary) < 100:
        summary = fallback["summary"]
    if len(key_concepts) < 3:
        key_concepts = fallback["key_concepts"]
    if len(formulas) < 2:
        formulas = fallback["formulas"]
    if not los_items:
        los_items = fallback["los"]

    return {
        "summary": summary,
        "key_concepts": key_concepts,
        "formulas": formulas,
        "exam_tips": exam_tips,
        "los": los_items,
    }


# ── Public interface ──────────────────────────────────────────────────────────

class ConceptLoader:
    # Legacy docx path kept for backward compatibility
    DATA_DIR = Path(__file__).parent / "data" / "summary_notes"

    def load_for_module(self, module: str) -> dict:
        """
        Load concept data for a module.
        Tries: SQLite cache → hardcoded Korean data → PDF parsing enhancement.
        Returns dict with: summary, key_concepts, formulas, exam_tips, los.
        """
        cached = db.get_cached_concept(module)
        if cached:
            return cached

        # Use hardcoded Korean concept data as base
        result = _fallback(module)
        
        # Enhance with PDF data if available
        pdf_data = _parse_from_pdf(module)
        if pdf_data and result:
            # Merge: PDF concepts supplement, not replace
            if not result.get("key_concepts") and pdf_data.get("key_concepts"):
                result["key_concepts"] = pdf_data["key_concepts"]
            if not result.get("formulas") and pdf_data.get("formulas"):
                result["formulas"] = pdf_data["formulas"]
            result["_pdf_available"] = True
        
        db.save_concept_cache(module, result)
        return result

    def get_concept(self, module: str) -> dict:
        return self.load_for_module(module)

    def get_sections(self, module: str) -> dict:
        data = self.load_for_module(module)
        return {
            "summary": data.get("summary", ""),
            "key_concepts": data.get("key_concepts", []),
            "formulas": data.get("formulas", []),
            "exam_tips": data.get("exam_tips", []),
            "los": data.get("los", []),
        }

    def available_modules(self) -> list:
        return module_names()

    def clear_cache(self) -> None:
        db.clear_concept_cache()
