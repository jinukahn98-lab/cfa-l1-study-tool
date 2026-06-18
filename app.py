"""
CFA Level 1 Study Tool — Streamlit app
SchweserNotes 2022 기반 개념 정리 + 문제은행 + 진도 추적
"""
import html as _html
import streamlit as st
import pandas as pd
import re
from quiz_loader import QuizLoader
from modules_l1 import module_names, topics_for_module, module_color, MODULE_COLORS, MODULE_BOOK_MAP
from concept_loader import ConceptLoader
import db

def _md_inline(text: str) -> str:
    """Escape HTML and convert **bold** markdown to <strong> for embedding in HTML blocks."""
    text = _html.escape(str(text))
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


_LOS_ACTION_COLORS = {
    "Calculate":   ("#1e40af", "#dbeafe"),
    "Describe":    ("#065f46", "#d1fae5"),
    "Explain":     ("#6d28d9", "#ede9fe"),
    "Compare":     ("#b45309", "#fef3c7"),
    "Interpret":   ("#1d4ed8", "#dbeafe"),
    "Define":      ("#065f46", "#d1fae5"),
    "Identify":    ("#1e40af", "#dbeafe"),
    "Discuss":     ("#6d28d9", "#ede9fe"),
    "Demonstrate": ("#6d28d9", "#ede9fe"),
    "Evaluate":    ("#b45309", "#fef3c7"),
    "Analyze":     ("#b45309", "#fef3c7"),
    "Distinguish": ("#b45309", "#fef3c7"),
    "Contrast":    ("#b45309", "#fef3c7"),
}

st.set_page_config(page_title="CFA Level 1 Study Tool", page_icon="📊", layout="wide")

# ─── Custom CSS ──────────────
st.markdown("""
<style>
/* ─── Global ─── */
.stApp {
    background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 100%);
}
.stApp > header {
    background: linear-gradient(90deg, #0a1628 0%, #132044 50%, #1a2d5e 100%) !important;
    border-bottom: 2px solid #c8a04e;
}
.stApp > header a, .stApp > header span {
    color: #c8a04e !important;
}

/* ─── Title ─── */
.main-title {
    background: linear-gradient(135deg, #0a1628 0%, #1a3a6b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.2rem;
    margin-bottom: 0.2rem;
}
.title-sub {
    color: #64748b;
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
}

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #ffffff;
    border-radius: 14px;
    padding: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 0.9rem;
    color: #64748b;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #f1f5f9;
    color: #0a1628;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0a1628, #1a3a6b) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(10,22,40,0.25);
}

/* ─── Sidebar / Columns ─── */
[data-testid="column"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    border: 1px solid #f1f5f9;
}
div[data-testid="stVerticalBlock"] > div[data-testid="column"]:first-child {
    padding-top: 16px;
}

/* ─── Buttons ─── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    border: none !important;
    padding: 8px 20px !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0a1628, #1a3a6b) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(10,22,40,0.2) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(10,22,40,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: #f1f5f9 !important;
    color: #334155 !important;
    border: 1px solid #e2e8f0 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #e2e8f0 !important;
}

/* ─── Metrics ─── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    border: 1px solid #f1f5f9;
    text-align: center;
}
[data-testid="stMetric"] label {
    color: #64748b;
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: #0a1628 !important;
}

/* ─── Progress Bar ─── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #0a1628, #c8a04e) !important;
    border-radius: 10px;
}
.stProgress > div > div {
    background: #e2e8f0 !important;
    border-radius: 10px;
    height: 8px !important;
}

/* ─── Dividers ─── */
.stDivider {
    border-color: #e2e8f0 !important;
    margin: 1.2rem 0 !important;
}

/* ─── Alert boxes ─── */
.stAlert {
    border-radius: 10px !important;
    border-left: 4px solid !important;
}
div.stAlert {
    padding: 12px 16px !important;
}

/* ─── Dataframe ─── */
[data-testid="stDataFrame"] {
    border: 1px solid #f1f5f9 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ─── Module Badge helper class ─── */
.module-badge {
    display: inline-block !important;
    padding: 3px 12px !important;
    border-radius: 20px !important;
    color: white !important;
    font-size: 0.78em !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
}

/* ─── Expanders ─── */
.streamlit-expanderHeader {
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    border-left: 2px solid #e2e8f0 !important;
    padding-left: 1rem !important;
}

/* ─── Selectbox / Input ─── */
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
}

/* ─── Slider ─── */
.stSlider [data-baseweb="slider"] {
    margin-top: 0.5rem;
}

/* ─── Container padding ─── */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px;
}

/* ─── Radio buttons ─── */
.row-widget.stRadio {
    padding: 0.3rem 0;
}
.row-widget.stRadio > div {
    gap: 0.3rem;
}

/* ─── Quiz result box (dark card) ─── */
.quiz-result-box {
    background: linear-gradient(135deg, #0a1628 0%, #1a3a6b 100%);
    border-radius: 14px;
    padding: 2rem;
    color: white;
    text-align: center;
    margin: 1rem 0;
}
.quiz-result-box h2 {
    color: #c8a04e !important;
    font-size: 1.8rem !important;
}

/* ─── Callout card ─── */
.callout-card {
    background: linear-gradient(135deg, #f8fafc, #eef2f7);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
}

/* ─── Success, Error boxes inside quiz ─── */
.quiz-feedback-correct {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0;
}
.quiz-feedback-wrong {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0;
}
.quiz-feedback-skip {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

db.init_db()
try:
    ql = QuizLoader()
except FileNotFoundError as e:
    st.error(f"❌ {e}")
    st.info("👉 Google Drive에서 quiz_data.json을 다운로드한 후 `data/` 폴더에 넣어주세요.")
    st.stop()

if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.q_idx = 0
    st.session_state.answers = {}

st.markdown('<div class="main-title">📊 CFA Level 1 Study Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="title-sub">SchweserNotes 2022 기반 · 5권 PDF · 문제은행 · 진도 추적</div>', unsafe_allow_html=True)
st.divider()

cl = ConceptLoader()

tab_quiz, tab_concept, tab_progress, tab_wrong = st.tabs(["📝 문제 풀이", "📖 개념 정리", "📈 진도 현황", "📕 오답 노트"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1: 문제 풀이
# ════════════════════════════════════════════════════════════════════════════
with tab_quiz:
    col_setting, col_quiz = st.columns([1, 3])

    with col_setting:
        st.subheader("⚙️ 설정")

        avail_modules = ql.available_modules()
        selected_module = st.selectbox("모듈 선택", ["전체"] + avail_modules)

        if selected_module != "전체":
            topics = ["전체"] + list(ql.topics_for_module(selected_module).keys())
            selected_topic = st.selectbox("토픽 선택", topics)
        else:
            selected_topic = "전체"

        question_count = st.slider("문제 수", 5, 50, 10)

        if st.button("🔄 새 문제 세트 시작", use_container_width=True, type="primary"):
            module = selected_module if selected_module != "전체" else None
            topic = selected_topic if selected_topic != "전체" else None
            st.session_state.questions = ql.get_questions(module, topic, question_count)
            st.session_state.q_idx = 0
            st.session_state.answers = {}
            st.rerun()

    with col_quiz:
        if not st.session_state.questions:
            st.markdown("""
            <div class="callout-card">
                <div style="font-size:3rem; margin-bottom:0.5rem;">📋</div>
                <div style="font-size:1.1rem; font-weight:600; color:#334155;">왼쪽에서 설정을 선택하세요</div>
                <div style="color:#94a3b8; margin-top:0.3rem;">모듈 · 토픽 · 문제 수를 고르고 시작 버튼을 눌러주세요</div>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.questions:
            qs = st.session_state.questions
            idx = st.session_state.q_idx
            total = len(qs)

            if idx >= total:
                correct = sum(1 for a in st.session_state.answers.values() if a.get("is_correct"))
                total_answered = len(st.session_state.answers)
                pct = correct / max(total_answered, 1) * 100

                st.balloons()
                st.markdown("""
                <div class="quiz-result-box">
                    <h2>🎉 세트 완료!</h2>
                    <div style="font-size:3rem; font-weight:800; margin:0.5rem 0;">{correct}/{total_answered}</div>
                    <div style="font-size:1.2rem; opacity:0.9;">{pct:.0f}% 정답률</div>
                </div>
                """.format(correct=correct, total_answered=total_answered, pct=pct), unsafe_allow_html=True)

                if total_answered > 0:
                    df = pd.DataFrame([
                        {"모듈": a.get("module", "?"), "결과": "✅" if a["is_correct"] else "❌"}
                        for a in st.session_state.answers.values()
                    ])
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(df["모듈"].value_counts(), use_container_width=True)

                if st.button("🔄 다시 시작", use_container_width=True):
                    st.session_state.questions = []
                    st.session_state.q_idx = 0
                    st.session_state.answers = {}
                    st.rerun()
            else:
                q = qs[idx]
                st.progress((idx + 1) / total, text=f"**{idx + 1} / {total}**")

                mod = q.get("fallback_module", q.get("topic", "?"))
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"### Q{idx + 1}")
                    st.markdown(q["text"])
                with col_b:
                    st.markdown(
                        f"<span class='module-badge' style='background:{MODULE_COLORS.get(mod, '#6B7280')};'>"
                        f"{mod}</span>",
                        unsafe_allow_html=True
                    )
                    st.caption(f"Book {q.get('book', '?')} | #{q.get('num', '?')}")

                st.divider()

                options = list(q.get("options", {}).values())

                already_answered = idx in st.session_state.answers
                disabled = already_answered

                selected = st.radio(
                    "정답을 고르세요:",
                    options,
                    key=f"radio_{idx}",
                    index=None,
                    disabled=disabled,
                )

                col_submit, col_skip = st.columns([1, 1])

                with col_submit:
                    if st.button("✅ 제출", type="primary", disabled=disabled or not selected, use_container_width=True):
                        if selected:
                            correct_key = q.get("answer", "A")
                            correct_text = q["options"].get(correct_key, options[0] if options else "")

                            is_correct = selected == correct_text
                            st.session_state.answers[idx] = {
                                "selected": selected,
                                "correct": correct_text,
                                "correct_key": correct_key,
                                "is_correct": is_correct,
                                "module": mod,
                                "topic": q.get("fallback_topic", q.get("topic", "?")),
                            }

                            db.save_attempt(
                                q.get("book", 1), q.get("reading_num", 0),
                                q.get("num", 0), q["text"],
                                selected, correct_text,
                                mod, q.get("topic", "?")
                            )
                            st.rerun()

                with col_skip:
                    if st.button("⏭️ 건너뛰기", use_container_width=True):
                        st.session_state.answers[idx] = {
                            "selected": "skipped",
                            "correct": "",
                            "correct_key": "",
                            "is_correct": False,
                            "module": mod,
                            "topic": q.get("fallback_topic", q.get("topic", "?")),
                        }
                        st.rerun()

                if already_answered:
                    ans = st.session_state.answers[idx]
                    st.divider()

                    if ans["is_correct"]:
                        st.markdown(f"""
                        <div class="quiz-feedback-correct">
                            <strong>✅ 정답!</strong> ({ans['correct_key']}) {ans['correct']}
                        </div>
                        """, unsafe_allow_html=True)
                    elif ans["selected"] == "skipped":
                        correct_key = q.get("answer", "A")
                        correct_text = q["options"].get(correct_key, "")
                        st.markdown(f"""
                        <div class="quiz-feedback-skip">
                            <strong>⏭️ 건너뜀</strong> · 정답: <strong>{correct_key}. {correct_text}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="quiz-feedback-wrong">
                            <strong>❌ 오답</strong><br>
                            정답: <strong>{ans['correct_key']}. {ans['correct']}</strong>
                        </div>
                        """, unsafe_allow_html=True)

                    col_next, col_bm = st.columns([1, 1])
                    with col_next:
                        if st.button("➡️ 다음 문제", type="primary", use_container_width=True):
                            st.session_state.q_idx += 1
                            st.rerun()
                    with col_bm:
                        if st.button("⭐ 북마크", use_container_width=True):
                            db.add_bookmark(
                                q.get("book", 1), q.get("reading_num", 0), q.get("num", 0)
                            )
                            st.toast("📌 북마크에 추가됨!")


# ════════════════════════════════════════════════════════════════════════════
# TAB 4: 개념 정리
# ════════════════════════════════════════════════════════════════════════════
with tab_concept:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
        <div style="font-size:1.8rem;">📖</div>
        <div>
            <div style="font-size:1.5rem; font-weight:700; color:#0a1628;">개념 정리</div>
            <div style="color:#64748b; font-size:0.9rem;">SchweserNotes 2024 기반 · Reading별 요약</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        concept_modules = cl.available_modules()
    except Exception:
        concept_modules = module_names()

    sel_module = st.selectbox("📚 모듈 선택", concept_modules, key="concept_module")

    try:
        data = cl.get_sections(sel_module)
    except Exception as e:
        st.error(f"개념 데이터를 불러오지 못했습니다: {e}")
        data = {}

    mod_color = MODULE_COLORS.get(sel_module, "#6B7280")

    # ── Module header ──
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin:0 0 16px 0;">
        <div style="background:{mod_color}; width:4px; height:32px; border-radius:2px;"></div>
        <div style="font-size:1.2rem; font-weight:700; color:{mod_color};">{sel_module}</div>
    </div>
    """, unsafe_allow_html=True)

    source = data.get("_source", "unknown")
    reading_summaries = data.get("reading_summaries", [])
    summary = data.get("summary", "")
    topics = data.get("topics", [])
    los_flat = data.get("los", [])
    formulas = data.get("formulas", [])
    exam_tips = data.get("exam_tips", [])

    # ════════════════════════════════════════════════════════════════════════
    # READING SUMMARIES VIEW — Reading별 요약 (when reading_summaries.json exists)
    # ════════════════════════════════════════════════════════════════════════
    if source == "reading_summaries" and reading_summaries:
        # Summary card (from enhanced source if available)
        if summary:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #f0f4ff 0%, #e8eef7 100%);
                        border:1px solid #d0d9e8; border-radius:12px; padding:16px 20px; margin-bottom:20px;">
                <div style="color:#334155; line-height:1.6; font-size:0.92rem;">{summary}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="color:#94a3b8; font-size:0.8rem; margin-bottom:12px;">
            {len(reading_summaries)}개 Reading
        </div>
        """, unsafe_allow_html=True)

        # Render each reading as a card
        for idx, reading in enumerate(reading_summaries):
            rnum = reading.get("reading_num", idx + 1)
            title = reading.get("title", f"Reading {rnum}")
            summary_text = reading.get("summary", "")
            key_points = reading.get("key_points", [])

            is_expanded = idx == 0  # First reading auto-expanded
            card_id = f"reading_{sel_module}_{rnum}"

            # Clean title: remove "Module X.Y:" prefix for cleaner display
            display_title = re.sub(r'\s*Module\s+\d+\.\d+:\s*', '', title)
            display_title = re.sub(r'\s*Introduction\s*$', '', display_title)
            # Also clean up the "READING N" prefix
            display_title = re.sub(r'^READING\s+\d+\s+', '', display_title)
            display_title = display_title.strip()

            # Card container
            st.markdown(f"""
            <div style="background:white; border:1px solid #e2e8f0; border-radius:12px;
                        padding:0; margin-bottom:12px; overflow:hidden;
                        box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="display:flex; align-items:center; gap:10px;
                            background:linear-gradient(90deg, {mod_color}08 0%, {mod_color}02 100%);
                            padding:12px 16px; border-bottom:1px solid #e2e8f0;
                            cursor:pointer;"
                     onclick="document.getElementById('{card_id}_body').style.display =
                              document.getElementById('{card_id}_body').style.display === 'none' ? 'block' : 'none';
                              this.querySelector('.toggle-icon').textContent =
                              this.querySelector('.toggle-icon').textContent === '▶' ? '▼' : '▶';">
                    <span style="background:{mod_color}; color:white; font-size:0.75rem; font-weight:700;
                                 padding:2px 10px; border-radius:8px; flex-shrink:0;">R{rnum}</span>
                    <span style="font-size:0.95rem; font-weight:600; color:#0a1628; flex:1;">{display_title}</span>
                    <span class="toggle-icon" style="color:{mod_color}; font-size:0.8rem;">{'▼' if is_expanded else '▶'}</span>
                </div>
                <div id="{card_id}_body" style="padding:16px 20px; display:{'block' if is_expanded else 'none'};">
            """, unsafe_allow_html=True)

            # Key points — 한글 문서 스타일 2단 그리드
            if key_points:
                st.markdown(f"""
                <div style="margin:14px 0 8px 0; border-bottom:2px solid {mod_color}; padding-bottom:4px;">
                    <span style="font-weight:700; color:#0a1628; font-size:0.95rem;">🔑 핵심 포인트</span>
                </div>
                """, unsafe_allow_html=True)

                # 2-column grid
                half = (len(key_points) + 1) // 2
                for row_idx in range(half):
                    cols = st.columns(2)
                    for col_idx in range(2):
                        pt_idx = row_idx * 2 + col_idx
                        if pt_idx < len(key_points):
                            pt = key_points[pt_idx]
                            with cols[col_idx]:
                                st.markdown(f"""
                                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:3px solid {mod_color};
                                            border-radius:6px; padding:8px 12px; margin-bottom:6px; min-height:48px;
                                            display:flex; align-items:center;">
                                    <span style="color:{mod_color}; font-size:0.78rem; font-weight:700; margin-right:6px;">•</span>
                                    <span style="color:#334155; font-size:0.85rem; line-height:1.5;">{_md_inline(pt)}</span>
                                </div>
                                """, unsafe_allow_html=True)

            # Summary — always render as markdown (supports ##headers, **bold**, tables, bullets)
            if summary_text:
                st.markdown(f"""
                <div style="margin:14px 0 8px 0; border-bottom:2px solid {mod_color}; padding-bottom:4px;">
                    <span style="font-weight:700; color:#0a1628; font-size:0.95rem;">📝 상세 설명</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(summary_text)

            # Close card body
            st.markdown("</div></div>", unsafe_allow_html=True)

        # ── LOS (참고용) ──
        if los_flat:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">🎯</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">LOS (참고)</span>
                <span style="background:#0a162818; color:#0a1628; padding:2px 10px; border-radius:10px;
                             font-size:0.75rem; font-weight:600;">{len(los_flat)}개</span>
            </div>
            """, unsafe_allow_html=True)

            for i, lo in enumerate(los_flat, 1):
                st.markdown(f"""
                <div style="border-left:3px solid {mod_color}44; padding:6px 12px; margin-bottom:4px;
                            background:#f8fafc; border-radius:0 6px 6px 0;">
                    <span style="color:#64748b; font-size:0.78rem; font-weight:600;">LOS {i}</span>
                    <span style="color:#475569; font-size:0.85rem; margin-left:6px;">{lo}</span>
                </div>
                """, unsafe_allow_html=True)

        # ── Formulas ──
        if formulas:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">📐</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">주요 공식</span>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns(2)
            for i, formula in enumerate(formulas, 1):
                with cols[(i - 1) % 2]:
                    if isinstance(formula, list) and len(formula) >= 2:
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #e2e8f0; border-radius:8px;
                                    padding:10px 14px; margin-bottom:8px;">
                            <div style="font-size:0.72rem; color:#64748b; font-weight:600;
                                        text-transform:uppercase; margin-bottom:2px;">{formula[0]}</div>
                            <div style="color:#1e293b; font-size:0.88rem; font-family:monospace;
                                        background:#f8fafc; border-radius:4px; padding:4px 8px;">{formula[1]}</div>
                        </div>
                        """, unsafe_allow_html=True)

        # ── Exam Tips ──
        if exam_tips:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">💡</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">시험 꿀팁</span>
            </div>
            """, unsafe_allow_html=True)

            for tip in exam_tips:
                tip_text = tip if isinstance(tip, str) else tip.get("tip", tip.get("content", ""))
                if not tip_text:
                    continue
                st.markdown(f"""
                <div style="background:#fffbeb; border:1px solid #fde68a; border-left:3px solid #f59e0b;
                            border-radius:8px; padding:8px 14px; margin-bottom:6px;">
                    <span style="color:#92400e; font-size:0.88rem;">{tip_text}</span>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # STRUCTURED VIEW — topics with per-LOS cards (when structured_concepts.json exists)
    # ════════════════════════════════════════════════════════════════════════
    elif source == "structured" and topics:
        total_los = sum(len(t.get("los_items", [])) for t in topics)
        st.markdown(f"""
        <div style="color:#94a3b8; font-size:0.8rem; margin-bottom:12px;">
            {len(topics)}개 토픽 &nbsp;·&nbsp; {total_los}개 LOS
        </div>
        """, unsafe_allow_html=True)

        for topic in topics:
            topic_name = topic.get("name", "")
            los_items = topic.get("los_items", [])
            if not los_items:
                continue

            # Topic section header
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:8px; margin:20px 0 8px 0;">
                <div style="background:{mod_color}; width:3px; height:20px; border-radius:2px; flex-shrink:0;"></div>
                <span style="font-size:1.05rem; font-weight:700; color:#0a1628;">{topic_name}</span>
                <span style="background:{mod_color}18; color:{mod_color}; font-size:0.72rem; font-weight:600;
                             padding:2px 10px; border-radius:10px;">{len(los_items)} LOS</span>
            </div>
            """, unsafe_allow_html=True)

            for item in los_items:
                los_text = item.get("los", "")
                explanation = item.get("explanation", "")
                key_points = item.get("key_points", [])

                # Derive action verb for color badge
                words = los_text.replace(":", " ").split()
                action = ""
                for w in words:
                    if w[0].isupper() and w not in ("LOS",):
                        action = w
                        break
                fg, bg = _LOS_ACTION_COLORS.get(action, ("#475569", "#f1f5f9"))

                # Short label for expander header
                colon_idx = los_text.find(":")
                short = los_text[colon_idx + 1:].strip() if colon_idx != -1 else los_text
                if len(short) > 100:
                    short = short[:100] + "…"

                with st.expander(short, expanded=False):
                    # LOS statement
                    st.markdown(f"""
                    <div style="background:#f8fafc; border-left:3px solid {fg};
                                border-radius:0 8px 8px 0; padding:10px 14px; margin-bottom:12px;">
                        <span style="background:{bg}; color:{fg}; font-size:0.7rem; font-weight:700;
                                     padding:1px 8px; border-radius:8px; margin-right:8px;">{action.upper() or "LOS"}</span>
                        <span style="color:#334155; font-size:0.88rem;">{los_text}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    # Explanation
                    if explanation:
                        st.markdown(f"""
                        <div style="color:#1e293b; font-size:0.92rem; line-height:1.7; margin-bottom:12px;">
                            {explanation}
                        </div>
                        """, unsafe_allow_html=True)

                    # Key points
                    if key_points:
                        bullets_html = "".join(
                            f'<li style="color:#334155; font-size:0.88rem; margin-bottom:4px;">{p}</li>'
                            for p in key_points
                        )
                        st.markdown(f"""
                        <ul style="margin:0; padding-left:20px; list-style-type:disc;">
                            {bullets_html}
                        </ul>
                        """, unsafe_allow_html=True)

        # ── Formulas ──
        if formulas:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">📐</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">주요 공식</span>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns(2)
            for i, formula in enumerate(formulas, 1):
                with cols[(i - 1) % 2]:
                    if isinstance(formula, list) and len(formula) >= 2:
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #e2e8f0; border-radius:8px;
                                    padding:10px 14px; margin-bottom:8px;">
                            <div style="font-size:0.72rem; color:#64748b; font-weight:600;
                                        text-transform:uppercase; margin-bottom:2px;">{formula[0]}</div>
                            <div style="color:#1e293b; font-size:0.88rem; font-family:monospace;
                                        background:#f8fafc; border-radius:4px; padding:4px 8px;">{formula[1]}</div>
                        </div>
                        """, unsafe_allow_html=True)

        # ── Exam Tips ──
        if exam_tips:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">💡</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">시험 꿀팁</span>
            </div>
            """, unsafe_allow_html=True)

            for tip in exam_tips:
                tip_text = tip if isinstance(tip, str) else tip.get("tip", tip.get("content", ""))
                if not tip_text:
                    continue
                st.markdown(f"""
                <div style="background:#fffbeb; border:1px solid #fde68a; border-left:3px solid #f59e0b;
                            border-radius:8px; padding:8px 14px; margin-bottom:6px;">
                    <span style="color:#92400e; font-size:0.88rem;">{tip_text}</span>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # FALLBACK VIEW — flat LOS list (enhanced_concepts.json source)
    # ════════════════════════════════════════════════════════════════════════
    elif los_flat:
        st.markdown(f"""
        <div style="background:#fef9c3; border:1px solid #fde047; border-radius:8px;
                    padding:8px 14px; margin-bottom:16px; font-size:0.82rem; color:#713f12;">
            더 나은 학습 경험을 위해 <code>python scripts/generate_structured_concepts.py</code>를 실행하세요.
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:16px;">
            <span style="font-weight:700; color:#0a1628; font-size:1.1rem;">Learning Outcomes (LOS)</span>
            <span style="background:#0a162818; color:#0a1628; padding:2px 10px; border-radius:10px;
                         font-size:0.75rem; font-weight:600;">{len(los_flat)}개</span>
        </div>
        """, unsafe_allow_html=True)

        for i, lo in enumerate(los_flat, 1):
            words = lo.replace(":", " ").split()
            action = next((w for w in words if w[0].isupper() and w != "LOS"), "")
            fg, bg = _LOS_ACTION_COLORS.get(action, ("#475569", "#f1f5f9"))
            short = lo if len(lo) <= 110 else lo[:110] + "…"

            with st.expander(f"**LOS {i}** — {short}", expanded=False):
                st.markdown(f"""
                <div style="border-left:3px solid {fg}; padding-left:14px;">
                    <span style="background:{bg}; color:{fg}; font-size:0.7rem; font-weight:700;
                                 padding:1px 8px; border-radius:8px; margin-right:8px;">{action.upper() or "LOS"}</span>
                    <span style="color:#1e293b; font-size:0.95rem; line-height:1.7;">{lo}</span>
                </div>
                """, unsafe_allow_html=True)

        # ── Formulas ──
        if formulas:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">📐</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">주요 공식</span>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns(2)
            for i, formula in enumerate(formulas, 1):
                with cols[(i - 1) % 2]:
                    if isinstance(formula, list) and len(formula) >= 2:
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #e2e8f0; border-radius:8px;
                                    padding:10px 14px; margin-bottom:8px;">
                            <div style="font-size:0.72rem; color:#64748b; font-weight:600;
                                        text-transform:uppercase; margin-bottom:2px;">{formula[0]}</div>
                            <div style="color:#1e293b; font-size:0.88rem; font-family:monospace;
                                        background:#f8fafc; border-radius:4px; padding:4px 8px;">{formula[1]}</div>
                        </div>
                        """, unsafe_allow_html=True)

        # ── Exam Tips ──
        if exam_tips:
            st.divider()
            st.markdown("""
            <div style="display:flex; align-items:center; gap:8px; margin:4px 0 10px 0;">
                <span style="font-size:1rem;">💡</span>
                <span style="font-weight:700; color:#0a1628; font-size:1.05rem;">시험 꿀팁</span>
            </div>
            """, unsafe_allow_html=True)

            for tip in exam_tips:
                tip_text = tip if isinstance(tip, str) else tip.get("tip", tip.get("content", ""))
                if not tip_text:
                    continue
                st.markdown(f"""
                <div style="background:#fffbeb; border:1px solid #fde68a; border-left:3px solid #f59e0b;
                            border-radius:8px; padding:8px 14px; margin-bottom:6px;">
                    <span style="color:#92400e; font-size:0.88rem;">{tip_text}</span>
                </div>
                """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2: 진도 현황
# ════════════════════════════════════════════════════════════════════════════
with tab_progress:
    st.subheader("📊 모듈별 진도 현황")

    progress = db.get_progress()
    if progress:
        total_attempts = sum(p["total"] for p in progress)
        total_correct = sum(p["correct"] for p in progress)
        overall_pct = round(total_correct / max(total_attempts, 1) * 100, 1)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("총 문제", total_attempts)
        col_m2.metric("정답", total_correct)
        col_m3.metric("정답률", f"{overall_pct}%")

        st.divider()

        df = pd.DataFrame(progress)
        df.columns = ["모듈", "시도", "정답 수", "정답률(%)"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("📈 모듈별 정답률")
        for p in progress:
            color = MODULE_COLORS.get(p["module"], "#6B7280")
            st.markdown(f"**{p['module']}** — {p['pct']}% ({p['correct']}/{p['total']})")
            st.progress(p["pct"] / 100, text="")
    else:
        st.info("📊 아직 푼 문제가 없습니다. '문제 풀이' 탭에서 시작하세요!")

    st.divider()
    st.subheader("📚 문제은행 현황")
    stats = ql.stats()
    total_qs = sum(m["total_questions"] for m in stats.values())
    st.metric("전체 문제 수", total_qs)
    st.dataframe(
        pd.DataFrame([
            {"모듈": mod, "문제 수": info["total_questions"],
             "토픽 수": len(info["topics"])}
            for mod, info in sorted(stats.items())
        ]),
        use_container_width=True, hide_index=True
    )


# ════════════════════════════════════════════════════════════════════════════
# TAB 3: 오답 노트
# ════════════════════════════════════════════════════════════════════════════
with tab_wrong:
    st.subheader("📕 오답 노트")
    st.caption("틀렸거나 건너뛴 문제들을 모아서 복습할 수 있습니다.")

    wrong_modules = ["전체"] + avail_modules
    selected_wrong_module = st.selectbox("모듈 필터", wrong_modules, key="wrong_mod")

    module_param = selected_wrong_module if selected_wrong_module != "전체" else None
    wrong = db.get_wrong_answers(module=module_param, limit=100)

    if wrong:
        st.info(f"📌 총 {len(wrong)}개의 오답/건너뜀 항목")

        for i, w in enumerate(wrong[:50]):
            q_text = w["question_text"][:120] + ("..." if len(w["question_text"]) > 120 else "")
            with st.expander(f"❌ {q_text}", expanded=i == 0):
                st.markdown(f"**문제:** {w['question_text']}")
                st.divider()
                selected_display = w["selected"] if w["selected"] != "skipped" else "⏭️ 건너뜀"
                st.markdown(f"**선택한 답:** {selected_display}")
                if w["correct"]:
                    st.markdown(f"**정답:** ✅ {w['correct']}")
                st.divider()
                st.caption(f"📁 {w['module']} | Book {w['book']} | Reading {w['reading_num']} | {w['timestamp'][:10]}")

        if len(wrong) > 50:
            st.info(f"...외 {len(wrong) - 50}개 더 있음")

        st.divider()
        if st.button("🗑️ 오답 기록 초기화", type="secondary"):
            db.clear_attempts()
            st.rerun()
    else:
        st.success("🎉 아직 틀린 문제가 없습니다! 계속 좋은 페이스로 가세요!")
