#!/usr/bin/env python3
"""Generate Reading별 summaries for each CFA L1 module using Claude CLI.

Processes ONE reading at a time (not whole modules) for reliability.
Reads data/pdf_reading_texts.json and calls `claude -p` per reading.
Output: data/reading_summaries.json

Resumable: skips readings already present in output file.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
PDF_READING_FILE = ROOT / "data" / "pdf_reading_texts.json"
OUTPUT_FILE = ROOT / "data" / "reading_summaries.json"

MAX_TEXT_CHARS = 8000  # Truncate long reading texts to this many chars


def call_claude(prompt: str) -> str:
    """Call Claude Code CLI with a prompt, return response text."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--print"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "CLAUDE_HOME": os.path.expanduser("~/.claude")},
    )
    stderr = result.stderr.strip()
    if stderr:
        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI error (exit {result.returncode}): {stderr}")
        # Some claude versions print warnings to stdout mixed with response
    return result.stdout.strip()


def clean_text(text: str) -> str:
    """Clean reading text: remove video markers, excess whitespace, truncate."""
    text = re.sub(r'Video covering\s*\n\s*this content is\s*\n\s*available online\.?\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n\n[... (truncated)]"
    return text


def load_existing() -> dict:
    """Load existing output for resumability."""
    if OUTPUT_FILE.exists():
        return json.loads(OUTPUT_FILE.read_text("utf-8"))
    return {}


def save_output(data: dict):
    """Atomically save output to file."""
    tmp = OUTPUT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    tmp.rename(OUTPUT_FILE)


def reading_done(existing: dict, module: str, reading_num: int) -> bool:
    """Check if a specific reading has already been summarized."""
    mod_data = existing.get(module)
    if not mod_data:
        return False
    readings = mod_data.get("readings", [])
    for r in readings:
        if r.get("reading_num") == reading_num:
            return True
    return False


def generate_reading_summary(module: str, reading: dict) -> Optional[dict]:
    """Generate summary for one reading via Claude CLI."""
    rnum = reading.get("reading_num", "?")
    title = reading.get("title", "Unknown")
    text = clean_text(reading.get("text", ""))

    prompt = f"""You are a CFA Level 1 expert tutor creating a Korean study document (한글 학습 자료).

Write everything in **Korean (한글)**. Use English only for technical terms (e.g., "discount rate", "HPR") in parentheses.

Format your response like a well-structured study guide:

1. SUMMARY: 2-4 short paragraphs in Korean. Use **bold** for key terms. Include markdown tables (| pipes) for comparisons, formulas, or categories.
2. KEY POINTS: 6-8 specific, exam-focused bullet points in Korean.
3. Include markdown tables where appropriate: 공식 비교표, 개념 비교표, 분류표 등

Use bullet points (•) extensively. Tables (| pipes) for any classifications or comparisons.

Reading: {title}

{text}

Respond ONLY with this exact JSON structure:
{{{{
  "reading_num": {rnum},
  "title": "{title}",
  "summary": "Full study document in Korean with **bold** terms, bullet points, markdown tables...",
  "key_points": [
    "Exam-ready fact 1 in Korean",
    "Exam-ready fact 2 in Korean",
    ...
  ]
}}}}

Example table format in summary:
| 개념 | 설명 | 예시 |
|------|------|------|
| 명목이자율 | ... | ... |
| 실질이자율 | ... | ... |

Make it LOOK like a real Korean study guide (한글 요약집 스타일) — lots of bullets, tables, structured sections.
Respond ONLY with raw JSON, no markdown fences."""

    print(f"  Calling Claude CLI for Reading {rnum}: {title[:50]}...", end=" ", flush=True)
    for attempt in range(3):
        try:
            response = call_claude(prompt)
            # Remove markdown fences if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            result = json.loads(response)
            summary_len = len(result.get("summary", ""))
            kp_count = len(result.get("key_points", []))
            print(f"✅ ({summary_len} chars, {kp_count} key points)")
            return result
        except (json.JSONDecodeError, RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"⚠️{attempt+1}", end=" ", flush=True)
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"❌ Failed: {e}")
                return None
    return None


def main():
    if not PDF_READING_FILE.exists():
        print(f"❌ {PDF_READING_FILE} not found")
        sys.exit(1)

    pdf_data = json.loads(PDF_READING_FILE.read_text("utf-8"))
    existing = load_existing()

    # Count total readings across all modules
    total_readings = 0
    for mod in pdf_data:
        total_readings += len(pdf_data[mod].get("readings", []))
    done_count = 0
    for mod in existing:
        done_count += len(existing[mod].get("readings", []))

    print(f"📚 {len(pdf_data)} modules, {total_readings} total readings")
    print(f"📂 Resuming: {done_count}/{total_readings} readings already done")

    # Process in a sensible module order
    module_order = [
        "Quantitative Methods",
        "Economics",
        "Corporate Issuers",
        "Financial Statement Analysis",
        "Equity Investments",
        "Fixed Income",
        "Derivatives",
        "Alternative Investments",
        "Portfolio Management",
        "Ethics",
    ]

    for module in module_order:
        mod_data = pdf_data.get(module)
        if not mod_data:
            continue

        readings = mod_data.get("readings", [])
        if not readings:
            continue

        print(f"\n📘 {module} ({len(readings)} readings)")
        mod_skipped = 0
        mod_done = 0

        for reading in readings:
            rnum = reading.get("reading_num")

            if reading_done(existing, module, rnum):
                mod_skipped += 1
                continue

            result = generate_reading_summary(module, reading)
            if result:
                # Add to existing data
                if module not in existing:
                    existing[module] = {"readings": []}
                # Check for duplicate reading_num
                existing_readings = existing[module]["readings"]
                existing_readings = [r for r in existing_readings if r.get("reading_num") != rnum]
                existing_readings.append(result)
                # Sort by reading_num
                existing_readings.sort(key=lambda x: x.get("reading_num", 0))
                existing[module]["readings"] = existing_readings
                save_output(existing)
                mod_done += 1
            else:
                # If a reading fails, continue with others
                print(f"  ❌ Reading {rnum} failed after 3 attempts, continuing")
                continue

            # Small delay between readings
            time.sleep(1)

        total_done = len(existing[module]["readings"]) if module in existing else 0
        print(f"  📊 {module}: {total_done}/{len(readings)} readings done")

    total_completed = sum(len(existing[m].get("readings", [])) for m in existing)
    print(f"\n✅ DONE! {total_completed}/{total_readings} readings completed")
    print(f"   Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
