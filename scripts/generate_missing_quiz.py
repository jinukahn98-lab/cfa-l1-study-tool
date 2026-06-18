#!/usr/bin/env python3
"""Generate quiz questions for missing readings: 88 (PM) and 89-93 (Ethics)."""
import json, os, re, subprocess, sys, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).parent.parent
PDF_FILE = ROOT / "data" / "pdf_reading_texts.json"
QUIZ_FILE = ROOT / "data" / "quiz_data.json"

MAX_WORKERS = 3

MODULE_BOOK = {
    "Portfolio Management": 5,
    "Ethics": 5,
}

WRAPPER = os.path.expanduser("~/.hermes/scripts/claude-wrapper.sh")

def call_claude(prompt):
    r = subprocess.run([WRAPPER, "-p", prompt, "--print"], capture_output=True, text=True, timeout=120)
    if r.stderr.strip() and r.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {r.stderr}")
    return r.stdout.strip()

def gen_one(reading, module, book):
    rnum = reading["reading_num"]
    title = reading["title"]
    text = reading.get("text", "")
    text = re.sub(r'Video covering.*?available online\.?\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()[:4000]

    prompt = f"""You are a CFA Level 1 exam question writer. Generate 5-10 realistic CFA-style multiple choice questions.

Reading: {title}

{text}

Requirements:
1. ALL text in **Korean (한글)**. English terms in parentheses only.
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
            resp = call_claude(prompt)
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0].strip()
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0].strip()
            qs = json.loads(resp)
            if not isinstance(qs, list) or len(qs) < 3:
                raise ValueError(f"Expected 3+ questions, got {len(qs)}")
            answers = {}
            clean = []
            for q in qs:
                k = str(q.get("num", len(clean)+1))
                answers[k] = {"letter": q.pop("answer", "A"), "explanation": q.pop("explanation", "")}
                clean.append(q)
            return (rnum, module, book, clean, answers)
        except Exception as e:
            if attempt < 2: time.sleep(3)
            else:
                print(f"  ❌ R{rnum}: {e}", flush=True)
                return None

def main():
    pdf = json.loads(PDF_FILE.read_text("utf-8"))
    existing = json.loads(QUIZ_FILE.read_text("utf-8")) if QUIZ_FILE.exists() else {}

    # Find missing readings
    pending = []
    for module in ["Portfolio Management", "Ethics"]:
        mod_data = pdf.get(module, {})
        book = MODULE_BOOK[module]
        for r in mod_data.get("readings", []):
            rnum = r["reading_num"]
            # Check if already exists
            found = False
            for bk_data in existing.values():
                if str(rnum) in bk_data.get("questions", {}):
                    found = True
                    break
            if not found:
                pending.append((r, module, book))

    print(f"📚 {len(pending)} readings to generate", flush=True)
    lock = threading.Lock()

    def process(item):
        r, mod, bk = item
        result = gen_one(r, mod, bk)
        with lock:
            if result:
                nr, mod, bk, qs, ans = result
                bk_str = str(bk)
                if bk_str not in existing:
                    existing[bk_str] = {"questions": {}, "answers": {}}
                existing[bk_str]["questions"][str(nr)] = qs
                if mod not in existing[bk_str]["answers"]:
                    existing[bk_str]["answers"][mod] = {}
                existing[bk_str]["answers"][mod].update(ans)
                tmp = QUIZ_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")
                tmp.rename(QUIZ_FILE)
                print(f"  ✅ R{nr}: {len(qs)}문항", flush=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fs = [pool.submit(process, item) for item in pending]
        for f in as_completed(fs): f.result()

    # Final count
    total = sum(len(qs) for bk in existing.values() for qs in bk.get("questions", {}).values())
    print(f"\n✅ 완료! 총 {total}문항", flush=True)

if __name__ == "__main__":
    main()
