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

tab_timer, tab_dashboard, tab_goals, tab_pomodoro = st.tabs(
    ["⏱️ 공부 타이머", "📊 대시보드", "🎯 목표 설정", "🍅 뽀모도로"]
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
