import json
import random
from pathlib import Path
from modules_l1 import get_module_for_reading, module_names, TOPIC_ALIAS

DATA_DIR = Path(__file__).parent / "data"


class QuizLoader:
    """Loads quiz_data.json and provides filtered question access.

    quiz_data.json structure:
        {book_num: {
            "questions": {reading_num_str: [{num, text, options, topic, book}, ...]},
            "answers": {topic_name: {question_num_str: {letter, explanation}, ...}}
        }}
    """

    def __init__(self, path=None):
        self.path = path or DATA_DIR / "quiz_data.json"
        if not self.path.exists():
            raise FileNotFoundError(
                f"quiz_data.json not found at {self.path}. "
                "Download it from Google Drive first."
            )
        with open(self.path, encoding="utf-8") as f:
            self.raw = json.load(f)
        self._index = None
        self._answer_map = None

    def _build_index(self):
        """Build module → topic → [question] index and answer lookup map."""
        index = {}
        answer_map = {}  # (book, reading_num, question_num) -> answer_letter

        for bk_str, book_data in self.raw.items():
            book_num = int(bk_str)

            # Build answer map by topic name
            for topic_name, answers in book_data.get("answers", {}).items():
                for qnum_str, ans_info in answers.items():
                    key = (book_num, topic_name, int(qnum_str))
                    answer_map[key] = ans_info.get("letter", "")

            # Index questions
            for reading_str, questions in book_data.get("questions", {}).items():
                reading_num = int(reading_str)

                for q in questions:
                    q["book"] = book_num
                    q["reading_num"] = reading_num
                    q_topic = q.get("topic", "")

                    # Use topic field FIRST (data's own classification), fallback to reading number mapping
                    mod_from_topic = TOPIC_ALIAS.get(q_topic, None)
                    if mod_from_topic:
                        module = mod_from_topic
                        topic = q_topic
                    else:
                        module, topic = get_module_for_reading(reading_num)
                        if not module:
                            module = "미분류"
                            topic = "일반"

                    q["fallback_module"] = module
                    q["fallback_topic"] = topic

                    # Look up answer
                    ans_key = (book_num, q.get("topic", ""), q["num"])
                    direct_ans_key = (book_num, reading_num, q["num"])
                    q["answer"] = (
                        answer_map.get(ans_key, "") or
                        answer_map.get(direct_ans_key, "") or
                        "A"
                    )

                    # Add to index
                    use_module = module or q.get("topic", "미분류")
                    if use_module not in index:
                        index[use_module] = {}
                    use_topic = topic or q.get("topic", "일반")
                    if use_topic not in index[use_module]:
                        index[use_module][use_topic] = []
                    index[use_module][use_topic].append(q)

        self._index = index

    @property
    def index(self):
        if self._index is None:
            self._build_index()
        return self._index

    def available_modules(self):
        """Return list of module names that have questions in the data."""
        modules = []
        for m in module_names():
            if m in self.index:
                modules.append(m)
        # Add any non-standard modules found in data
        for m in sorted(self.index.keys()):
            if m not in modules:
                modules.append(m)
        return modules

    def topics_for_module(self, module):
        """Return dict of topic -> question_count"""
        mod_data = self.index.get(module, {})
        return {t: len(qs) for t, qs in mod_data.items()}

    def get_questions(self, module=None, topic=None, count=None, shuffle=True):
        """Get questions filtered by module/topic."""
        questions = []
        if module:
            for t, qs in self.index.get(module, {}).items():
                if topic and t != topic:
                    continue
                questions.extend(qs)
        else:
            for mod in self.index.values():
                for qs in mod.values():
                    questions.extend(qs)

        if shuffle:
            random.shuffle(questions)
        if count and count < len(questions):
            questions = questions[:count]
        return questions

    def stats(self):
        """Return module-wise stats dict."""
        stats = {}
        for mod, topics in self.index.items():
            total = sum(len(qs) for qs in topics.values())
            stats[mod] = {
                "total_questions": total,
                "topics": {t: len(qs) for t, qs in topics.items()},
            }
        return stats
