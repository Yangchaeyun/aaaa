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

st.divider()
