import json
from datetime import date, datetime, timedelta
from io import StringIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from google import genai
except ImportError:
    genai = None

st.set_page_config(page_title="공부 밸런스 트래커", page_icon="📚", layout="wide")

DEFAULT_SUBJECTS = ["수학", "영어", "국어", "과학", "사회", "기타"]
DEFAULT_GOALS = {subject: 120 for subject in DEFAULT_SUBJECTS}  # minutes per day

def init_state():
    defaults = {
        "subjects": DEFAULT_SUBJECTS.copy(),
        "goals": DEFAULT_GOALS.copy(),
        "sessions": [],
        "active_subject": DEFAULT_SUBJECTS[0],
        "running": False,
        "started_at": None,
        "elapsed_before_pause": 0,
        "pomodoro_mode": "집중 25분",
        "pomodoro_started_at": None,
        "pomodoro_paused_seconds": 0,
        "pomodoro_running": False,
        "daily_target": 6,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

def format_seconds(seconds):
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def session_seconds():
    extra = 0
    if st.session_state.running and st.session_state.started_at:
        extra = (datetime.now() - st.session_state.started_at).total_seconds()
    return int(st.session_state.elapsed_before_pause + extra)

def get_today_df():
    if not st.session_state.sessions:
        return pd.DataFrame(columns=["date", "subject", "seconds", "minutes", "started_at"])
    df = pd.DataFrame(st.session_state.sessions)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df[df["date"] == date.today()].copy()

def all_df():
    if not st.session_state.sessions:
        return pd.DataFrame(columns=["date", "subject", "seconds", "minutes", "started_at"])
    df = pd.DataFrame(st.session_state.sessions)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

st.title("📚 공부 밸런스 트래커")
st.caption("과목별 공부 시간 측정 · 뽀모도로 · 목표 달성률 · Plotly 시각화 · Gemini 학습 코치")
st.info("기록은 현재 브라우저 세션에 저장됩니다. 브라우저 세션이 초기화되기 전에 CSV를 내려받아 보관하세요.")

with st.sidebar:
    st.header("⚙️ 설정")
    new_subject = st.text_input("과목 추가", placeholder="예: 정보")
    if st.button("과목 추가하기", use_container_width=True):
        name = new_subject.strip()
        if name and name not in st.session_state.subjects:
            st.session_state.subjects.append(name)
            st.session_state.goals[name] = 120
            st.success(f"'{name}' 과목을 추가했어요.")
        elif name:
            st.warning("이미 등록된 과목이에요.")
    st.divider()
    st.subheader("오늘의 목표")
    st.session_state.daily_target = st.number_input(
        "총 공부 목표 (시간)", min_value=1, max_value=18,
        value=int(st.session_state.daily_target), step=1
    )
    st.caption("과목별 목표 시간은 아래 '목표 설정' 탭에서 변경할 수 있어요.")

tab_timer, tab_dashboard, tab_goals, tab_pomodoro, tab_coach = st.tabs(
    ["⏱️ 공부 타이머", "📊 대시보드", "🎯 목표 설정", "🍅 뽀모도로", "✨ AI 학습 코치"]
)

with tab_timer:
    st.subheader("과목 선택 후 시작 / 일시정지 / 종료")
    c1, c2 = st.columns([2, 1])
    with c1:
        selected = st.selectbox(
            "공부할 과목", st.session_state.subjects,
            index=st.session_state.subjects.index(st.session_state.active_subject)
            if st.session_state.active_subject in st.session_state.subjects else 0,
            disabled=st.session_state.running
        )
        st.session_state.active_subject = selected
        st.caption("타이머 실행 중에는 과목을 바꿀 수 없어요. 종료 후 다음 과목을 선택하세요.")
    with c2:
        st.metric("현재 측정 시간", format_seconds(session_seconds()))
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("▶ 시작 / 재개", type="primary", use_container_width=True,
                     disabled=st.session_state.running):
            st.session_state.started_at = datetime.now()
            st.session_state.running = True
            st.rerun()
    with b2:
        if st.button("⏸ 일시정지", use_container_width=True,
                     disabled=not st.session_state.running):
            st.session_state.elapsed_before_pause += (datetime.now() - st.session_state.started_at).total_seconds()
            st.session_state.started_at = None
            st.session_state.running = False
            st.rerun()
    with b3:
        if st.button("⏹ 종료 및 기록", use_container_width=True,
                     disabled=(session_seconds() <= 0)):
            seconds = session_seconds()
            started = st.session_state.started_at
            # Use current time for a safe timestamp even after a paused session.
            st.session_state.sessions.append({
                "date": date.today().isoformat(),
                "subject": st.session_state.active_subject,
                "seconds": int(seconds),
                "minutes": round(seconds / 60, 2),
                "started_at": (started or datetime.now()).isoformat(timespec="seconds"),
            })
            st.session_state.running = False
            st.session_state.started_at = None
            st.session_state.elapsed_before_pause = 0
            st.success(f"{st.session_state.active_subject}: {format_seconds(seconds)} 기록 완료!")
            st.rerun()
    if st.session_state.running:
        st.warning("타이머가 실행 중입니다. 화면을 주기적으로 새로고침하면 표시 시간이 갱신됩니다.")
        st.button("🔄 시간 갱신", on_click=st.rerun)
    st.markdown("**최근 학습 기록**")
    recent = all_df().sort_values("started_at", ascending=False).head(10) if not all_df().empty else all_df()
    if recent.empty:
        st.write("아직 기록이 없어요. 시작 버튼을 눌러 첫 공부 기록을 만들어 보세요.")
    else:
        st.dataframe(recent[["date", "subject", "minutes", "started_at"]], use_container_width=True, hide_index=True)
    if not all_df().empty:
        csv = all_df().to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 전체 학습 기록 CSV 다운로드", data=csv, file_name="study_records.csv",
                           mime="text/csv", use_container_width=True)

with tab_dashboard:
    st.subheader("오늘의 공부 현황")
    today = get_today_df()
    today_minutes = today.groupby("subject")["minutes"].sum().to_dict() if not today.empty else {}
    total_minutes = float(sum(today_minutes.values()))
    target_minutes = int(st.session_state.daily_target) * 60
    progress = min(total_minutes / target_minutes, 1.0) if target_minutes else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("오늘 총 공부", f"{total_minutes / 60:.1f}시간")
    m2.metric("일일 목표 달성률", f"{progress * 100:.1f}%")
    m3.metric("기록한 세션", f"{len(today)}회")
    st.progress(progress, text=f"일일 목표 {st.session_state.daily_target}시간 중 {total_minutes/60:.1f}시간")
    if today.empty or total_minutes == 0:
        st.info("공부 타이머에서 기록을 추가하면 그래프가 표시됩니다.")
    else:
        left, right = st.columns(2)
        pie_df = pd.DataFrame({"과목": list(today_minutes.keys()), "공부 시간(분)": list(today_minutes.values())})
        with left:
            fig = px.pie(pie_df, names="과목", values="공부 시간(분)", hole=0.45,
                         title="과목별 공부 시간 비율")
            fig.update_traces(textposition="inside", textinfo="label+percent")
            st.plotly_chart(fig, use_container_width=True)
        with right:
            goal_df = pd.DataFrame([
                {"과목": subject, "실제 공부(분)": float(today_minutes.get(subject, 0)),
                 "목표 공부(분)": float(st.session_state.goals.get(subject, 120))}
                for subject in st.session_state.subjects
            ])
            fig = go.Figure()
            fig.add_bar(name="실제 공부", x=goal_df["과목"], y=goal_df["실제 공부(분)"])
            fig.add_bar(name="목표 공부", x=goal_df["과목"], y=goal_df["목표 공부(분)"])
            fig.update_layout(barmode="group", title="과목별 목표 대비 공부 시간", yaxis_title="분")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("**과목별 목표 달성률**")
        attainment = []
        for subject in st.session_state.subjects:
            goal = float(st.session_state.goals.get(subject, 120))
            actual = float(today_minutes.get(subject, 0))
            attainment.append({"과목": subject, "실제(분)": round(actual, 1),
                               "목표(분)": goal, "달성률(%)": round(actual / goal * 100, 1) if goal else 0})
        attainment_df = pd.DataFrame(attainment)
        fig = px.bar(attainment_df, x="과목", y="달성률(%)", color="달성률(%)",
                     title="과목별 목표 달성률", text="달성률(%)")
        fig.add_hline(y=100, line_dash="dash", annotation_text="목표 100%")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(attainment_df, use_container_width=True, hide_index=True)

    history = all_df()
    if not history.empty:
        st.markdown("**날짜별 공부 시간 추이**")
        trend = history.groupby(["date", "subject"], as_index=False)["minutes"].sum()
        fig = px.line(trend, x="date", y="minutes", color="subject", markers=True,
                      title="날짜별 과목 공부 시간", labels={"date": "날짜", "minutes": "공부 시간(분)", "subject": "과목"})
        st.plotly_chart(fig, use_container_width=True)

with tab_goals:
    st.subheader("과목별 목표 시간과 D-Day")
    exam_date = st.date_input("시험 / 목표 날짜", value=date.today() + timedelta(days=30), min_value=date.today())
    days_left = (exam_date - date.today()).days
    st.metric("D-Day", f"D-{days_left}" if days_left else "D-Day!")
    st.caption("목표 시간은 하루 기준 분 단위입니다.")
    goal_values = {}
    cols = st.columns(2)
    for i, subject in enumerate(st.session_state.subjects):
        with cols[i % 2]:
            goal_values[subject] = st.number_input(
                f"{subject} 하루 목표(분)", min_value=0, max_value=1440,
                value=int(st.session_state.goals.get(subject, 120)), step=15, key=f"goal_{subject}"
            )
    if st.button("목표 저장", type="primary"):
        st.session_state.goals.update(goal_values)
        st.success("과목별 목표를 저장했어요.")
    st.divider()
    st.markdown("**계산식 시각화**")
    st.latex(r"\text{과목별 달성률} = \frac{\text{실제 공부 시간}}{\text{목표 공부 시간}} \times 100\%")
    st.latex(r"\text{D-Day까지 필요한 하루 공부량} = \frac{\text{남은 목표 공부량}}{\text{남은 날짜 수}}")
    st.caption("현재 기록만으로 남은 전체 공부량을 추정할 수는 없으므로, 아래 그래프는 하루 목표 시간과 오늘 실제 시간을 비교합니다.")
    today = get_today_df()
    minutes_by_subject = today.groupby("subject")["minutes"].sum().to_dict() if not today.empty else {}
    rows = []
    for subject in st.session_state.subjects:
        goal = float(st.session_state.goals.get(subject, 120))
        actual = float(minutes_by_subject.get(subject, 0))
        rows.append({"과목": subject, "목표(분)": goal, "실제(분)": actual,
                     "달성률(%)": actual / goal * 100 if goal > 0 else 0})
    goal_chart = pd.DataFrame(rows)
    fig = px.scatter(goal_chart, x="목표(분)", y="실제(분)", text="과목", size="달성률(%)",
                     title="목표 시간과 실제 공부 시간의 관계")
    maxval = max(60, float(goal_chart[["목표(분)", "실제(분)"]].max().max()))
    fig.add_trace(go.Scatter(x=[0, maxval], y=[0, maxval], mode="lines",
                             name="목표 달성선", line=dict(dash="dash")))
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

with tab_pomodoro:
    st.subheader("🍅 뽀모도로 타이머")
    mode = st.radio("모드", ["집중 25분", "짧은 휴식 5분", "긴 휴식 15분"], horizontal=True,
                    index=["집중 25분", "짧은 휴식 5분", "긴 휴식 15분"].index(st.session_state.pomodoro_mode))
    st.session_state.pomodoro_mode = mode
    durations = {"집중 25분": 25 * 60, "짧은 휴식 5분": 5 * 60, "긴 휴식 15분": 15 * 60}
    duration = durations[mode]
    elapsed = st.session_state.pomodoro_paused_seconds
    if st.session_state.pomodoro_running and st.session_state.pomodoro_started_at:
        elapsed += (datetime.now() - st.session_state.pomodoro_started_at).total_seconds()
    remaining = max(0, int(duration - elapsed))
    st.markdown(f"<h1 style='text-align:center;font-size:64px'>{format_seconds(remaining)}</h1>", unsafe_allow_html=True)
    st.progress(min(elapsed / duration, 1.0))
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("▶ 뽀모도로 시작", type="primary", use_container_width=True,
                     disabled=st.session_state.pomodoro_running or remaining == 0):
            st.session_state.pomodoro_started_at = datetime.now()
            st.session_state.pomodoro_running = True
            st.rerun()
    with p2:
        if st.button("⏸ 일시정지", use_container_width=True, disabled=not st.session_state.pomodoro_running):
            st.session_state.pomodoro_paused_seconds += (datetime.now() - st.session_state.pomodoro_started_at).total_seconds()
            st.session_state.pomodoro_started_at = None
            st.session_state.pomodoro_running = False
            st.rerun()
    with p3:
        if st.button("↺ 초기화", use_container_width=True):
            st.session_state.pomodoro_started_at = None
            st.session_state.pomodoro_paused_seconds = 0
            st.session_state.pomodoro_running = False
            st.rerun()
    if remaining == 0:
        st.success("시간이 끝났어요! 다음 모드로 전환하거나 타이머를 초기화하세요.")
    elif st.session_state.pomodoro_running:
        st.caption("시간 표시를 갱신하려면 아래 버튼을 누르세요.")
        st.button("🔄 시간 갱신", key="pomodoro_refresh", on_click=st.rerun)

with tab_coach:
    st.subheader("✨ Gemini AI 학습 코치")
    st.write("오늘 공부 기록을 바탕으로 균형 잡힌 학습 계획과 개선점을 제안받을 수 있어요.")
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        api_key = None
    if not api_key:
        st.warning("Gemini 기능을 사용하려면 Streamlit Secrets에 `GEMINI_API_KEY`를 설정하세요. 나머지 앱 기능은 키 없이 작동합니다.")
    if st.button("학습 분석 요청", type="primary", disabled=not bool(api_key)):
        if genai is None:
            st.error("google-genai 라이브러리를 찾을 수 없어요. requirements.txt를 확인하세요.")
        else:
            today = get_today_df()
            summary = today.groupby("subject")["minutes"].sum().round(1).to_dict() if not today.empty else {}
            goals = {s: st.session_state.goals.get(s, 120) for s in st.session_state.subjects}
            prompt = (
                "너는 친절한 한국어 학습 코치야. 아래 학습 기록을 바탕으로 현실적인 피드백을 작성해줘. "
                "1) 잘한 점 2) 과목 균형 분석 3) 내일의 구체적인 계획 4) 무리하지 않는 조언 순서로 답해줘. "
                "기록에 없는 사실은 추측하지 마.\n"
                f"오늘 과목별 공부 시간(분): {json.dumps(summary, ensure_ascii=False)}\n"
                f"과목별 하루 목표(분): {json.dumps(goals, ensure_ascii=False)}\n"
                f"전체 일일 목표(시간): {st.session_state.daily_target}"
            )
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.markdown(response.text or "응답을 받지 못했어요.")
            except Exception as exc:
                st.error(f"Gemini 요청에 실패했어요. API 키와 사용량 설정을 확인하세요. ({type(exc).__name__})")

st.divider()
st.caption("공부 시간은 기록 보조용이며, 성적이나 학습 성과를 보장하지 않습니다.")
