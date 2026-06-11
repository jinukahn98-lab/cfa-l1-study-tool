import streamlit as st
import pandas as pd
from quiz_loader import QuizLoader
from modules_l1 import module_names, topics_for_module, module_color, MODULE_COLORS
from concept_loader import ConceptLoader
from flashcard_generator import FlashcardGenerator
import db

st.set_page_config(page_title="CFA Level 1 Study Tool", page_icon="📊", layout="wide")

db.init_db()
try:
    ql = QuizLoader()
except FileNotFoundError as e:
    st.error(f"❌ {e}")
    st.info("👉 Google Drive에서 quiz_data.json을 다운로드한 후 `data/` 폴더에 넣어주세요.")
    st.stop()

# ── Session state init ──────────────────────────────────────────────────────
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.q_idx = 0
    st.session_state.answers = {}

# ── Header ──────────────────────────────────────────────────────────────────
st.title("📊 CFA Level 1 Study Tool")
st.caption("2026 Curriculum 기반 | 문제은행 + 진도 추적")
st.divider()

cl = ConceptLoader()
fg = FlashcardGenerator()

tab1, tab4, tab2, tab3 = st.tabs(["📝 문제 풀이", "📖 개념 정리", "📈 진도 현황", "📕 오답 노트"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1: 문제 풀이
# ════════════════════════════════════════════════════════════════════════════
with tab1:
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
            st.info("👈 설정을 선택하고 '새 문제 세트 시작'을 눌러주세요.")
            st.stop()

        qs = st.session_state.questions
        idx = st.session_state.q_idx
        total = len(qs)

        if idx >= total:
            correct = sum(1 for a in st.session_state.answers.values() if a.get("is_correct"))
            total_answered = len(st.session_state.answers)
            pct = correct / max(total_answered, 1) * 100

            st.balloons()
            st.success(f"## 🎉 세트 완료!")
            st.metric("정답", f"{correct}/{total_answered}", f"{pct:.0f}%")

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
            st.stop()

        # ── Current question ────────────────────────────────────────────────
        q = qs[idx]
        st.progress((idx + 1) / total, text=f"**{idx + 1} / {total}**")

        # Question header
        mod = q.get("fallback_module", q.get("topic", "?"))
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown(f"### Q{idx + 1}")
            st.markdown(q["text"])
        with col_b:
            st.markdown(
                f"<span style='background:{MODULE_COLORS.get(mod, '#6B7280')}; "
                f"padding:2px 8px; border-radius:10px; color:white; font-size:0.8em;'>"
                f"{mod}</span>",
                unsafe_allow_html=True
            )
            st.caption(f"Book {q.get('book', '?')} | #{q.get('num', '?')}")

        st.divider()

        # Options
        options = list(q.get("options", {}).values())
        opt_keys = list(q.get("options", {}).keys())

        # Check if already answered
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

        # Show result after answering
        if already_answered:
            ans = st.session_state.answers[idx]
            st.divider()

            if ans["is_correct"]:
                st.success(f"✅ **정답!** ({ans['correct_key']}) {ans['correct']}")
            elif ans["selected"] == "skipped":
                correct_key = q.get("answer", "A")
                correct_text = q["options"].get(correct_key, "")
                st.warning(f"⏭️ 건너뜀. 정답: **{correct_key}. {correct_text}**")
            else:
                st.error(f"❌ **오답.**")
                st.info(f"정답: **{ans['correct_key']}. {ans['correct']}**")

            # Bookmark + next
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
with tab4:
    col_nav, col_content = st.columns([1, 3])

    with col_nav:
        st.subheader("📚 모듈")
        concept_modules = cl.available_modules()
        selected_concept_module = st.selectbox(
            "모듈 선택",
            concept_modules,
            key="concept_module",
        )
        view_mode = st.radio(
            "보기 모드",
            ["개념요약", "핵심공식", "시험팁", "LOS", "플래시카드"],
            key="concept_view_mode",
        )

    with col_content:
        sections = cl.get_sections(selected_concept_module)

        if view_mode == "개념요약":
            st.subheader(f"📖 {selected_concept_module} — 개념 요약")
            st.markdown(sections["summary"])
            if sections["key_concepts"]:
                st.divider()
                st.subheader("🔑 핵심 개념")
                for concept in sections["key_concepts"]:
                    st.markdown(f"- {concept}")

        elif view_mode == "핵심공식":
            st.subheader(f"🧮 {selected_concept_module} — 핵심 공식")
            formulas = sections["formulas"]
            if formulas:
                for name, formula in formulas:
                    with st.container():
                        st.markdown(f"**{name}**")
                        st.code(formula, language=None)
            else:
                st.info("이 모듈에는 공식이 없습니다.")

        elif view_mode == "시험팁":
            st.subheader(f"💡 {selected_concept_module} — 시험 팁")
            tips = sections["exam_tips"]
            if tips:
                for i, tip in enumerate(tips, 1):
                    st.info(f"**팁 {i}.** {tip}")
            else:
                st.info("이 모듈에는 시험 팁이 없습니다.")

        elif view_mode == "LOS":
            st.subheader(f"🎯 {selected_concept_module} — 학습 목표 (LOS)")
            los_items = sections["los"]
            if los_items:
                for i, lo in enumerate(los_items, 1):
                    st.markdown(f"**{i}.** {lo}")
            else:
                st.info("이 모듈에는 LOS 정보가 없습니다.")

        elif view_mode == "플래시카드":
            st.subheader(f"🃏 {selected_concept_module} — 플래시카드")

            if not fg.enabled:
                st.warning(
                    "플래시카드 생성을 위해 `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY` "
                    "환경변수를 설정해 주세요."
                )
            else:
                cached = db.get_cached_flashcards(selected_concept_module)

                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    gen_btn = st.button(
                        "✨ 플래시카드 생성" if not cached else "🔄 재생성",
                        type="primary",
                        use_container_width=True,
                    )
                with col_btn2:
                    if cached and st.button("🗑️ 캐시 삭제", use_container_width=True):
                        db.delete_flashcard_cache(selected_concept_module)
                        st.rerun()

                if gen_btn:
                    summary = sections["summary"]
                    key_concepts = "\n".join(f"- {c}" for c in sections["key_concepts"])
                    full_text = f"{summary}\n\n{key_concepts}"
                    with st.spinner("플래시카드를 생성 중입니다..."):
                        cards = fg.generate(full_text, count=7)
                    if cards is False:
                        st.error("플래시카드 생성에 실패했습니다. API 키를 확인해 주세요.")
                    else:
                        db.save_flashcards(selected_concept_module, cards)
                        cached = cards
                        st.rerun()

                if cached:
                    st.caption(f"총 {len(cached)}개의 플래시카드")
                    for i, card in enumerate(cached, 1):
                        with st.expander(f"Q{i}. {card['question']}"):
                            st.markdown(f"**정답:** {card['answer']}")
                else:
                    st.info("'플래시카드 생성' 버튼을 눌러 AI 플래시카드를 만들어 보세요.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2: 진도 현황
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 모듈별 진도 현황")

    progress = db.get_progress()
    if progress:
        # Summary metrics
        total_attempts = sum(p["total"] for p in progress)
        total_correct = sum(p["correct"] for p in progress)
        overall_pct = round(total_correct / max(total_attempts, 1) * 100, 1)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("총 문제", total_attempts)
        col_m2.metric("정답", total_correct)
        col_m3.metric("정답률", f"{overall_pct}%")

        st.divider()

        # Table
        df = pd.DataFrame(progress)
        df.columns = ["모듈", "시도", "정답 수", "정답률(%)"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # Progress bars with module colors
        st.subheader("📈 모듈별 정답률")
        for p in progress:
            color = MODULE_COLORS.get(p["module"], "#6B7280")
            st.markdown(f"**{p['module']}** — {p['pct']}% ({p['correct']}/{p['total']})")
            st.progress(p["pct"] / 100, text="")

    else:
        st.info("📊 아직 푼 문제가 없습니다. '문제 풀이' 탭에서 시작하세요!")

    # Available questions stats
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
with tab3:
    st.subheader("📕 오답 노트")
    st.caption("틀렸거나 건너뛴 문제들을 모아서 복습할 수 있습니다.")

    # Module filter
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
