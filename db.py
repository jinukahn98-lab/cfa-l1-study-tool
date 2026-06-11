import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "cfa_l1_study.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                book          INTEGER,
                reading_num   INTEGER,
                question_num  INTEGER,
                question_text TEXT,
                selected      TEXT,
                correct       TEXT,
                is_correct    BOOLEAN,
                module        TEXT,
                topic         TEXT,
                timestamp     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bookmarks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                book          INTEGER,
                reading_num   INTEGER,
                question_num  INTEGER,
                note          TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS study_sessions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                module            TEXT,
                questions_total   INTEGER,
                questions_correct INTEGER,
                duration_sec      INTEGER,
                started_at        TIMESTAMP,
                ended_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_attempts_module ON quiz_attempts(module);
            CREATE INDEX IF NOT EXISTS idx_attempts_correct ON quiz_attempts(is_correct);
            CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON quiz_attempts(timestamp DESC);
        """)


def save_attempt(book, reading_num, question_num, question_text,
                 selected, correct, module, topic):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO quiz_attempts
                (book, reading_num, question_num, question_text,
                 selected, correct, is_correct, module, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book, reading_num, question_num, question_text,
              selected, correct, selected == correct, module, topic))


def add_bookmark(book, reading_num, question_num, note=""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO bookmarks (book, reading_num, question_num, note)
            VALUES (?, ?, ?, ?)
        """, (book, reading_num, question_num, note))


def get_wrong_answers(module=None, limit=50):
    with get_conn() as conn:
        if module:
            rows = conn.execute("""
                SELECT * FROM quiz_attempts
                WHERE is_correct = 0 AND module = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (module, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM quiz_attempts
                WHERE is_correct = 0
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_progress():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT module,
                   COUNT(*) as total,
                   SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
                   ROUND(AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as pct
            FROM quiz_attempts
            GROUP BY module
            ORDER BY pct
        """).fetchall()
        return [dict(r) for r in rows]


def get_recent_attempts(limit=20):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM quiz_attempts
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def clear_attempts():
    with get_conn() as conn:
        conn.execute("DELETE FROM quiz_attempts")
