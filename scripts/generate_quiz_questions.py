#!/usr/bin/env python3
"""Generate CFA-style quiz questions for all 88 readings using Claude CLI in parallel.

Process: multiple readings concurrently, resumable, saves incrementally.
Output: data/quiz_data.json (full format with questions + answers).
"""
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
PDF_FILE = ROOT / "data" / "pdf_reading_texts.json"
QUIZ_FILE = ROOT / "data" / "quiz_data.json"
MAX_TEXT_CHARS = 4000
MAX_WORKERS = 5  # Parallel readings

MODULES_IN_ORDER = [
    "Quantitative Methods",          # 11 readings
    "Economics",                     # 8
    "Corporate Issuers",             # 7
    "Financial Statement Analysis",  # 11
    "Equity Investments",            # 8
    "Fixed Income",                  # 18
    "Derivatives",                   # 10
    "Alternative Investments",       # 6
    "Portfolio Management",          # 4
    "Ethics",                        # 5
]

MODULE_BOOK = {  # module -> book number
    "Quantitative Methods": 1,
    "Economics": 1,
    "Corporate Issuers": 2,
    "Financial Statement Analysis": 3,
    "Equity Investments": 3,
    "Fixed Income": 4,
    "Derivatives": 4,
    "Alternative Investments": 5,
    "Portfolio Management": 5,
    "Ethics": 5,
}


def call_claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--print"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "CLAUDE_HOME": os.path.expanduser("~/.claude")},
    )
    stderr = result.stderr.strip()
    if stderr and result.returncode != 0:
        raise RuntimeError(f"Claude CLI error (exit {result.returncode}): {stderr}")
    return result.stdout.strip()


def reading_has_questions(existing: dict, reading_num: int) -> bool:
    for bk_str, bk_data in existing.items():
        qs = bk_data.get("questions", {}).get(str(reading_num), [])
        if qs and len(qs) >= 5:
            return True
    return False


def generate_one_reading(reading: dict, module: str, book: int):
    """Generate questions for a single reading. Returns (reading_num, questions, answers) or None."""
    rnum = reading.get("reading_num", "?")
    title = reading.get("title", "Unknown")
    text = reading.get("text", "")

    text = re.sub(r'Video covering\s*\n\s*this content is\s*\n\s*available online\.?\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n\n[... (truncated)]"

    prompt = f"""You are a CFA Level 1 exam question writer. Generate 5-10 realistic CFA-style multiple choice questions.

Reading: {title}

{text}

Requirements:
1. ALL text in **Korean (한글)**. English terms in parentheses only (e.g., "내부수익률(IRR)").
2. Mix of concept recall and calculation/application questions.
3. Each question has 3 options (A, B, C).
4. Provide correct answer letter and explanation in Korean.

Respond ONLY with this JSON array:
[
  {{
    "num": 1,
    "text": "Question in Korean?",
    "options": ["A: ...", "B: ...", "C: ..."],
    "topic": "{module}",
    "book": {book},
    "answer": "A",
    "explanation": "Explanation in Korean..."
  }},
  ...
]
Respond ONLY with the raw JSON array, no markdown fences."""

    for attempt in range(3):
        try:
            response = call_claude(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            qs = json.loads(response)
            if not isinstance(qs, list) or len(qs) < 3:
                raise ValueError(f"Expected list of 3+ questions, got {type(qs)} len={len(qs) if isinstance(qs, list) else '?'}")
            # Separate answers from question data
            answers = {}
            clean_qs = []
            for q in qs:
                ans_key = str(q.get("num", len(clean_qs) + 1))
                answers[ans_key] = {
                    "letter": q.pop("answer", "A"),
                    "explanation": q.pop("explanation", ""),
                }
                clean_qs.append(q)
            return (rnum, clean_qs, answers)
        except (json.JSONDecodeError, RuntimeError, subprocess.TimeoutExpired, ValueError) as e:
            if attempt < 2:
                time.sleep(3)
            else:
                return None


def save_checkpoint(data: dict):
    tmp = QUIZ_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    tmp.rename(QUIZ_FILE)


def main():
    if not PDF_FILE.exists():
        print(f"❌ {PDF_FILE} not found", flush=True)
        sys.exit(1)

    pdf_data = json.loads(PDF_FILE.read_text("utf-8"))
    existing = {}
    if QUIZ_FILE.exists():
        existing = json.loads(QUIZ_FILE.read_text("utf-8"))

    # Collect all readings that need processing
    pending = []
    for module in MODULES_IN_ORDER:
        mod_data = pdf_data.get(module)
        if not mod_data:
            continue
        readings = mod_data.get("readings", [])
        book = MODULE_BOOK.get(module, 0)
        for reading in readings:
            rnum = reading.get("reading_num")
            if reading_has_questions(existing, rnum):
                continue
            pending.append((reading, module, book))

    total = len(pending)
    done_count = 0
    total_questions = 0

    print(f"📚 {total} readings need quiz questions", flush=True)
    print(f"⚡ Parallel workers: {MAX_WORKERS}", flush=True)

    lock = __import__('threading').Lock()

    def process_one(item):
        nonlocal done_count, total_questions
        reading, module, book = item
        rnum = reading.get("reading_num")
        result = generate_one_reading(reading, module, book)
        with lock:
            done_count += 1
            if result:
                nr, qs, answers = result
                bk_str = str(book)
                if bk_str not in existing:
                    existing[bk_str] = {"questions": {}, "answers": {}}
                existing[bk_str]["questions"][str(nr)] = qs
                if module not in existing[bk_str]["answers"]:
                    existing[bk_str]["answers"][module] = {}
                for k, v in answers.items():
                    existing[bk_str]["answers"][module][k] = v
                total_questions += len(qs)
                save_checkpoint(existing)
                print(f"  ✅ R{nr}: {len(qs)}문항 ({done_count}/{total})", flush=True)
            else:
                print(f"  ❌ R{reading.get('reading_num','?')}: 실패 ({done_count}/{total})", flush=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(process_one, item) for item in pending]
        for f in as_completed(futures):
            f.result()  # re-raises exceptions

    print(f"\n✅ 완료! 총 {total_questions}문항 생성됨", flush=True)
    print(f"   파일: {QUIZ_FILE}", flush=True)

    # Count per book
    for bk in sorted(existing.keys()):
        qcount = sum(len(qs) for qs in existing[bk].get("questions", {}).values())
        print(f"   Book {bk}: {qcount}문항", flush=True)


if __name__ == "__main__":
    main()
