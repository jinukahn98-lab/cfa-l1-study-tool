import os
import json
import requests


class FlashcardGenerator:
    def __init__(self):
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.enabled = bool(self.anthropic_key or self.openai_key)

    def generate(self, summary_text: str, count: int = 5) -> list[dict] | bool:
        if not self.enabled:
            return False

        prompt = (
            f"다음 CFA Level 1 개념 요약을 읽고, 시험에 나올 만한 플래시카드 {count}개를 만들어 주세요.\n"
            f"각 플래시카드는 {{\"question\": \"...\", \"answer\": \"...\"}} 형식의 JSON이어야 합니다.\n"
            f"질문과 답변 모두 한국어로 작성하세요. 반드시 JSON 배열만 출력하세요.\n\n"
            f"개념 요약:\n{summary_text[:3000]}"
        )

        if self.anthropic_key:
            return self._call_anthropic(prompt)
        return self._call_openai(prompt)

    def _call_anthropic(self, prompt: str) -> list[dict] | bool:
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            return self._parse_cards(content)
        except Exception:
            return False

    def _call_openai(self, prompt: str) -> list[dict] | bool:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_cards(content)
        except Exception:
            return False

    def _parse_cards(self, text: str) -> list[dict] | bool:
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            return False
        try:
            cards = json.loads(text[start:end])
            if isinstance(cards, list) and all(
                isinstance(c, dict) and "question" in c and "answer" in c
                for c in cards
            ):
                return cards
        except (json.JSONDecodeError, ValueError):
            pass
        return False
