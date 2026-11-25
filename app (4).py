from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="공부 밸런스 트래커", page_icon="📚", layout="wide")

DEFAULT_SUBJECTS = ["수학", "영어", "국어", "과학", "사회", "기타"]
DEFAULT_GOALS = {subject: 120 for subject in DEFAULT_SUBJECTS}
POMODORO_MODES = {
    "집중 25분": 25 * 60,
    "짧은 휴식 5분": 5 * 60,
    "긴 휴식 15분": 15 * 60,
}


def init_state():
    defaults = {
        "subjects": DEFAULT_SUBJECTS.copy(),
        "goals": DEFAULT_GOALS.copy(),
        "sessions": [],
        "active_subject": DEFAULT_SUBJECTS[0],
        "running": False,
        "started_at": None,
        "elapsed_before_pause": 0.0,
        "daily_target": 6,
        "pomodoro_mode": "집중 25분",
        "pomodoro_started_at": None,
        "pomodoro_paused_seconds": 0.0,
        "pomodoro_running": False,
        "goal_deadline": date.today() + timedelta(days=30),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

if "study_subject_select" not in st.session_state:
    current = st.session_state.active_subject
    st.session_state.study_subject_select = (
        current if current in st.session_state.subjects
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


def pomodoro_total_seconds():
    return POMODORO_MODES[st.session_state.pomodoro_mode]


def pomodoro_elapsed_seconds():
    extra = 0
    if st.session_state.pomodoro_running and st.session_state.pomodoro_started_at:
        extra = (datetime.now() - st.session_state.pomodoro_started_at).total_seconds()
    return int(st.session_state.pomodoro_paused_seconds + extra)


def pomodoro_remaining_seconds():
    return max(0, pomodoro_total_seconds() - pomodoro_elapsed_seconds())


st.title("📚 공부 밸런스 트래커")
st.caption("과목별 공부 시간 측정 · 뽀모도로 · 목표 달성률 · Plotly 시각화")
st.info("기록은 현재 브라우저 세션에 저장됩니다. 브라우저 세션이 초기화되기 전에 CSV를 내려받아 보관하세요.")

with st.sidebar:
    st.header("⚙️ 설정")
    new_subject = st.text_input("과목 추가", placeholder="예: 정보", key="new_subject_input")
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
        value=int(st.session_state.daily_target), step=1, key="daily_target_input"
    )
    st.caption("과목별 목표 시간은 '목표 설정' 탭에서 변경할 수 있어요.")

tab_timer, tab_dashboard, tab_goals, tab_pomodoro = st.tabs(
    ["⏱️ 공부 타이머", "📊 대시보드", "🎯 목표 설정", "🍅 뽀모도로"]
)

with tab_timer:
    st.subheader("과목 선택 후 시작 / 일시정지 / 종료")
    c1, c2 = st.columns([2, 1])
    with c1:
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
        if st.button("▶ 시작 / 재개", key="study_start_button", type="primary",
                     use_container_width=True, disabled=st.session_state.running):
            st.session_state.started_at = datetime.now()
            st.session_state.running = True
            st.rerun()
    with b2:
        if st.button("⏸ 일시정지", key="study_pause_button",
                     use_container_width=True, disabled=not st.session_state.running):
            st.session_state.elapsed_before_pause += (
                datetime.now() - st.session_state.started_at
            ).total_seconds()
            st.session_state.started_at = None
            st.session_state.running = False
            st.rerun()
    with b3:
        if st.button("⏹ 종료 및 기록", key="study_finish_button",
                     use_container_width=True, disabled=(session_seconds() <= 0)):
            seconds = session_seconds()
            st.session_state.sessions.append({
                "date": date.today().isoformat(),
                "subject": st.session_state.active_subject,
                "seconds": int(seconds),
                "minutes": round(seconds / 60, 2),
                "started_at": datetime.now().isoformat(timespec="seconds"),
            })
            st.session_state.running = False
            st.session_state.started_at = None
            st.session_state.elapsed_before_pause = 0.0
            st.success(f"{st.session_state.active_subject}: {format_seconds(seconds)} 기록 완료!")
            st.rerun()

    if st.session_state.running:
        st.warning("타이머가 실행 중입니다. 아래 버튼을 눌러 표시 시간을 갱신할 수 있어요.")
        if st.button("🔄 공부 시간 갱신", key="study_refresh_button"):
            st.rerun()

    st.markdown("**최근 학습 기록**")
    records = all_df()
    recent = records.sort_values("started_at", ascending=False).head(10) if not records.empty else records
    if recent.empty:
        st.write("아직 기록이 없어요. 시작 버튼을 눌러 첫 공부 기록을 만들어 보세요.")
    else:
        st.dataframe(
            recent[["date", "subject", "minutes", "started_at"]],
            use_container_width=True, hide_index=True
        )
        csv_data = records.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 전체 학습 기록 CSV 다운로드",
            data=csv_data,
            file_name="study_records.csv",
            mime="text/csv",
            use_container_width=True,
            key="study_csv_download"
        )

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
    st.progress(progress, text=f"일일 목표 {st.session_state.daily_target}시간 중 {total_minutes / 60:.1f}시간")
    if today.empty or total_minutes == 0:
        st.info("공부 타이머에서 기록을 추가하면 그래프가 표시됩니다.")
    else:
        left, right = st.columns(2)
        pie_df = pd.DataFrame({
            "과목": list(today_minutes.keys()),
            "공부 시간(분)": list(today_minutes.values())
        })
        with left:
            fig = px.pie(
                pie_df, names="과목", values="공부 시간(분)",
                hole=0.45, title="과목별 공부 시간 비율"
            )
            fig.update_traces(textposition="inside", textinfo="label+percent")
            st.plotly_chart(fig, use_container_width=True)
        with right:
            goal_df = pd.DataFrame([
                {
                    "과목": subject,
                    "실제 공부(분)": float(today_minutes.get(subject, 0)),
                    "목표 공부(분)": float(st.session_state.goals.get(subject, 120))
                }
                for subject in st.session_state.subjects
            ])
            fig = go.Figure()
            fig.add_bar(name="실제 공부", x=goal_df["과목"], y=goal_df["실제 공부(분)"])
            fig.add_bar(name="목표 공부", x=goal_df["과목"], y=goal_df["목표 공부(분)"])
            fig.update_layout(
                barmode="group", title="과목별 목표 대비 공부 시간",
                yaxis_title="분"
            )
            st.plotly_chart(fig, use_container_width=True)

with tab_goals:
    st.subheader("과목별 공부 목표 설정")
    st.write("각 과목의 하루 목표 시간을 분 단위로 입력하세요.")
    st.caption("예: 60분은 1시간, 90분은 1시간 30분입니다.")

    goal_cols = st.columns(2)
    for index, subject in enumerate(st.session_state.subjects):
        with goal_cols[index % 2]:
            current_goal = int(st.session_state.goals.get(subject, 120))
            st.session_state.goals[subject] = st.number_input(
                f"{subject} 하루 목표 (분)",
                min_value=0,
                max_value=1440,
                value=current_goal,
                step=10,
                key=f"goal_input_{index}_{subject}"
            )

    st.divider()
    st.subheader("목표 날짜")
    st.session_state.goal_deadline = st.date_input(
        "목표를 달성하고 싶은 날짜",
        value=st.session_state.goal_deadline,
        min_value=date.today(),
        key="goal_deadline_input"
    )
    days_left = (st.session_state.goal_deadline - date.today()).days
    st.metric("목표일까지 남은 기간", f"D-{days_left}")

    today = get_today_df()
    done = today.groupby("subject")["minutes"].sum().to_dict() if not today.empty else {}
    goal_rows = []
    for subject in st.session_state.subjects:
        goal = int(st.session_state.goals.get(subject, 120))
        actual = float(done.get(subject, 0))
        rate = min(actual / goal, 1.0) if goal > 0 else 0.0
        goal_rows.append({
            "과목": subject,
            "목표 시간(분)": goal,
            "실제 공부(분)": round(actual, 1),
            "달성률(%)": round(rate * 100, 1)
        })
    goal_result = pd.DataFrame(goal_rows)
    st.subheader("오늘의 과목별 목표 달성 현황")
    st.dataframe(goal_result, use_container_width=True, hide_index=True)
    if not goal_result.empty:
        fig = px.bar(
            goal_result, x="과목", y="달성률(%)",
            title="과목별 하루 목표 달성률",
            range_y=[0, 100], text="달성률(%)"
        )
        st.plotly_chart(fig, use_container_width=True)
    total_goal = sum(st.session_state.goals.values())
    total_done = sum(done.values())
    overall = min(total_done / total_goal, 1.0) if total_goal > 0 else 0
    st.metric("과목별 목표 전체 달성률", f"{overall * 100:.1f}%")
    st.progress(overall)

with tab_pomodoro:
    st.subheader("집중과 휴식을 반복하는 뽀모도로 타이머")
    st.write("집중 시간과 휴식 시간을 선택한 뒤 시작 버튼을 누르세요.")

    selected_mode = st.selectbox(
        "타이머 모드",
        options=list(POMODORO_MODES.keys()),
        key="pomodoro_mode",
        disabled=st.session_state.pomodoro_running
    )
    total_seconds = pomodoro_total_seconds()
    remaining = pomodoro_remaining_seconds()

    st.metric("남은 시간", format_seconds(remaining))
    st.progress(max(0.0, min(1.0, 1 - remaining / total_seconds)))

    if st.session_state.pomodoro_running and remaining == 0:
        st.session_state.pomodoro_running = False
        st.session_state.pomodoro_started_at = None
        st.session_state.pomodoro_paused_seconds = 0.0
        st.success("타이머가 끝났어요! 잠시 쉬거나 다음 집중 시간을 시작하세요.")
    elif st.session_state.pomodoro_running:
        st.info("타이머가 실행 중입니다. '시간 갱신'을 눌러 남은 시간을 확인하세요.")
    elif st.session_state.pomodoro_paused_seconds > 0:
        st.warning("타이머가 일시정지되어 있습니다.")

    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button(
            "▶ 시작 / 재개",
            key="pomodoro_start_button",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.pomodoro_running
        ):
            st.session_state.pomodoro_started_at = datetime.now()
            st.session_state.pomodoro_running = True
            st.rerun()
    with p2:
        if st.button(
            "⏸ 일시정지",
            key="pomodoro_pause_button",
            use_container_width=True,
            disabled=not st.session_state.pomodoro_running
        ):
            st.session_state.pomodoro_paused_seconds += (
                datetime.now() - st.session_state.pomodoro_started_at
            ).total_seconds()
            st.session_state.pomodoro_started_at = None
            st.session_state.pomodoro_running = False
            st.rerun()
    with p3:
        if st.button(
            "↻ 초기화",
            key="pomodoro_reset_button",
            use_container_width=True
        ):
            st.session_state.pomodoro_started_at = None
            st.session_state.pomodoro_paused_seconds = 0.0
            st.session_state.pomodoro_running = False
            st.rerun()

    if st.session_state.pomodoro_running:
        if st.button("🔄 남은 시간 갱신", key="pomodoro_refresh_button"):
            st.rerun()

    st.caption("화면의 시간이 자동으로 바뀌지 않으면 '남은 시간 갱신' 버튼을 눌러 주세요.")
