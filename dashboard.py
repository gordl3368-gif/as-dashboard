import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2 import service_account
import os

SPREADSHEET_ID = "1tsdHzv1l__d63BQpTf6yFnxRn22KhpCwo7HJG61oYwg"
GS_SHEET_NAME  = "고객자산관리대장"
SA_PATH        = r"C:\Users\user\AS자동화\보고서발송\service_account.json"  # 로컬 전용

# 공통 색상
C_MAIN  = "#4472C4"   # 파랑 (제품별)
C_SUB   = "#ED7D31"   # 주황 (유형별)
C_DONE  = "#70AD47"   # 초록 (완료)
C_ING   = "#FFC000"   # 노랑 (진행중)
C_WARN  = "#FF4B4B"   # 빨강 (중복/경고)

st.set_page_config(page_title="A/S 현황 대시보드", page_icon="🔧", layout="wide")

st.markdown("""
<meta name="google" content="notranslate">
<meta http-equiv="Content-Language" content="ko">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html, body, [class*="css"], .stApp, button, input, select, textarea {
    font-family: 'Noto Sans KR', 'Malgun Gothic', '맑은 고딕', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

def _get_gspread_client():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    # Streamlit Cloud: st.secrets 사용 / 로컬: service_account.json 사용
    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            SA_PATH, scopes=SCOPES
        )
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data():
    try:
        client = _get_gspread_client()
        sh = client.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(GS_SHEET_NAME)

        # 1~3행: 제목/병합셀, 4행: 헤더, 5행~: 데이터
        all_rows = ws.get_all_values()
        if len(all_rows) < 5:
            return None, "데이터가 없습니다."

        col_map = {
            0:"순번", 1:"접수일자", 3:"HA번호", 4:"제품명", 5:"시리얼",
            6:"수량", 7:"업체명", 11:"증상", 12:"유형", 14:"완료일자", 16:"원인", 17:"처치",
        }
        data_rows = all_rows[4:]  # 5행부터 데이터
        n_cols = max(col_map.keys()) + 1
        padded = [r + [""] * (n_cols - len(r)) for r in data_rows if len(r) > 0]
        df = pd.DataFrame(padded)
        df = df.rename(columns=col_map)
        keep = [c for c in ["순번","접수일자","HA번호","제품명","시리얼","수량",
                             "업체명","증상","유형","완료일자","원인","처치"] if c in df.columns]
        df = df[keep]
        df = df[df["시리얼"].astype(str).str.strip() != ""]
        if "유형" in df.columns:
            df = df[~df["유형"].astype(str).str.contains("세부내용|유형|항목", na=False)]
        for col in ["접수일자","완료일자"]:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        df["수량"] = pd.to_numeric(df["수량"], errors="coerce").fillna(1)
        df["상태"] = df["완료일자"].apply(lambda x: "완료" if pd.notna(x) else "진행중")
        def exm(ha):
            try:
                mm = int(str(ha).strip()[6:8])
                return mm if 1 <= mm <= 12 else None
            except: return None
        df["월"] = df["HA번호"].apply(exm) if "HA번호" in df.columns else df["접수일자"].dt.month
        return df, None
    except Exception as e:
        return None, str(e)

df, err = load_data()

col_title, col_refresh = st.columns([6, 1])
col_title.title("🔧 큐라시스 A/S 현황 대시보드")
if col_refresh.button("↺ 새로고침", use_container_width=True):
    st.cache_data.clear(); st.rerun()

if err:
    st.error(f"파일 로드 오류: {err}")
    st.stop()

# ── 사이드바 필터 ──────────────────────────────────────
with st.sidebar:
    st.header("필터")
    months = sorted(df["월"].dropna().unique().astype(int).tolist())
    sel_months = st.multiselect("월 선택", months, default=months,
                                format_func=lambda m: f"{m}월")
    prods = sorted(df["제품명"].dropna().unique().tolist())
    sel_prods = st.multiselect("제품명", prods, default=prods)
    types = sorted(df["유형"].dropna().unique().tolist()) if "유형" in df.columns else []
    sel_types = st.multiselect("유형", types, default=types)

# ── 필터 적용 ──────────────────────────────────────────
f = df.copy()
if sel_months: f = f[f["월"].isin(sel_months)]
if sel_prods:  f = f[f["제품명"].isin(sel_prods)]
if sel_types and "유형" in f.columns: f = f[f["유형"].isin(sel_types)]

# ── 중복 S/N 계산 (전체 데이터 기준, 식별불가 제외) ───
EXCLUDE_SNS = ["식별불가", "불명", "미상", "없음", "N/A", "n/a", "-", ""]
sn_valid  = df[~df["시리얼"].astype(str).str.strip().str.lower().isin(
                [x.lower() for x in EXCLUDE_SNS])]
sn_counts = sn_valid["시리얼"].value_counts()
dup_sns   = sn_counts[sn_counts > 1]
dup_cnt   = len(dup_sns)

# ── 전월 비교 계산 (현재 날짜 기준) ──────────────────
import datetime
cur_m  = datetime.date.today().month
prev_m = cur_m - 1 if cur_m > 1 else 12

def month_stats(data, m):
    d = data[data["월"] == m] if m else pd.DataFrame()
    cnt  = len(d)
    done = len(d[d["상태"] == "완료"]) if cnt else 0
    pct  = round(done / cnt * 100, 1) if cnt else 0
    return cnt, done, pct

cur_cnt,  cur_done,  cur_pct  = month_stats(df, cur_m)
prev_cnt, prev_done, prev_pct = month_stats(df, prev_m)

def delta_str(cur, prev, unit="건"):
    if prev is None or prev == 0: return None
    diff = cur - prev
    return f"{'+' if diff >= 0 else ''}{diff}{unit} (전월)"

# ── KPI ───────────────────────────────────────────────
total_qty = int(f["수량"].sum())
total_cnt = len(f)
done_cnt  = len(f[f["상태"]=="완료"])
done_pct  = round(done_cnt/total_cnt*100, 1) if total_cnt else 0
prog_cnt  = total_cnt - done_cnt

st.caption(f"※ 전월 비교: {prev_m}월 → {cur_m}월 기준 (전체 데이터)" if prev_m else "")

k1, k2, k3 = st.columns(3)
k1.metric(f"이번달 접수 ({cur_m}월)", f"{cur_cnt}건",
          delta_str(cur_cnt, prev_cnt), delta_color="normal")
k2.metric(f"전월 접수 ({prev_m}월)", f"{prev_cnt}건" if prev_m else "-")
k3.metric("중복 S/N", f"{dup_cnt}건", "동일 기기 재접수" if dup_cnt else "없음",
          delta_color="inverse" if dup_cnt else "off")
st.markdown("---")

# ── 탭 ───────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 종합현황", "🔍 유형별", "📋 상세목록", "⚠️ 중복 S/N"])

# ═══ 탭1: 종합현황 ════════════════════════════════════
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("월별 A/S 입고 수량")
        md = (f.dropna(subset=["월"])
               .assign(월str=lambda x: x["월"].astype(int).map(lambda m: f"{m}월"))
               .groupby(["월str","상태"])["수량"].sum().reset_index())
        if not md.empty:
            fig = px.bar(md, x="월str", y="수량", color="상태",
                         color_discrete_map={"완료": C_DONE, "진행중": C_ING},
                         barmode="stack", text_auto=True)
            fig.update_layout(margin=dict(t=10,b=0,l=0,r=0), height=280,
                              xaxis_title="", yaxis_title="수량",
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("제품별 입고 수량")
        pc = f.groupby("제품명")["수량"].sum().reset_index().sort_values("수량", ascending=False)
        if not pc.empty:
            fig2 = px.bar(pc, x="제품명", y="수량", text="수량",
                          color_discrete_sequence=[C_MAIN])
            fig2.update_layout(margin=dict(t=30,b=0,l=0,r=0), height=280,
                               xaxis_title="", yaxis_title="수량",
                               yaxis=dict(range=[0, pc["수량"].max() * 1.2]))
            fig2.update_traces(textposition="outside", textfont_size=13)
            st.plotly_chart(fig2, use_container_width=True)

    if "유형" in f.columns:
        st.subheader("불량 유형별 수량")
        tc = f.groupby("유형")["수량"].sum().reset_index().sort_values("수량", ascending=False)
        if not tc.empty:
            fig3 = px.bar(tc, x="유형", y="수량", text="수량",
                          color_discrete_sequence=[C_SUB])
            fig3.update_layout(margin=dict(t=30,b=0,l=0,r=0), height=280,
                               xaxis_title="", yaxis_title="수량",
                               yaxis=dict(range=[0, tc["수량"].max() * 1.2]))
            fig3.update_traces(textposition="outside", textfont_size=13)
            st.plotly_chart(fig3, use_container_width=True)

# ═══ 탭2: 유형별 ══════════════════════════════════════
with tab2:
    if "유형" in f.columns:
        type_list = sorted(f["유형"].dropna().unique().tolist())
        t_tabs = st.tabs(["전체"] + type_list)

        def type_view(data, label="전체"):
            if data.empty: st.info("데이터 없음"); return
            a, b, c = st.columns(3)
            a.metric("건수", f"{len(data)}")
            b.metric("제품 종류", f"{data['제품명'].nunique()}")
            c.metric("완료율", f"{round(len(data[data['상태']=='완료'])/len(data)*100,1)}%")
            pd_ = data.groupby("제품명")["수량"].sum().reset_index().sort_values("수량", ascending=False)
            fig = px.bar(pd_, x="제품명", y="수량", text="수량",
                         color_discrete_sequence=[C_MAIN])
            fig.update_layout(margin=dict(t=50,b=0,l=0,r=0), height=380,
                              xaxis_title="", yaxis_title="수량",
                              yaxis=dict(range=[0, pd_["수량"].max() * 1.2]))
            fig.update_traces(textposition="outside", textfont_size=16, textfont_color="black")
            st.plotly_chart(fig, use_container_width=True, key=f"type_chart_{label}")

        with t_tabs[0]: type_view(f)
        for i, t in enumerate(type_list):
            with t_tabs[i+1]: type_view(f[f["유형"]==t], t)

# ═══ 탭3: 상세목록 ═══════════════════════════════════
with tab3:
    prod_list = sorted(f["제품명"].dropna().unique().tolist())
    d_tabs = st.tabs(["전체"] + prod_list)
    dcols = [c for c in ["순번","접수일자","HA번호","업체명","제품명","시리얼",
                          "유형","증상","상태","완료일자"] if c in f.columns]

    def render_table(data):
        if data.empty: st.info("데이터 없음"); return
        if "유형" in data.columns:
            vc = data["유형"].value_counts()
            sc = st.columns(min(len(vc), 6))
            for i, (k, v) in enumerate(vc.items()):
                if i < len(sc): sc[i].metric(k, f"{v}건")
        d = data[dcols].copy()
        d["중복"] = d["시리얼"].isin(dup_sns.index)
        for col in ["접수일자","완료일자"]:
            if col in d.columns:
                d[col] = pd.to_datetime(d[col], errors="coerce").dt.strftime("%Y-%m-%d")
                d[col] = d[col].fillna("")
        def hl(row):
            if row.get("중복"): return ["background-color: #fff0f0"] * len(row)
            if row.get("상태") == "진행중": return ["background-color: #f5f5f5"] * len(row)
            return [""] * len(row)
        st.dataframe(d.drop(columns=["중복"]).style.apply(hl, axis=1),
                     use_container_width=True, height=350)

    with d_tabs[0]: render_table(f)
    for i, prod in enumerate(prod_list):
        with d_tabs[i+1]:
            pdata = f[f["제품명"]==prod]
            st.caption(f"{prod} — {len(pdata)}건")
            render_table(pdata)

# ═══ 탭4: 중복 S/N ════════════════════════════════════
with tab4:
    if dup_cnt == 0:
        st.success("중복 접수된 S/N이 없습니다.")
    else:
        st.error(f"⚠️ 동일 S/N으로 2회 이상 접수된 기기: {dup_cnt}건")

        # 중복 S/N 요약 테이블
        dup_df = (df[df["시리얼"].isin(dup_sns.index)]
                  .copy()
                  .sort_values(["시리얼","접수일자"]))

        summary_cols = [c for c in ["시리얼","제품명","업체명","유형","접수일자","완료일자","상태"] if c in dup_df.columns]
        sd = dup_df[summary_cols].copy()
        for col in ["접수일자","완료일자"]:
            if col in sd.columns:
                sd[col] = pd.to_datetime(sd[col], errors="coerce").dt.strftime("%Y-%m-%d")
                sd[col] = sd[col].fillna("")

        # 접수 횟수 추가
        sd.insert(0, "접수횟수", sd["시리얼"].map(sn_counts))

        # S/N별 그룹 표시
        sn_list = sorted(dup_sns.index.tolist(), key=lambda s: -sn_counts[s])
        for sn in sn_list:
            rows = sd[sd["시리얼"] == sn]
            cnt  = int(sn_counts[sn])
            prod = rows["제품명"].iloc[0] if "제품명" in rows.columns else ""
            with st.expander(f"🔴 {sn}  |  {prod}  |  총 {cnt}회 접수"):
                st.dataframe(rows.drop(columns=["접수횟수"]).reset_index(drop=True),
                             use_container_width=True, hide_index=True)
