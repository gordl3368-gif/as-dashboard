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

import base64 as _b64

def _load_logo():
    for p in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"),
        r"C:\Users\user\AS자동화\대시보드\logo.png",
    ]:
        try:
            with open(p, "rb") as f:
                return "data:image/png;base64," + _b64.b64encode(f.read()).decode()
        except Exception:
            pass
    return None

LOGO_DATA = _load_logo()

st.set_page_config(page_title="A/S 현황 대시보드", layout="wide", page_icon="🔧")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html,body,[class*="css"],.stApp{font-family:'Noto Sans KR','Malgun Gothic',sans-serif!important;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
.stDeployButton{visibility:hidden;}
header[data-testid="stHeader"]{display:none!important;}
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
        if "처치" in df.columns:
            df["처치_분류"] = df["처치"].apply(_map_treatment)
        return df, None
    except Exception as e:
        return None, str(e)


TREAT_MAP = [
    ("PCB·메인보드 교체",              ["pcb", "메인보드"]),
    ("핫멜트 작업",                    ["핫멜트", "핫 멜트", "핫멧트", "핫맬트"]),
    ("펌프 세척 및 suction case 교체", ["세척", "suction", "석션", "튜브"]),
    ("펌프 교체",                      ["펌프교체", "펌프 교체"]),
    ("자재 교체",                      ["커버", "cover", "케이스", "case", "키패드", "배터리",
                                        "행거", "어댑터", "밴드패브릭", "밴드홀더", "밴드패드릭",
                                        "나사", "캐니스터", "windows", "widdows", "winodws",
                                        "smps", "ac엔트리", "ac entry", "ac코드", "디스플레이",
                                        "에어파츠", "플러그", "홀더"]),
    ("연구소 전달",                    ["연구소"]),
]

def _map_treatment(val):
    v = str(val).lower()
    matched = [cat for cat, kws in TREAT_MAP if any(k.lower() in v for k in kws)]
    return matched if matched else ["기타"]


df, err = load_data()
today  = datetime.date.today()
cur_m  = today.month
prev_m = cur_m - 1 if cur_m > 1 else 12


# Color palette
PALETTE = [
    ("#1a73e8", "rgba(26,115,232,0.1)"),
    ("#ea4335", "rgba(234,67,53,0.1)"),
    ("#34a853", "rgba(52,168,83,0.1)"),
    ("#fbbc04", "rgba(251,188,4,0.1)"),
    ("#9334e6", "rgba(147,52,230,0.1)"),
    ("#ff6d00", "rgba(255,109,0,0.1)"),
    ("#00bcd4", "rgba(0,188,212,0.1)"),
]
FONT = dict(family="Noto Sans KR, Malgun Gothic, sans-serif", size=12)
BASE = dict(
    plot_bgcolor="white", paper_bgcolor="white", font=FONT,
    xaxis=dict(gridcolor="#f0f4f8", zeroline=False),
    yaxis=dict(gridcolor="#f0f4f8", zeroline=False, rangemode="tozero"),
)

_logo_html = (
    f'<img src="{LOGO_DATA}" style="width:100%;height:100%;object-fit:cover;display:block;">'
    if LOGO_DATA else
    '<div style="color:#fff;font-size:15px;font-weight:700;letter-spacing:1.2px;">CGBIO</div>'
)
_logo_bg = "" if LOGO_DATA else "background:#c0392b;"

# Header
st.markdown(f"""
<div style="display:flex;align-items:stretch;border-bottom:3px solid #e0e4ef;margin-bottom:18px;background:#fff;">
  <div style="{_logo_bg}width:160px;flex-shrink:0;overflow:hidden;">
    {_logo_html}
  </div>
  <div style="width:1px;background:#e0e4ef;flex-shrink:0;"></div>
  <div style="padding:12px 22px;display:flex;flex-direction:column;justify-content:center;">
    <div style="font-size:17px;font-weight:600;color:#1a1f36;letter-spacing:-.2px;">큐라시스 A/S 센터 현황</div>
    <div style="font-size:11px;color:#9ca3af;margin-top:4px;">A/S 접수 · 처리현황 · 원인분석 · 처리내역 &nbsp;|&nbsp; Google Sheets 실시간 연동</div>
  </div>
  <div style="margin-left:auto;padding:12px 22px;display:flex;align-items:center;gap:20px;flex-shrink:0;">
    <div style="font-size:11px;color:#9ca3af;text-align:right;line-height:1.9;">
      {today.strftime('%Y년 %m월 %d일')} 기준<br>
      <span style="color:#1a73e8;font-weight:500;">● 실시간 (1분 갱신)</span>
    </div>
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

EXCL = ["식별불가","불명","미상","없음","N/A","n/a","-",""]
sn_valid  = df[~df["시리얼"].astype(str).str.strip().str.lower().isin([x.lower() for x in EXCL])]
sn_counts = sn_valid["시리얼"].value_counts()
dup_sns   = sn_counts[sn_counts > 1]
dup_cnt   = len(dup_sns)

def month_stats(data, m):
    d = data[data["월"] == m]
    cnt  = len(d)
    done = len(d[d["상태"] == "완료"])
    pct  = round(done / cnt * 100, 1) if cnt else 0
    return cnt, done, pct

cur_cnt, cur_done, cur_pct   = month_stats(df, cur_m)
prev_cnt, prev_done, prev_pct = month_stats(df, prev_m)
delta     = cur_cnt - prev_cnt
total_cnt = len(f)
done_cnt  = len(f[f["상태"] == "완료"])
prog_cnt  = total_cnt - done_cnt
done_pct  = round(done_cnt / total_cnt * 100, 1) if total_cnt else 0

# Weekly stats
_today_dt        = datetime.date.today()
_this_week_start = _today_dt - datetime.timedelta(days=_today_dt.weekday())
_last_week_start = _this_week_start - datetime.timedelta(weeks=1)
_last_week_end   = _this_week_start - datetime.timedelta(days=1)

_df_dated = df[df["접수일자"].notna()].copy()
_df_dated["_date"] = _df_dated["접수일자"].dt.date

_this_w = _df_dated[_df_dated["_date"] >= _this_week_start]
_last_w = _df_dated[(_df_dated["_date"] >= _last_week_start) & (_df_dated["_date"] <= _last_week_end)]

_weeks_rows = []
for _i in range(7, -1, -1):
    _ws = _this_week_start - datetime.timedelta(weeks=_i)
    _we = _ws + datetime.timedelta(days=6)
    _wd = _df_dated[(_df_dated["_date"] >= _ws) & (_df_dated["_date"] <= _we)]
    _weeks_rows.append({
        "label": f"{_ws.month}/{_ws.day}",
        "접수": len(_wd),
        "완료": len(_wd[_wd["상태"] == "완료"]),
        "진행중": len(_wd[_wd["상태"] != "완료"]),
    })
_weeks_df = pd.DataFrame(_weeks_rows)

# KPI
k1, k2, k3, k4, k5 = st.columns(5)
with k1: st.metric(f"이번달 접수 ({cur_m}월)", f"{cur_cnt}건", f"{delta:+d}건 전월비")
with k2: st.metric(f"전월 접수 ({prev_m}월)", f"{prev_cnt}건", f"{prev_pct}% 완료율", delta_color="off")
with k3: st.metric("처리 완료율", f"{done_pct}%", f"{done_cnt} / {total_cnt}건", delta_color="off")
with k4: st.metric("진행중", f"{prog_cnt}건", "처리 대기 중", delta_color="off")
with k5: st.metric("중복 S/N", f"{dup_cnt}건",
                   "⚠ 재접수 주의" if dup_cnt else "이상 없음",
                   delta_color="inverse" if dup_cnt else "off")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

all_months = sorted(df["월"].dropna().unique().astype(int).tolist())
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 종합현황", "🏷️ 제품별 분석", "🔍 유형·원인 분석", "📋 상세목록", "⚠️ 중복 S/N"])


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────

def pivot_table(data, group_col):
    """월별 피벗 테이블 + 합계 + 비율"""
    if data.empty or group_col not in data.columns:
        return pd.DataFrame()
    clean = data[data[group_col].astype(str).str.strip() != ""]
    if clean.empty:
        return pd.DataFrame()
    pv = clean.groupby([group_col, "월"])["수량"].sum().unstack(fill_value=0)
    for m in all_months:
        if m not in pv.columns:
            pv[m] = 0
    pv = pv[[m for m in all_months if m in pv.columns]]
    pv["합계"] = pv.sum(axis=1)
    total = pv["합계"].sum()
    pv["비율"] = (pv["합계"] / total * 100).round(1).astype(str) + "%" if total > 0 else "0%"
    pv.columns = [f"{int(c)}월" if isinstance(c, (int, float)) else c for c in pv.columns]
    return pv


def _x_axis_cfg(months_list):
    """월 순서 고정 xaxis 설정"""
    return dict(
        gridcolor="#f0f4f8", zeroline=False, tickfont=dict(size=8),
        categoryorder="array",
        categoryarray=[f"{m}월" for m in months_list],
    )


def mini_line(data, label, color, fill, months_list):
    monthly = data.groupby("월")["수량"].sum().reindex(months_list, fill_value=0)
    fig = go.Figure(go.Scatter(
        x=[f"{m}월" for m in months_list], y=monthly.values,
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5, color=color, line=dict(width=1.5, color="white")),
        fill="tozeroy", fillcolor=fill,
    ))
    fig.update_layout(
        title=dict(text=label, font=dict(size=11, color="#1a1f36"), x=0),
        height=160, margin=dict(t=30, b=20, l=28, r=8),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=_x_axis_cfg(months_list),
        yaxis=dict(gridcolor="#f0f4f8", zeroline=False, rangemode="tozero", tickfont=dict(size=8)),
        showlegend=False, font=FONT,
    )
    return fig


def mini_bar(data, label, color, months_list):
    monthly = data.groupby("월")["수량"].sum().reindex(months_list, fill_value=0)
    fig = go.Figure(go.Bar(
        x=[f"{m}월" for m in months_list], y=monthly.values,
        marker=dict(color=color, opacity=0.85),
    ))
    fig.update_layout(
        title=dict(text=label, font=dict(size=11, color="#1a1f36"), x=0),
        height=160, margin=dict(t=30, b=20, l=28, r=8),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=_x_axis_cfg(months_list),
        yaxis=dict(gridcolor="#f0f4f8", zeroline=False, rangemode="tozero", tickfont=dict(size=8)),
        showlegend=False, font=FONT,
    )
    return fig


def analysis_section(data, group_col, title, chart_fn="line"):
    """피벗 테이블 + 2열 미니차트 섹션"""
    if group_col not in data.columns:
        return
    cats = [c for c in data[group_col].dropna().unique() if str(c).strip()]
    if not cats:
        return
    with st.container(border=True):
        st.markdown(f"**{title}**")
        pv = pivot_table(data, group_col)
        if not pv.empty:
            st.dataframe(pv, use_container_width=True,
                         height=min(105 + len(cats) * 36, 320))
        for i in range(0, len(cats), 2):
            pair = cats[i:i+2]
            cols = st.columns(len(pair))
            for j, cat in enumerate(pair):
                clr, fill = PALETTE[(i + j) % len(PALETTE)]
                cat_data = data[data[group_col] == cat]
                fig = mini_line(cat_data, cat, clr, fill, all_months) if chart_fn == "line" \
                      else mini_bar(cat_data, cat, clr, all_months)
                with cols[j]:
                    st.plotly_chart(fig, use_container_width=True)


# ═══ TAB 1: 종합현황 ════════════════════════════════════════════════════════
with tab1:
    # 주간 현황
    with st.container(border=True):
        st.markdown("**주간 진행 현황**")
        _tw_cnt  = len(_this_w)
        _tw_done = len(_this_w[_this_w["상태"] == "완료"])
        _tw_prog = _tw_cnt - _tw_done
        _lw_cnt  = len(_last_w)
        _lw_done = len(_last_w[_last_w["상태"] == "완료"])
        _lw_prog = _lw_cnt - _lw_done

        wc1, wc2, wc3, wc4, wc5, wc6 = st.columns(6)
        with wc1: st.metric("이번주 접수", f"{_tw_cnt}건", f"{_tw_cnt - _lw_cnt:+d}건 전주비")
        with wc2: st.metric("이번주 완료", f"{_tw_done}건", delta_color="off")
        with wc3: st.metric("이번주 진행중", f"{_tw_prog}건", delta_color="off")
        with wc4: st.metric("지난주 접수", f"{_lw_cnt}건", delta_color="off")
        with wc5: st.metric("지난주 완료", f"{_lw_done}건", delta_color="off")
        with wc6: st.metric("지난주 진행중", f"{_lw_prog}건", delta_color="off")

        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(
            x=_weeks_df["label"], y=_weeks_df["접수"],
            name="접수", marker=dict(color="#1a73e8", opacity=0.85),
            text=_weeks_df["접수"], textposition="outside", textfont=dict(size=11),
        ))
        fig_w.add_trace(go.Bar(
            x=_weeks_df["label"], y=_weeks_df["완료"],
            name="완료", marker=dict(color="#34a853", opacity=0.85),
        ))
        fig_w.update_layout(
            **BASE, height=260, barmode="overlay",
            margin=dict(t=20, b=30, l=40, r=10),
            legend=dict(orientation="h", y=1.1, x=0, font=dict(size=11)),
        )
        st.plotly_chart(fig_w, use_container_width=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 제품별 월별 멀티라인
    c1, c2 = st.columns([3, 1])
    with c1:
        with st.container(border=True):
            st.markdown("**제품별 월별 A/S 접수 추이**")
            st.caption("제품별 라인 비교")
            pm = f.dropna(subset=["월"]).groupby(["제품명","월"])["수량"].sum().reset_index()
            x_labels = [f"{m}월" for m in all_months]
            fig1 = go.Figure()
            for i, prod in enumerate(sorted(pm["제품명"].unique())):
                vals = pm[pm["제품명"]==prod].set_index("월")["수량"].reindex(all_months, fill_value=0)
                clr, _ = PALETTE[i % len(PALETTE)]
                fig1.add_trace(go.Scatter(
                    x=x_labels, y=vals.values,
                    name=prod, mode="lines+markers",
                    line=dict(color=clr, width=2.5),
                    marker=dict(size=7, color=clr, line=dict(width=2, color="white")),
                ))
            fig1.update_layout(**BASE, height=300,
                               margin=dict(t=10,b=30,l=40,r=10),
                               legend=dict(orientation="h",y=1.12,x=0,font=dict(size=11)))
            fig1.update_xaxes(categoryorder="array", categoryarray=x_labels)
            st.plotly_chart(fig1, use_container_width=True)

    with c2:
        with st.container(border=True):
            st.markdown("**제품별 비중**")
            pt = f.groupby("제품명")["수량"].sum().reset_index()
            if not pt.empty:
                fig_pie = go.Figure(go.Pie(
                    labels=pt["제품명"], values=pt["수량"], hole=0.5,
                    marker=dict(colors=[PALETTE[i % len(PALETTE)][0] for i in range(len(pt))],
                                line=dict(color="white", width=2)),
                    textinfo="label+percent", textfont=dict(size=11),
                ))
                fig_pie.update_layout(height=300, paper_bgcolor="white",
                                      margin=dict(t=10,b=10,l=10,r=10),
                                      showlegend=False, font=FONT)
                st.plotly_chart(fig_pie, use_container_width=True)

    # 제품별 수량 (접기)
    with st.expander("📦 제품별 접수 수량 상세", expanded=False):
        pc = f.groupby("제품명")["수량"].sum().reset_index().sort_values("수량", ascending=True)
        if not pc.empty:
            fig_b = go.Figure(go.Bar(
                y=pc["제품명"], x=pc["수량"], orientation="h",
                marker=dict(color="#1a73e8", opacity=0.85),
                text=pc["수량"], textposition="outside",
                textfont=dict(size=12, color="#1a1f36"),
            ))
            fig_b.update_layout(**BASE, height=max(180, len(pc)*45),
                                margin=dict(t=10,b=20,l=10,r=50))
            st.plotly_chart(fig_b, use_container_width=True)

    # 유형 + 처리현황
    c3, c4 = st.columns(2)
    with c3:
        with st.container(border=True):
            st.markdown("**유형별 접수 현황**")
            if "유형" in f.columns:
                tc = f.groupby("유형")["수량"].sum().reset_index().sort_values("수량", ascending=False)
                if not tc.empty:
                    fig3 = go.Figure(go.Bar(
                        x=tc["유형"], y=tc["수량"],
                        marker=dict(color=[PALETTE[i % len(PALETTE)][0] for i in range(len(tc))]),
                        text=tc["수량"], textposition="outside", textfont=dict(size=12),
                    ))
                    fig3.update_layout(**BASE, height=250, margin=dict(t=10,b=30,l=40,r=10))
                    st.plotly_chart(fig3, use_container_width=True)

    with c4:
        with st.container(border=True):
            st.markdown("**처리 현황**")
            sv = f["상태"].value_counts().reset_index()
            sv.columns = ["상태","건수"]
            if not sv.empty:
                cs = ["#34a853" if s=="완료" else "#fbbc04" for s in sv["상태"]]
                fig4 = go.Figure(go.Pie(
                    labels=sv["상태"], values=sv["건수"], hole=0.58,
                    marker=dict(colors=cs, line=dict(color="white", width=2)),
                    textinfo="label+percent", textfont=dict(size=12),
                ))
                fig4.update_layout(
                    height=250, paper_bgcolor="white", font=FONT,
                    margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
                    annotations=[dict(text=f"<b>{done_pct}%</b><br>완료",
                                      x=0.5, y=0.5, showarrow=False,
                                      font=dict(size=15, family="Noto Sans KR, Malgun Gothic, sans-serif"))]
                )
                st.plotly_chart(fig4, use_container_width=True)


# ═══ TAB 2: 제품별 분석 ═════════════════════════════════════════════════════
with tab2:
    prod_all = sorted(f["제품명"].dropna().unique().tolist())
    if not prod_all:
        st.info("필터에 맞는 제품 데이터가 없습니다.")
    else:
        sel_prod = st.radio("제품 선택", prod_all, horizontal=True)
        pd_data  = f[f["제품명"] == sel_prod]
        st.divider()

        # 월별 총합 추이
        with st.container(border=True):
            st.markdown(f"**{sel_prod} — 월별 접수 추이 (총합)**")
            clr, fill = PALETTE[prod_all.index(sel_prod) % len(PALETTE)]
            mo = pd_data.groupby("월")["수량"].sum().reindex(all_months, fill_value=0)
            fig_p = go.Figure(go.Scatter(
                x=[f"{m}월" for m in all_months], y=mo.values,
                mode="lines+markers+text",
                line=dict(color=clr, width=2.5),
                marker=dict(size=8, color=clr, line=dict(width=2, color="white")),
                fill="tozeroy", fillcolor=fill,
                text=mo.values, textposition="top center", textfont=dict(size=10),
            ))
            fig_p.update_layout(**BASE, height=240,
                                margin=dict(t=10,b=30,l=40,r=10), showlegend=False)
            fig_p.update_xaxes(categoryorder="array",
                               categoryarray=[f"{m}월" for m in all_months])
            st.plotly_chart(fig_p, use_container_width=True)

        # 접수 내용 (유형별)
        if "유형" in pd_data.columns:
            analysis_section(pd_data, "유형", f"{sel_prod} — 접수 내용 (유형별)", chart_fn="line")

        # 원인 분석
        if "원인" in pd_data.columns:
            analysis_section(pd_data, "원인", f"{sel_prod} — 원인 분석", chart_fn="line")

        # 처리 내역
        if "처치_분류" in pd_data.columns:
            exp = pd_data.explode("처치_분류").copy()
            analysis_section(exp, "처치_분류", f"{sel_prod} — 처리 내역", chart_fn="bar")


# ═══ TAB 3: 유형·원인 분석 ══════════════════════════════════════════════════
with tab3:
    with st.container(border=True):
        st.markdown("**유형별 월별 추이**")
        st.caption("전체 제품 합산")
        if "유형" in f.columns:
            tm = f.dropna(subset=["월","유형"]).groupby(["유형","월"])["수량"].sum().reset_index()
            x_labels = [f"{m}월" for m in all_months]
            fig_t = go.Figure()
            for i, t in enumerate(sorted(tm["유형"].unique())):
                vals = tm[tm["유형"]==t].set_index("월")["수량"].reindex(all_months, fill_value=0)
                clr, _ = PALETTE[i % len(PALETTE)]
                fig_t.add_trace(go.Scatter(
                    x=x_labels, y=vals.values,
                    name=t, mode="lines+markers",
                    line=dict(color=clr, width=2.5),
                    marker=dict(size=7, color=clr, line=dict(width=2, color="white")),
                ))
            fig_t.update_layout(**BASE, height=320,
                                margin=dict(t=10,b=30,l=40,r=10),
                                legend=dict(orientation="h",y=1.12,x=0,font=dict(size=11)))
            fig_t.update_xaxes(categoryorder="array", categoryarray=x_labels)
            st.plotly_chart(fig_t, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        with st.container(border=True):
            st.markdown("**유형별 비율**")
            if "유형" in f.columns:
                type_tot = f.groupby("유형")["수량"].sum().reset_index()
                if not type_tot.empty:
                    fig_tp = go.Figure(go.Pie(
                        labels=type_tot["유형"], values=type_tot["수량"], hole=0.5,
                        marker=dict(colors=[PALETTE[i % len(PALETTE)][0] for i in range(len(type_tot))],
                                    line=dict(color="white", width=2)),
                        textinfo="label+percent", textfont=dict(size=11),
                    ))
                    fig_tp.update_layout(height=250, paper_bgcolor="white",
                                         margin=dict(t=10,b=10,l=10,r=10),
                                         showlegend=False, font=FONT)
                    st.plotly_chart(fig_tp, use_container_width=True)

    with c4:
        with st.container(border=True):
            st.markdown("**원인별 비율**")
            if "원인" in f.columns:
                cause_tot = f[f["원인"].astype(str).str.strip() != ""].groupby("원인")["수량"].sum().reset_index()
                if not cause_tot.empty:
                    fig_cp = go.Figure(go.Pie(
                        labels=cause_tot["원인"], values=cause_tot["수량"], hole=0.5,
                        marker=dict(colors=[PALETTE[i % len(PALETTE)][0] for i in range(len(cause_tot))],
                                    line=dict(color="white", width=2)),
                        textinfo="label+percent", textfont=dict(size=11),
                    ))
                    fig_cp.update_layout(height=250, paper_bgcolor="white",
                                         margin=dict(t=10,b=10,l=10,r=10),
                                         showlegend=False, font=FONT)
                    st.plotly_chart(fig_cp, use_container_width=True)


# ═══ TAB 4: 상세목록 ════════════════════════════════════════════════════════
with tab4:
    dcols = [c for c in ["순번","접수일자","HA번호","업체명","제품명","시리얼",
                          "유형","증상","원인","처치","상태","완료일자"] if c in f.columns]

    def render_table(data):
        if data.empty:
            st.info("데이터 없음")
            return
        d = data[dcols].copy()
        d["_dup"] = d["시리얼"].isin(dup_sns.index)
        for col in ["접수일자","완료일자"]:
            if col in d.columns:
                d[col] = pd.to_datetime(d[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        def hl(row):
            if row.get("_dup"): return ["background-color:#fff5f5"] * len(row)
            if row.get("상태") == "진행중": return ["background-color:#fffbf0"] * len(row)
            return [""] * len(row)
        st.dataframe(d.drop(columns=["_dup"]).style.apply(hl, axis=1),
                     use_container_width=True, height=420)

    prod_list_d = sorted(f["제품명"].dropna().unique().tolist())
    d_tabs = st.tabs(["전체"] + prod_list_d)

    with d_tabs[0]:
        if "유형" in f.columns:
            vc = f["유형"].value_counts()
            sc = st.columns(min(len(vc), 6))
            for i, (k, v) in enumerate(vc.items()):
                if i < len(sc): sc[i].metric(k, f"{v}건")
        render_table(f)

    for i, prod in enumerate(prod_list_d):
        with d_tabs[i+1]:
            pdata = f[f["제품명"] == prod]
            st.caption(f"{prod} — 총 {len(pdata)}건")
            render_table(pdata)


# ═══ TAB 5: 중복 S/N ════════════════════════════════════════════════════════
with tab5:
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
