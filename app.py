from datetime import date, datetime, timedelta
from io import StringIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

# 과목 선택 위젯의 선택값을 세션 상태에 별도로 보관합니다.
if "study_subject_select" not in st.session_state:
    current_subject = st.session_state.active_subject
    st.session_state.study_subject_select = (
        current_subject if current_subject in st.session_state.subjects
        else st.session_state.subjects[0]
    )

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
st.caption("과목별 공부 시간 측정 · 뽀모도로 · 목표 달성률 · Plotly 시각화")
st.info("기록은 현재 브라우저 세션에 저장됩니다. 브라우저 세션이 초기화되기 전에 CSV를 내려받아 보관하세요.")

with st.sidebar:
    st.header("⚙️ 설정")
    new_subject = st.text_input("과목 추가", placeholder="예: 정보")
    if st.button("과목 추가하기", key="add_subject_button", use_container_width=True):
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

tab_timer, tab_dashboard, tab_goals, tab_pomodoro = st.tabs(
    ["⏱️ 공부 타이머", "📊 대시보드", "🎯 목표 설정", "🍅 뽀모도로"]
)

with tab_timer:
    st.subheader("과목 선택 후 시작 / 일시정지 / 종료")
    c1, c2 = st.columns([2, 1])
    with c1:
        # key로 선택값을 유지하고, 선택된 과목을 타이머 기록에 반영합니다.
        if st.session_state.study_subject_select not in st.session_state.subjects:
            st.session_state.study_subject_select = st.session_state.subjects[0]

        selected = st.selectbox(
            "공부할 과목",
            options=st.session_state.subjects,
            key="study_subject_select",
            disabled=st.session_state.running,
        )
        st.session_state.active_subject = selected
        st.caption("타이머 실행 중에는 과목을 바꿀 수 없어요. 종료 후 다음 과목을 선택하세요.")
    with c2:
        st.metric("현재 측정 시간", format_seconds(session_seconds()))
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("▶ 시작 / 재개", key="study_start_button", type="primary", use_container_width=True,
                     disabled=st.session_state.running):
            st.session_state.started_at = datetime.now()
            st.session_state.running = True
            st.rerun()
    with b2:
        if st.button("⏸ 일시정지", key="study_pause_button", use_container_width=True,
                     disabled=not st.session_state.running):
            st.session_state.elapsed_before_pause += (datetime.now() - st.session_state.started_at).total_seconds()
            st.session_state.started_at = None
            st.session_state.running = False
            st.rerun()
    with b3:
        if st.button("⏹ 종료 및 기록", key="study_finish_button", use_container_width=True,
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
        st.button("🔄 시간 갱신", key="study_refresh_button", on_click=st.rerun)
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
