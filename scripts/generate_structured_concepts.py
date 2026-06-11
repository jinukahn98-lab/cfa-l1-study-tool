#!/usr/bin/env python3
"""Generate structured study content for each CFA L1 module using Claude CLI.

Uses `claude -p` (Claude Code CLI) instead of anthropic SDK,
so it works with Claude Code's existing auth.

Output: data/structured_concepts.json
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENHANCED_FILE = ROOT / "data" / "enhanced_concepts.json"
OUTPUT_FILE = ROOT / "data" / "structured_concepts.json"
# Load topic structure from modules_l1
sys.path.insert(0, str(ROOT))
from modules_l1 import MODULES
from typing import Optional


def call_claude(prompt: str) -> str:
    """Call Claude Code CLI with a prompt, return response text."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--print"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "CLAUDE_HOME": os.path.expanduser("~/.claude")},
    )
    stderr = result.stderr.strip()
    if stderr:
        # claude CLI often prints warnings to stderr; only raise if actual error
        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI error (exit {result.returncode}): {stderr}")
    return result.stdout.strip()


def generate_module_structured(module: str, mod_data: dict, enhanced: dict) -> Optional[dict]:
    """Generate structured content for one module via Claude CLI."""
    enhanced_mod = enhanced.get(module, {})
    los_list = enhanced_mod.get("los", [])
    formulas = enhanced_mod.get("formulas", [])
    tips = enhanced_mod.get("exam_tips", [])
    summary = enhanced_mod.get("summary", "")
    topics_raw = mod_data.get("topics", {})
    topic_names = list(topics_raw.keys())

    if not los_list:
        print(f"  ⏭️  {module}: no LOS data, skipping")
        return None

    prompt = f"""You are a CFA Level 1 expert tutor. Given the module "{module}" with the following data, create structured study content.

TOPICS: {json.dumps(topic_names, ensure_ascii=False)}

LOS LIST:
{chr(10).join(f"{i+1}. {lo}" for i, lo in enumerate(los_list))}

FORMULAS: {json.dumps(formulas[:10], ensure_ascii=False)}
EXAM TIPS: {json.dumps(tips[:5], ensure_ascii=False)}

Assign each LOS to its topic. For each LOS, write:
1. explanation: 2-4 sentence clear concept explanation
2. key_points: 3-5 bullet points highlighting exam-critical facts

Respond ONLY with a valid JSON object with this structure:
{{
  "topics": [
    {{
      "name": "topic name",
      "los_items": [
        {{
          "los": "full LOS text",
          "explanation": "2-4 sentence explanation...",
          "key_points": ["point 1", "point 2", "point 3"]
        }}
      ]
    }}
  ]
}}

IMPORTANT: Every LOS from the list must appear in exactly one topic's los_items array.
Do NOT skip any LOS. Do NOT add LOS that aren't in the list.
Respond ONLY with raw JSON, no markdown fences, no commentary."""

    print(f"  Calling Claude CLI for {module}...")
    for attempt in range(3):
        try:
            response = call_claude(prompt)
            # Remove markdown fences if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            result = json.loads(response)
            print(f"  ✅ {module}: {len(result.get('topics', []))} topics")
            return result
        except (json.JSONDecodeError, RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"  ⚠️  Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"  ❌ {module}: all attempts failed")
                return None


def main():
    if not ENHANCED_FILE.exists():
        print(f"❌ {ENHANCED_FILE} not found")
        sys.exit(1)

    enhanced = json.loads(ENHANCED_FILE.read_text("utf-8"))
    
    # Load existing output for resumability
    if OUTPUT_FILE.exists():
        existing = json.loads(OUTPUT_FILE.read_text("utf-8"))
        print(f"📂 Resuming from existing {OUTPUT_FILE} ({len(existing)} modules done)")
    else:
        existing = {}

    modules = [
        ("Ethics", MODULES.get("Ethics", {})),
        ("Quantitative Methods", MODULES.get("Quantitative Methods", {})),
        ("Economics", MODULES.get("Economics", {})),
        ("Financial Statement Analysis", MODULES.get("Financial Statement Analysis", {})),
        ("Corporate Issuers", MODULES.get("Corporate Issuers", {})),
        ("Equity Investments", MODULES.get("Equity Investments", {})),
        ("Fixed Income", MODULES.get("Fixed Income", {})),
        ("Derivatives", MODULES.get("Derivatives", {})),
        ("Alternative Investments", MODULES.get("Alternative Investments", {})),
        ("Portfolio Management", MODULES.get("Portfolio Management", {})),
    ]

    for module, mod_data in modules:
        if module in existing:
            print(f"  ⏭️  {module}: already done, skipping")
            continue
        result = generate_module_structured(module, mod_data, enhanced)
        if result:
            existing[module] = result
            OUTPUT_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=1), "utf-8")
            print(f"  💾 Saved ({len(existing)}/10)")
        # Small delay between modules
        time.sleep(2)

    print(f"\n✅ Done! {len(existing)}/10 modules processed")
    print(f"   Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
