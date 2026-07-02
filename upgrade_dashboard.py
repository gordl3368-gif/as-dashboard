import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from urllib.parse import quote

SHEET_ID = "11rqfeZJ-OqvaJoYgFq30PYDQvTS8PuFx8nfJ0Et0bIE"
FORM_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={quote('신청서 접수 현황')}"
MGMT_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={quote('큐라시스2 업그레이드 일정 관리 및 현황 로그')}"

C_MAIN = "#4472C4"
C_DONE = "#70AD47"
C_ING  = "#FFC000"
C_WAIT = "#A9A9A9"
C_WARN = "#FF4B4B"

st.set_page_config(page_title="큐라시스2 업그레이드 현황", page_icon="📋", layout="wide")

st.markdown("""
<meta name="google" content="notranslate">
<meta http-equiv="Content-Language" content="ko">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html, body, [class*="css"], .stApp, button, input, select, textarea {
    font-family: 'Noto Sans KR', 'Malgun Gothic', '맑은 고딕', sans-serif !important;
}
.stage-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


def _fetch_csv(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text), header=0)


@st.cache_data(ttl=60)
def load_form():
    df = _fetch_csv(FORM_URL)
    cols = df.columns.tolist()
    rename = {
        cols[0]:  "접수일시",
        cols[1]:  "동의",
        cols[2]:  "업체명",
        cols[3]:  "담당자명",
        cols[4]:  "연락처",
        cols[5]:  "병원명",
        cols[6]:  "수량",
        cols[7]:  "Lot번호확인",
        cols[8]:  "희망날짜",
        cols[9]:  "내용확인",
        cols[10]: "Score",
        cols[11]: "이메일",
        cols[13]: "견적서발송",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in cols})
    df = df[df["업체명"].notna() & (df["업체명"].astype(str).str.strip() != "")]
    df["접수일시"] = pd.to_datetime(df["접수일시"], errors="coerce")
    df["수량_숫자"] = df["수량"].astype(str).str.extract(r"(\d+)").astype(float)
    # 진행단계 판정
    def get_stage(row):
        qs = str(row.get("견적서발송", "")).strip()
        if qs and qs not in ("", "nan"):
            return "견적서발송"
        return "신청접수"
    df["진행단계"] = df.apply(get_stage, axis=1)
    return df


@st.cache_data(ttl=60)
def load_mgmt():
    try:
        dm = _fetch_csv(MGMT_URL)
        rename_m = {
            "병원명": "병원명",
            "운영대수": "운영대수",
            "업체명": "업체명",
            "RPM명": "RPM명",
            "업데이트 요청 날짜": "요청날짜",
            "협의 완료 날짜": "협의완료일",
            "장소섭외 현황": "장소섭외",
            "업그레이드 진행현황": "진행현황",
            "랜딩 장비 현황": "장비현황",
            "결제 현황": "결제현황",
            "Notes": "비고",
        }
        dm = dm.rename(columns=rename_m)
        dm = dm[dm["병원명"].notna() & (dm["병원명"].astype(str).str.strip() != "")]
        return dm
    except Exception as e:
        return pd.DataFrame(), str(e)


# ── 데이터 로드 ────────────────────────────────────────
try:
    df = load_form()
    err = None
except Exception as e:
    df = pd.DataFrame()
    err = str(e)

dm_result = load_mgmt()
dm = dm_result[0] if isinstance(dm_result, tuple) else dm_result
dm_err = dm_result[1] if isinstance(dm_result, tuple) else None

# ── 헤더 ──────────────────────────────────────────────
col_title, col_refresh = st.columns([6, 1])
col_title.title("📋 큐라시스2 업그레이드 신청 현황")
if col_refresh.button("↺ 새로고침", use_container_width=True):
    st.cache_data.clear(); st.rerun()

if err:
    st.error(f"데이터 로드 오류: {err}")
    st.stop()

if df.empty:
    st.info("신청 데이터가 없습니다.")
    st.stop()

# ── KPI ───────────────────────────────────────────────
total      = len(df)
quote_sent = len(df[df["진행단계"] == "견적서발송"])
waiting    = total - quote_sent
total_qty  = df["수량_숫자"].sum()

# 설치완료 수 (관리 시트 기준)
installed = 0
if not dm.empty and "진행현황" in dm.columns:
    installed = dm["진행현황"].astype(str).str.contains("완료", na=False).sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("총 신청건수",  f"{total}건")
k2.metric("신청접수 (대기)", f"{waiting}건")
k3.metric("견적서 발송완료", f"{quote_sent}건")
k4.metric("설치 완료",    f"{installed}건")
k5.metric("총 신청 수량", f"{int(total_qty) if total_qty > 0 else '-'}대")

st.markdown("---")

# ── 탭 ────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 신청 목록", "📊 통계", "🔧 관리 현황"])

# ═══ 탭1: 신청 목록 ════════════════════════════════════
with tab1:
    # 검색 필터
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        search_co = st.text_input("업체명 검색", "")
    with fc2:
        search_hosp = st.text_input("병원명 검색", "")
    with fc3:
        sel_stage = st.multiselect("진행단계",
                                   ["신청접수", "견적서발송"],
                                   default=["신청접수", "견적서발송"])

    fdf = df.copy()
    if search_co:
        fdf = fdf[fdf["업체명"].astype(str).str.contains(search_co, na=False)]
    if search_hosp:
        fdf = fdf[fdf["병원명"].astype(str).str.contains(search_hosp, na=False)]
    if sel_stage:
        fdf = fdf[fdf["진행단계"].isin(sel_stage)]

    st.caption(f"총 {len(fdf)}건")

    # 표시용 데이터프레임
    disp = fdf[["접수일시","업체명","담당자명","연락처","병원명","수량","희망날짜","진행단계","견적서발송"]].copy()
    disp["접수일시"] = disp["접수일시"].dt.strftime("%Y-%m-%d %H:%M").fillna("")
    disp["진행단계"] = disp["진행단계"].map({
        "신청접수": "⏳ 신청접수",
        "견적서발송": "✅ 견적서발송",
    })

    def hl(row):
        if "견적서발송" in str(row.get("진행단계", "")):
            return ["background-color: #f0fff0"] * len(row)
        return ["background-color: #fffbf0"] * len(row)

    st.dataframe(
        disp.reset_index(drop=True).style.apply(hl, axis=1),
        use_container_width=True,
        height=450,
        column_config={
            "접수일시": st.column_config.TextColumn("접수일시", width=130),
            "업체명":   st.column_config.TextColumn("업체명",   width=160),
            "담당자명": st.column_config.TextColumn("담당자명", width=90),
            "연락처":   st.column_config.TextColumn("연락처",   width=120),
            "병원명":   st.column_config.TextColumn("병원명",   width=160),
            "수량":     st.column_config.TextColumn("수량",     width=80),
            "희망날짜": st.column_config.TextColumn("희망날짜", width=110),
            "진행단계": st.column_config.TextColumn("진행단계", width=120),
            "견적서발송": st.column_config.TextColumn("견적서발송", width=110),
        }
    )

# ═══ 탭2: 통계 ═════════════════════════════════════════
with tab2:
    cc1, cc2 = st.columns(2)

    with cc1:
        st.subheader("업체별 신청 건수")
        co_cnt = df["업체명"].value_counts().reset_index()
        co_cnt.columns = ["업체명", "건수"]
        fig1 = px.bar(co_cnt, x="업체명", y="건수", text="건수",
                      color_discrete_sequence=[C_MAIN])
        fig1.update_layout(margin=dict(t=10,b=0,l=0,r=0), height=300,
                           xaxis_title="", yaxis_title="건수")
        fig1.update_traces(textposition="outside")
        st.plotly_chart(fig1, use_container_width=True, key="chart_company")

    with cc2:
        st.subheader("진행단계별 현황")
        stage_cnt = df["진행단계"].value_counts().reset_index()
        stage_cnt.columns = ["단계", "건수"]
        stage_cnt["단계_kor"] = stage_cnt["단계"].map({
            "신청접수": "신청접수 (대기)",
            "견적서발송": "견적서 발송완료",
        })
        cmap = {"신청접수 (대기)": C_ING, "견적서 발송완료": C_DONE}
        fig2 = px.pie(stage_cnt, names="단계_kor", values="건수",
                      color="단계_kor", color_discrete_map=cmap,
                      hole=0.4)
        fig2.update_layout(margin=dict(t=10,b=10,l=0,r=0), height=300)
        st.plotly_chart(fig2, use_container_width=True, key="chart_stage")

    st.subheader("월별 신청 추이")
    df["접수월"] = df["접수일시"].dt.to_period("M").astype(str)
    mo_cnt = df.groupby(["접수월","진행단계"]).size().reset_index(name="건수")
    cmap2 = {"신청접수": C_ING, "견적서발송": C_DONE}
    fig3 = px.bar(mo_cnt, x="접수월", y="건수", color="진행단계",
                  color_discrete_map=cmap2, barmode="stack", text_auto=True)
    fig3.update_layout(margin=dict(t=10,b=0,l=0,r=0), height=280,
                       xaxis_title="", yaxis_title="건수",
                       legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig3, use_container_width=True, key="chart_monthly")

# ═══ 탭3: 관리 현황 ════════════════════════════════════
with tab3:
    if dm.empty:
        st.warning(f"관리 현황 시트를 불러올 수 없습니다. ({dm_err})")
    else:
        st.subheader("큐라시스2 업그레이드 일정 관리")

        # 진행현황 색상 하이라이트
        def hl_mgmt(row):
            s = str(row.get("진행현황", ""))
            if "완료" in s:   return ["background-color: #f0fff0"] * len(row)
            if "진행" in s:   return ["background-color: #fffbf0"] * len(row)
            return [""] * len(row)

        show_cols = [c for c in ["병원명","업체명","운영대수","요청날짜","협의완료일",
                                  "장소섭외","진행현황","장비현황","결제현황","비고"] if c in dm.columns]
        st.dataframe(
            dm[show_cols].reset_index(drop=True).style.apply(hl_mgmt, axis=1),
            use_container_width=True, height=450
        )
