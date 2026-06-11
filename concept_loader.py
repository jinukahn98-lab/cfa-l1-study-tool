"""
ConceptLoader: Extracts study content for each CFA L1 module.

Priority:
  1. data/structured_concepts.json (AI-generated per-LOS study notes, best UX)
  2. data/enhanced_concepts.json (pre-merged PDF + Korean)
  3. SQLite cache (per-module, runtime-generated)
  4. Hardcoded Korean fallback (concept_data.py)
"""
from pathlib import Path
from typing import Optional

import db
from concept_data import CONCEPT_DATA
from modules_l1 import module_names

STRUCTURED_FILE = Path(__file__).parent / "data" / "structured_concepts.json"
ENHANCED_FILE = Path(__file__).parent / "data" / "enhanced_concepts.json"
PDF_READING_FILE = Path(__file__).parent / "data" / "pdf_reading_texts.json"
_FSA_ALIAS = {"Financial Statement Analysis": "FSA"}


def _load_pdf_readings() -> dict:
    """Load full reading texts extracted from SchweserNotes PDFs."""
    try:
        import json
        import re
        if PDF_READING_FILE.exists():
            data = json.loads(PDF_READING_FILE.read_text("utf-8"))
            # Clean reading texts: remove video markers, excess whitespace
            for mod in data:
                for r in data[mod].get("readings", []):
                    text = r.get("text", "")
                    text = re.sub(r'Video covering\s*\n\s*this content is\s*\n\s*available online\.?\s*', '', text)
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    text = text.strip()
                    r["text"] = text
            return data
    except Exception:
        pass
    return {}


PDF_READINGS = _load_pdf_readings()


def _load_structured() -> dict:
    """Load AI-generated structured study notes (best source)."""
    try:
        import json
        if STRUCTURED_FILE.exists():
            return json.loads(STRUCTURED_FILE.read_text("utf-8"))
    except Exception:
        pass
    return {}


def _load_enhanced() -> dict:
    """Load pre-computed enhanced concept data (PDF + Korean merged)."""
    try:
        import json
        if ENHANCED_FILE.exists():
            return json.loads(ENHANCED_FILE.read_text("utf-8"))
    except Exception:
        pass
    return {}


STRUCTURED_DATA = _load_structured()
ENHANCED_DATA = _load_enhanced()


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


class ConceptLoader:
    DATA_DIR = Path(__file__).parent / "data"

    def load_for_module(self, module: str) -> dict:
        """Load concept data — tries structured JSON → enhanced JSON → SQLite cache → Korean fallback."""

        # 1. AI-generated structured study notes (best UX)
        if STRUCTURED_DATA:
            entry = STRUCTURED_DATA.get(module)
            if entry:
                return {
                    "summary": entry.get("summary", ""),
                    "topics": entry.get("topics", []),
                    "formulas": entry.get("formulas", []),
                    "exam_tips": entry.get("exam_tips", []),
                    "_source": "structured",
                }

        # 2. Check runtime-loaded enhanced data
        if ENHANCED_DATA:
            entry = ENHANCED_DATA.get(module)
            if entry:
                result = {
                    "summary": entry.get("summary", ""),
                    "key_concepts": entry.get("key_concepts", []),
                    "formulas": entry.get("formulas", []),
                    "exam_tips": entry.get("exam_tips", []),
                    "los": entry.get("los", []),
                    "_pdf_readings": entry.get("_pdf_readings", 0),
                    "_source": "enhanced",
                }
                # Warm the SQLite cache
                db.save_concept_cache(module, result)
                return result

        # 2. SQLite cache (from a previous run before enhancement existed)
        cached = db.get_cached_concept(module)
        if cached:
            return cached

        # 3. Hardcoded Korean fallback
        result = _fallback(module)
        db.save_concept_cache(module, result)
        return result

    def get_concept(self, module: str) -> dict:
        return self.load_for_module(module)

    def get_sections(self, module: str) -> dict:
        data = self.load_for_module(module)
        result = {
            "summary": data.get("summary", ""),
            "topics": data.get("topics", []),         # structured source
            "key_concepts": data.get("key_concepts", []),
            "formulas": data.get("formulas", []),
            "exam_tips": data.get("exam_tips", []),
            "los": data.get("los", []),
            "_source": data.get("_source", "unknown"),
        }
        return result

    def available_modules(self) -> list:
        return module_names()

    def clear_cache(self) -> None:
        db.clear_concept_cache()
