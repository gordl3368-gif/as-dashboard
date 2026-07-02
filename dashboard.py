import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2 import service_account
import datetime
import os

SPREADSHEET_ID = "1tsdHzv1l__d63BQpTf6yFnxRn22KhpCwo7HJG61oYwg"
GS_SHEET_NAME  = "고객자산관리대장"
SA_PATH        = r"C:\Users\user\AS자동화\보고서발송\service_account.json"

st.set_page_config(page_title="A/S 현황 대시보드", layout="wide", page_icon="🔧")

# CSS: short and safe (no Korean, no special chars in comments)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html,body,[class*="css"],.stApp{font-family:'Noto Sans KR','Malgun Gothic',sans-serif!important;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
.stDeployButton{visibility:hidden;}
.block-container{padding-top:0!important;padding-left:1.2rem!important;padding-right:1.2rem!important;max-width:100%!important;}
[data-testid="metric-container"]{background:#ffffff;border:1px solid #e8ecf4;border-radius:10px;padding:14px 18px!important;}
[data-testid="stMetricLabel"]>div{font-size:11px!important;color:#9ca3af!important;}
[data-testid="stMetricValue"]>div{font-size:28px!important;font-weight:700!important;}
</style>""", unsafe_allow_html=True)


def _get_gspread_client():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=60)
def load_data():
    try:
        client = _get_gspread_client()
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(GS_SHEET_NAME)
        all_rows = ws.get_all_values()
        if len(all_rows) < 5:
            return None, "데이터가 없습니다."
        col_map = {
            0:"순번", 1:"접수일자", 3:"HA번호", 4:"제품명", 5:"시리얼",
            6:"수량", 7:"업체명", 11:"증상", 12:"유형", 14:"완료일자", 16:"원인", 17:"처치",
        }
        n_cols = max(col_map.keys()) + 1
        padded = [r + [""] * (n_cols - len(r)) for r in all_rows[4:] if r]
        df = pd.DataFrame(padded).rename(columns=col_map)
        keep = [c for c in col_map.values() if c in df.columns]
        df = df[keep]
        df = df[df["시리얼"].astype(str).str.strip() != ""]
        if "유형" in df.columns:
            df = df[~df["유형"].astype(str).str.contains("세부내용|유형|항목", na=False)]
        for col in ["접수일자", "완료일자"]:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        df["수량"] = pd.to_numeric(df["수량"], errors="coerce").fillna(1)
        df["상태"] = df["완료일자"].apply(lambda x: "완료" if pd.notna(x) else "진행중")
        def exm(ha):
            try:
                mm = int(str(ha).strip()[6:8])
                return mm if 1 <= mm <= 12 else None
            except:
                return None
        df["월"] = df["HA번호"].apply(exm) if "HA번호" in df.columns else df["접수일자"].dt.month
        return df, None
    except Exception as e:
        return None, str(e)


df, err = load_data()
today  = datetime.date.today()
cur_m  = today.month
prev_m = cur_m - 1 if cur_m > 1 else 12

# Header (inline styles only - no CSS classes)
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:14px 0 14px;border-bottom:2px solid #eef1f8;margin-bottom:16px;">
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="background:#c0392b;color:#fff;font-size:11px;font-weight:700;
                 padding:5px 12px;border-radius:5px;letter-spacing:.8px;flex-shrink:0;">시지바이오</span>
    <div>
      <div style="font-size:17px;font-weight:600;color:#1a1f36;">큐라시스 A/S 현황 대시보드</div>
      <div style="font-size:11px;color:#9ca3af;margin-top:3px;">A/S 접수 · 처리현황 · 중복 S/N 관리 | Google Sheets 실시간 연동</div>
    </div>
  </div>
  <div style="font-size:11px;color:#9ca3af;text-align:right;line-height:1.8;">
    {today.strftime('%Y년 %m월 %d일')} 기준<br>
    <span style="color:#1a73e8;font-weight:500;">● 실시간 (1분 갱신)</span>
  </div>
</div>
""", unsafe_allow_html=True)

if err:
    st.error(f"데이터 로드 오류: {err}")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("### 필터")
    if st.button("↺ 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    months  = sorted(df["월"].dropna().unique().astype(int).tolist())
    sel_m   = st.multiselect("월", months, default=months, format_func=lambda m: f"{m}월")
    prods   = sorted(df["제품명"].dropna().unique().tolist())
    sel_p   = st.multiselect("제품명", prods, default=prods)
    types   = sorted(df["유형"].dropna().unique().tolist()) if "유형" in df.columns else []
    sel_t   = st.multiselect("유형", types, default=types)

f = df.copy()
if sel_m: f = f[f["월"].isin(sel_m)]
if sel_p: f = f[f["제품명"].isin(sel_p)]
if sel_t and "유형" in f.columns: f = f[f["유형"].isin(sel_t)]

# Duplicate S/N
EXCL = ["식별불가","불명","미상","없음","N/A","n/a","-",""]
sn_valid  = df[~df["시리얼"].astype(str).str.strip().str.lower().isin([x.lower() for x in EXCL])]
sn_counts = sn_valid["시리얼"].value_counts()
dup_sns   = sn_counts[sn_counts > 1]
dup_cnt   = len(dup_sns)

# Stats
def month_stats(data, m):
    d = data[data["월"] == m]
    cnt  = len(d)
    done = len(d[d["상태"] == "완료"])
    pct  = round(done / cnt * 100, 1) if cnt else 0
    return cnt, done, pct

cur_cnt,  cur_done,  cur_pct  = month_stats(df, cur_m)
prev_cnt, prev_done, prev_pct = month_stats(df, prev_m)
delta     = cur_cnt - prev_cnt
total_cnt = len(f)
done_cnt  = len(f[f["상태"] == "완료"])
prog_cnt  = total_cnt - done_cnt
done_pct  = round(done_cnt / total_cnt * 100, 1) if total_cnt else 0

# KPI cards using native st.metric (reliable on cloud)
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric(
        f"이번달 접수 ({cur_m}월)",
        f"{cur_cnt}건",
        f"{'▲' if delta >= 0 else '▼'} {abs(delta)}건 전월비"
    )
with k2:
    st.metric(f"전월 접수 ({prev_m}월)", f"{prev_cnt}건",
              f"{prev_pct}% 완료율", delta_color="off")
with k3:
    st.metric("처리 완료율", f"{done_pct}%",
              f"{done_cnt} / {total_cnt}건", delta_color="off")
with k4:
    st.metric("진행중", f"{prog_cnt}건", "처리 대기 중", delta_color="off")
with k5:
    st.metric("중복 S/N", f"{dup_cnt}건",
              "⚠ 재접수 주의" if dup_cnt else "이상 없음",
              delta_color="inverse" if dup_cnt else "off")

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 종합현황", "🔍 유형별 분석", "📋 상세목록", "⚠️ 중복 S/N"])

C_BLUE   = "#1a73e8"
C_GREEN  = "#34a853"
C_YELLOW = "#fbbc04"
C_RED    = "#ea4335"
C_PURPLE = "#9334e6"
FONT     = dict(family="Noto Sans KR, Malgun Gothic, sans-serif", size=12)
BASE_LAYOUT = dict(
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(t=10, b=30, l=40, r=20),
    font=FONT,
    xaxis=dict(gridcolor="#f0f4f8", zeroline=False),
    yaxis=dict(gridcolor="#f0f4f8", zeroline=False),
    legend=dict(orientation="h", y=1.15, x=0, font=dict(size=11)),
)


# TAB 1
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            st.markdown("**월별 A/S 접수 추이**")
            rng = f"{min(sel_m) if sel_m else '-'}월 ~ {max(sel_m) if sel_m else '-'}월 누적"
            st.caption(rng)
            md = f.dropna(subset=["월"]).groupby(["월","상태"])["수량"].sum().reset_index()
            if not md.empty:
                pv = md.pivot(index="월", columns="상태", values="수량").fillna(0).reset_index().sort_values("월")
                xl = pv["월"].astype(int).map(lambda m: f"{m}월")
                fig = go.Figure()
                if "완료" in pv.columns:
                    fig.add_trace(go.Scatter(
                        x=xl, y=pv["완료"], name="완료",
                        mode="lines+markers",
                        line=dict(color=C_GREEN, width=2.5),
                        marker=dict(size=7, color=C_GREEN, line=dict(width=2, color="white")),
                        fill="tozeroy", fillcolor="rgba(52,168,83,0.07)"
                    ))
                if "진행중" in pv.columns:
                    fig.add_trace(go.Scatter(
                        x=xl, y=pv["진행중"], name="진행중",
                        mode="lines+markers",
                        line=dict(color=C_YELLOW, width=2.5, dash="dot"),
                        marker=dict(size=7, color=C_YELLOW, line=dict(width=2, color="white")),
                    ))
                fig.update_layout(**BASE_LAYOUT, height=270)
                st.plotly_chart(fig, use_container_width=True)

    with c2:
        with st.container(border=True):
            st.markdown("**제품별 접수 수량**")
            st.caption("수량 합계 기준")
            pc = f.groupby("제품명")["수량"].sum().reset_index().sort_values("수량", ascending=True)
            if not pc.empty:
                fig2 = go.Figure(go.Bar(
                    y=pc["제품명"], x=pc["수량"], orientation="h",
                    marker=dict(color=C_BLUE, opacity=0.85),
                    text=pc["수량"], textposition="outside",
                    textfont=dict(size=12, color="#1a1f36")
                ))
                lo2 = {**BASE_LAYOUT, "height": 270, "margin": dict(t=10, b=30, l=10, r=50)}
                fig2.update_layout(**lo2)
                st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        if "유형" in f.columns:
            with st.container(border=True):
                st.markdown("**불량 유형별 접수**")
                st.caption("유형 분류 기준 · 수량 합계")
                tc = f.groupby("유형")["수량"].sum().reset_index().sort_values("수량", ascending=False)
                if not tc.empty:
                    fig3 = go.Figure(go.Bar(
                        x=tc["유형"], y=tc["수량"],
                        marker=dict(color=C_PURPLE, opacity=0.85),
                        text=tc["수량"], textposition="outside",
                        textfont=dict(size=12, color="#1a1f36")
                    ))
                    fig3.update_layout(**BASE_LAYOUT, height=250)
                    st.plotly_chart(fig3, use_container_width=True)

    with c4:
        with st.container(border=True):
            st.markdown("**처리 현황**")
            st.caption("완료 vs 진행중 비율")
            sv = f["상태"].value_counts().reset_index()
            sv.columns = ["상태", "건수"]
            if not sv.empty:
                colors = [C_GREEN if s == "완료" else C_YELLOW for s in sv["상태"]]
                fig4 = go.Figure(go.Pie(
                    labels=sv["상태"], values=sv["건수"],
                    hole=0.58,
                    marker=dict(colors=colors, line=dict(color="white", width=2)),
                    textinfo="label+percent",
                    textfont=dict(size=12),
                ))
                fig4.update_layout(
                    height=250,
                    paper_bgcolor="white",
                    margin=dict(t=10, b=10, l=10, r=10),
                    font=FONT,
                    showlegend=False,
                    annotations=[dict(
                        text=f"<b>{done_pct}%</b><br>완료",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=15, family="Noto Sans KR, Malgun Gothic, sans-serif")
                    )]
                )
                st.plotly_chart(fig4, use_container_width=True)


# TAB 2
with tab2:
    if "유형" in f.columns:
        type_list = sorted(f["유형"].dropna().unique().tolist())
        t_tabs = st.tabs(["전체"] + type_list)

        def type_view(data, label="전체"):
            if data.empty:
                st.info("데이터 없음")
                return
            a, b, c = st.columns(3)
            a.metric("건수", f"{len(data)}")
            b.metric("제품 종류", f"{data['제품명'].nunique()}")
            c.metric("완료율", f"{round(len(data[data['상태']=='완료'])/len(data)*100,1)}%")
            pd_ = data.groupby("제품명")["수량"].sum().reset_index().sort_values("수량", ascending=True)
            fig = go.Figure(go.Bar(
                y=pd_["제품명"], x=pd_["수량"], orientation="h",
                marker=dict(color=C_BLUE, opacity=0.85),
                text=pd_["수량"], textposition="outside",
                textfont=dict(size=14, color="#1a1f36")
            ))
            lo = {**BASE_LAYOUT, "height": 380, "margin": dict(t=30, b=30, l=10, r=60)}
            fig.update_layout(**lo)
            st.plotly_chart(fig, use_container_width=True, key=f"tc_{label}")

        with t_tabs[0]:
            type_view(f)
        for i, t in enumerate(type_list):
            with t_tabs[i + 1]:
                type_view(f[f["유형"] == t], t)


# TAB 3
with tab3:
    prod_list = sorted(f["제품명"].dropna().unique().tolist())
    d_tabs = st.tabs(["전체"] + prod_list)
    dcols = [c for c in ["순번","접수일자","HA번호","업체명","제품명","시리얼",
                          "유형","증상","상태","완료일자"] if c in f.columns]

    def render_table(data):
        if data.empty:
            st.info("데이터 없음")
            return
        if "유형" in data.columns:
            vc = data["유형"].value_counts()
            sc = st.columns(min(len(vc), 6))
            for i, (k, v) in enumerate(vc.items()):
                if i < len(sc):
                    sc[i].metric(k, f"{v}건")
        d = data[dcols].copy()
        d["_dup"] = d["시리얼"].isin(dup_sns.index)
        for col in ["접수일자", "완료일자"]:
            if col in d.columns:
                d[col] = pd.to_datetime(d[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        def hl(row):
            if row.get("_dup"):
                return ["background-color:#fff5f5"] * len(row)
            if row.get("상태") == "진행중":
                return ["background-color:#fffbf0"] * len(row)
            return [""] * len(row)
        st.dataframe(d.drop(columns=["_dup"]).style.apply(hl, axis=1),
                     use_container_width=True, height=420)

    with d_tabs[0]:
        render_table(f)
    for i, prod in enumerate(prod_list):
        with d_tabs[i + 1]:
            pdata = f[f["제품명"] == prod]
            st.caption(f"{prod} — {len(pdata)}건")
            render_table(pdata)


# TAB 4
with tab4:
    if dup_cnt == 0:
        st.success("중복 접수된 S/N이 없습니다.")
    else:
        st.error(f"⚠️ 동일 S/N으로 2회 이상 접수된 기기: {dup_cnt}건")
        dup_df = df[df["시리얼"].isin(dup_sns.index)].copy().sort_values(["시리얼","접수일자"])
        summary_cols = [c for c in ["시리얼","제품명","업체명","유형","접수일자","완료일자","상태"]
                        if c in dup_df.columns]
        sd = dup_df[summary_cols].copy()
        for col in ["접수일자","완료일자"]:
            if col in sd.columns:
                sd[col] = pd.to_datetime(sd[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        sd.insert(0, "접수횟수", sd["시리얼"].map(sn_counts))
        for sn in sorted(dup_sns.index, key=lambda s: -sn_counts[s]):
            rows = sd[sd["시리얼"] == sn]
            cnt  = int(sn_counts[sn])
            prod = rows["제품명"].iloc[0] if "제품명" in rows.columns else ""
            with st.expander(f"🔴 {sn}  |  {prod}  |  총 {cnt}회 접수"):
                st.dataframe(rows.drop(columns=["접수횟수"]).reset_index(drop=True),
                             use_container_width=True, hide_index=True)
