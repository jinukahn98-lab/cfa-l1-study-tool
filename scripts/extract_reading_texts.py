#!/usr/bin/env python3
"""Extract full reading texts from all 5 SchweserNotes PDFs per CFA module."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import pdf_parser
from modules_l1 import MODULE_BOOK_MAP

OUTPUT = Path(__file__).parent.parent / "data" / "pdf_reading_texts.json"

def main():
    result = {}
    for module, info in MODULE_BOOK_MAP.items():
        book = info["book"]
        rstart, rend = info["readings"]
        print(f"  {module}: Book {book}, Readings {rstart}-{rend}")
        readings = pdf_parser.get_readings_for_range(book, rstart, rend)
        module_readings = []
        for r in readings:
            module_readings.append({
                "reading_num": r["reading_num"],
                "title": r["title"],
                "text": r["text"],
            })
        result[module] = {
            "book": book,
            "readings": module_readings,
            "total_chars": sum(len(r["text"]) for r in module_readings),
        }
        print(f"    → {len(module_readings)} readings, {result[module]['total_chars']:,} chars")

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n✅ Saved: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"   Modules: {len(result)}")

if __name__ == "__main__":
    main()
