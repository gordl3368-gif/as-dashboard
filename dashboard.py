import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2 import service_account
import datetime
import os

SPREADSHEET_ID = "1tsdHzv1l__d63BQpTf6yFnxRn22KhpCwo7HJG61oYwg"
GS_SHEET_NAME  = "고객자산관리대장"
SURVEY_SHEET   = "만족도평가"
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

/* ── 기본 폰트 ── */
html,body,[class*="css"],.stApp{font-family:'Noto Sans KR','Malgun Gothic',sans-serif!important;}

/* ── 숨김 처리 ── */
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
.stDeployButton{visibility:hidden;}
header[data-testid="stHeader"]{display:none!important;}

/* ── 앱 배경 연한 회색 ── */
.stApp{background:#f4f6f9!important;}
section[data-testid="stSidebar"]{background:#ffffff!important;border-right:1px solid #e8ecf0!important;}

/* ── 메인 컨텐츠 여백 ── */
.block-container{padding-top:0!important;padding-left:1.4rem!important;padding-right:1.4rem!important;max-width:100%!important;}

/* ── KPI 메트릭 카드 ── */
[data-testid="metric-container"]{
  background:#ffffff!important;
  border:none!important;
  border-radius:14px!important;
  padding:18px 20px!important;
  box-shadow:0 2px 10px rgba(0,0,0,0.07)!important;
}
[data-testid="stMetricLabel"]>div{font-size:11px!important;color:#9ca3af!important;letter-spacing:0.3px!important;}
[data-testid="stMetricValue"]>div{font-size:26px!important;font-weight:700!important;color:#C45D31!important;}
[data-testid="stMetricDelta"]>div{font-size:11px!important;}

/* ── 컨테이너 카드 (border=True) ── */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:#ffffff!important;
  border:none!important;
  border-radius:14px!important;
  box-shadow:0 2px 10px rgba(0,0,0,0.06)!important;
  padding:4px!important;
}

/* ── 탭 스타일 ── */
.stTabs [data-baseweb="tab-list"]{
  gap:4px!important;
  border-bottom:2px solid #e8ecf0!important;
  background:transparent!important;
  padding-bottom:0!important;
}
.stTabs [data-baseweb="tab"]{
  padding:10px 18px!important;
  font-size:13px!important;
  font-weight:500!important;
  color:#6b7280!important;
  background:transparent!important;
  border:none!important;
  border-radius:0!important;
}
.stTabs [data-baseweb="tab"]:hover{color:#C45D31!important;background:rgba(196,93,49,0.05)!important;}
.stTabs [aria-selected="true"]{color:#C45D31!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-highlight"]{background:#C45D31!important;height:2px!important;}
.stTabs [data-baseweb="tab-border"]{display:none!important;}

/* ── 버튼 ── */
.stButton>button{
  border-radius:9px!important;
  font-weight:500!important;
  font-size:13px!important;
  border:1px solid #e0e4eb!important;
  background:#ffffff!important;
  color:#374151!important;
  transition:all 0.15s!important;
}
.stButton>button:hover{border-color:#C45D31!important;color:#C45D31!important;}

/* ── 사이드바 ── */
section[data-testid="stSidebar"] .stMarkdown h3{
  font-size:11px!important;color:#9ca3af!important;
  letter-spacing:0.8px!important;text-transform:uppercase!important;
  margin-bottom:8px!important;
}
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div,
section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div {
  border-radius:9px!important;
}

/* ── expander ── */
[data-testid="stExpander"]{
  border:none!important;
  border-radius:12px!important;
  background:#ffffff!important;
  box-shadow:0 2px 8px rgba(0,0,0,0.05)!important;
}

/* ── 검색 인풋 ── */
[data-testid="stTextInput"]>div>div>input{
  border-radius:9px!important;
  border:1px solid #e0e4eb!important;
  font-size:13px!important;
}
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
            0:"순번", 1:"접수일자", 2:"입고일자", 3:"HA번호", 4:"제품명", 5:"시리얼",
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
        for col in ["접수일자", "입고일자", "완료일자"]:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        df["수량"] = pd.to_numeric(df["수량"], errors="coerce").fillna(1)
        df["상태"] = df["완료일자"].apply(lambda x: "완료" if pd.notna(x) else "진행중")
        def exm(ha):
            try:
                mm = int(str(ha).strip()[6:8])
                return mm if 1 <= mm <= 12 else None
            except:
                return None
        df["월"] = df["입고일자"].dt.month.where(df["입고일자"].notna(), df["접수일자"].dt.month)
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


# Color palette (CGBIO 브랜드 컬러 기준)
PALETTE = [
    ("#C45D31", "rgba(196,93,49,0.1)"),
    ("#ea4335", "rgba(234,67,53,0.1)"),
    ("#34a853", "rgba(52,168,83,0.1)"),
    ("#fbbc04", "rgba(251,188,4,0.1)"),
    ("#9334e6", "rgba(147,52,230,0.1)"),
    ("#1a73e8", "rgba(26,115,232,0.1)"),
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
    <div style="font-size:17px;font-weight:600;color:#1a1f36;letter-spacing:-.2px;">시지바이오 A/S 센터 현황</div>
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

_completed = f[f["상태"] == "완료"].copy()
_completed["처리일수"] = (_completed["완료일자"] - _completed["접수일자"]).dt.days
avg_days = round(_completed["처리일수"].dropna().mean(), 1) if not _completed.empty else 0

# Weekly stats
_today_dt        = datetime.date.today()
_this_week_start = _today_dt - datetime.timedelta(days=_today_dt.weekday())
_last_week_start = _this_week_start - datetime.timedelta(weeks=1)
_last_week_end   = _this_week_start - datetime.timedelta(days=1)

_df_dated = df[df["입고일자"].notna()].copy()
_df_dated["_date"] = _df_dated["입고일자"].dt.date

_this_w = _df_dated[_df_dated["_date"] >= _this_week_start]
_last_w = _df_dated[(_df_dated["_date"] >= _last_week_start) & (_df_dated["_date"] <= _last_week_end)]

_weeks_rows = []
for _i in range(7, -1, -1):
    _ws = _this_week_start - datetime.timedelta(weeks=_i)
    _we = _ws + datetime.timedelta(days=6)
    _wd = _df_dated[(_df_dated["_date"] >= _ws) & (_df_dated["_date"] <= _we)]
    _wnum = (_ws.day - 1) // 7 + 1
    _weeks_rows.append({
        "label": f"{_ws.month}월 {_wnum}주차",
        "접수": len(_wd),
        "완료": len(_wd[_wd["상태"] == "완료"]),
        "진행중": len(_wd[_wd["상태"] != "완료"]),
    })
_weeks_df = pd.DataFrame(_weeks_rows)

# KPI
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric(f"이번달 접수 ({cur_m}월)", f"{cur_cnt}건", f"{delta:+d}건 전월비")
with k2: st.metric(f"전월 접수 ({prev_m}월)", f"{prev_cnt}건", f"{prev_pct}% 완료율", delta_color="off")
with k3: st.metric("처리 완료율", f"{done_pct}%", f"{done_cnt} / {total_cnt}건", delta_color="off")
with k4: st.metric("진행중", f"{prog_cnt}건", "처리 대기 중", delta_color="off")
with k5: st.metric("평균 처리 기간", f"{avg_days}일", "접수→완료 평균", delta_color="off")
with k6: st.metric("중복 S/N", f"{dup_cnt}건",
                   "⚠ 재접수 주의" if dup_cnt else "이상 없음",
                   delta_color="inverse" if dup_cnt else "off")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

all_months = sorted(df["월"].dropna().unique().astype(int).tolist())
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 종합현황", "🏷️ 제품별 분석", "🔍 유형·원인 분석", "📋 상세목록", "⚠️ 중복 S/N", "⭐ 만족도", "🏢 업체별 조회"])


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

    # 주차별 상세 분석
    with st.container(border=True):
        st.markdown("**주차별 상세 분석**")
        _week_labels = [r["label"] for r in _weeks_rows]
        _sel_week_label = st.selectbox("주차 선택", _week_labels,
                                       index=len(_week_labels)-1, key="week_sel")
        _sel_idx = _week_labels.index(_sel_week_label)
        _sel_ws  = _this_week_start - datetime.timedelta(weeks=(7 - _sel_idx))
        _sel_we  = _sel_ws + datetime.timedelta(days=6)
        _sel_wd  = _df_dated[(_df_dated["_date"] >= _sel_ws) & (_df_dated["_date"] <= _sel_we)]

        if _sel_wd.empty:
            st.info("해당 주차 데이터가 없습니다.")
        else:
            _wd_cnt  = len(_sel_wd)
            _wd_done = len(_sel_wd[_sel_wd["상태"] == "완료"])
            _wdkpi1, _wdkpi2, _wdkpi3 = st.columns(3)
            with _wdkpi1: st.metric("접수", f"{_wd_cnt}건", delta_color="off")
            with _wdkpi2: st.metric("완료", f"{_wd_done}건", delta_color="off")
            with _wdkpi3: st.metric("진행중", f"{_wd_cnt - _wd_done}건", delta_color="off")

            _wa, _wb = st.columns(2)

            def _week_hbar(col, data, group_col, title, color_single=None):
                with col:
                    if group_col not in data.columns:
                        return
                    vc = data[data[group_col].astype(str).str.strip() != ""] \
                             .groupby(group_col)["수량"].sum().reset_index() \
                             .sort_values("수량", ascending=True)
                    if vc.empty:
                        st.caption(f"{title} 데이터 없음")
                        return
                    colors = color_single if color_single else \
                             [PALETTE[i % len(PALETTE)][0] for i in range(len(vc))]
                    fig = go.Figure(go.Bar(
                        y=vc[group_col], x=vc["수량"],
                        orientation="h",
                        marker=dict(
                            color=colors,
                            line=dict(width=0),
                            opacity=0.88,
                        ),
                        text=vc["수량"],
                        textposition="outside",
                        textfont=dict(size=12, color="#1a1f36"),
                        cliponaxis=False,
                    ))
                    fig.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white", font=FONT,
                        height=max(180, len(vc) * 44 + 60),
                        title=dict(text=title, font=dict(size=13, color="#1a1f36", family="Noto Sans KR, sans-serif"), x=0),
                        margin=dict(t=40, b=10, l=10, r=60),
                        xaxis=dict(gridcolor="#f0f4f8", zeroline=False, showticklabels=False),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", zeroline=False,
                                   tickfont=dict(size=12, color="#374151")),
                        showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)

            _week_hbar(_wa, _sel_wd, "제품명", "기기별 입고 수량",
                       color_single=[PALETTE[i % len(PALETTE)][0]
                                     for i in range(len(_sel_wd["제품명"].dropna().unique()))])
            _week_hbar(_wb, _sel_wd, "유형", "유형별 접수 현황")

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
                text=mo.values, textposition="top center", textfont=dict(size=10, color="#1a1f36"),
                cliponaxis=False,
            ))
            fig_p.update_layout(**BASE, height=240,
                                margin=dict(t=50,b=30,l=60,r=20), showlegend=False)
            fig_p.update_xaxes(categoryorder="array",
                               categoryarray=[f"{m}월" for m in all_months])
            fig_p.update_yaxes(range=[0, mo.max() * 1.45], rangemode="normal")
            st.plotly_chart(fig_p, use_container_width=True)

        # 유형별 비율 + 처리 내역 비율 파이차트
        _pc1, _pc2 = st.columns(2)
        with _pc1:
            with st.container(border=True):
                st.markdown(f"**{sel_prod} — 유형별 비율**")
                if "유형" in pd_data.columns:
                    _type_tot = pd_data[pd_data["유형"].astype(str).str.strip() != ""].groupby("유형")["수량"].sum().reset_index()
                    if not _type_tot.empty:
                        fig_tp2 = go.Figure(go.Pie(
                            labels=_type_tot["유형"], values=_type_tot["수량"], hole=0.5,
                            marker=dict(colors=[PALETTE[i % len(PALETTE)][0] for i in range(len(_type_tot))],
                                        line=dict(color="white", width=2)),
                            textinfo="label+percent", textfont=dict(size=11),
                        ))
                        fig_tp2.update_layout(height=260, paper_bgcolor="white",
                                              margin=dict(t=10,b=10,l=10,r=10),
                                              showlegend=False, font=FONT)
                        st.plotly_chart(fig_tp2, use_container_width=True)
        with _pc2:
            with st.container(border=True):
                st.markdown(f"**{sel_prod} — 처리 내역 비율**")
                if "처치_분류" in pd_data.columns:
                    _exp2 = pd_data.explode("처치_분류").copy()
                    _treat_tot = _exp2[_exp2["처치_분류"].astype(str).str.strip() != ""].groupby("처치_분류")["수량"].sum().reset_index()
                    if not _treat_tot.empty:
                        fig_tr2 = go.Figure(go.Pie(
                            labels=_treat_tot["처치_분류"], values=_treat_tot["수량"], hole=0.5,
                            marker=dict(colors=[PALETTE[i % len(PALETTE)][0] for i in range(len(_treat_tot))],
                                        line=dict(color="white", width=2)),
                            textinfo="label+percent", textfont=dict(size=11),
                        ))
                        fig_tr2.update_layout(height=260, paper_bgcolor="white",
                                              margin=dict(t=10,b=10,l=10,r=10),
                                              showlegend=False, font=FONT)
                        st.plotly_chart(fig_tr2, use_container_width=True)

        # 유형별 월별 상세 수치
        if "유형" in pd_data.columns:
            with st.expander("📋 유형별 월별 상세 수치", expanded=False):
                pv = pivot_table(pd_data, "유형")
                if not pv.empty:
                    st.dataframe(pv, use_container_width=True,
                                 height=min(105 + len(pv) * 36, 320))

        # 원인 분석
        if "원인" in pd_data.columns:
            with st.expander("🔍 원인 분석 상세 보기", expanded=False):
                analysis_section(pd_data, "원인", f"{sel_prod} — 원인 분석", chart_fn="line")

        # 처리 내역 월별 상세 수치
        if "처치_분류" in pd_data.columns:
            with st.expander("📋 처리 내역 월별 상세 수치", expanded=False):
                _exp3 = pd_data.explode("처치_분류").copy()
                pv2 = pivot_table(_exp3, "처치_분류")
                if not pv2.empty:
                    st.dataframe(pv2, use_container_width=True,
                                 height=min(105 + len(pv2) * 36, 320))


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

    _, c3, _ = st.columns([1, 2, 1])
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

    with st.expander("🔍 원인 분석 상세 보기", expanded=False):
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

    # 시리얼 번호 검색
    _sa, _sb = st.columns([3, 1])
    with _sa:
        _search = st.text_input("🔍 검색", placeholder="시리얼 번호 입력", label_visibility="collapsed")
    with _sb:
        _search_clear = st.button("초기화", use_container_width=True)
    if _search_clear:
        _search = ""

    if _search.strip():
        _kw = _search.strip().lower()
        _mask = f["시리얼"].astype(str).str.lower().str.contains(_kw, na=False)
        f_search = f[_mask]
        st.caption(f"'{_search}' 검색 결과: {len(f_search)}건")
    else:
        f_search = f

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

    prod_list_d = sorted(f_search["제품명"].dropna().unique().tolist())
    d_tabs = st.tabs(["전체"] + prod_list_d)

    with d_tabs[0]:
        if "유형" in f_search.columns:
            vc = f_search["유형"].value_counts()
            sc = st.columns(min(len(vc), 6))
            for i, (k, v) in enumerate(vc.items()):
                if i < len(sc): sc[i].metric(k, f"{v}건")
        render_table(f_search)

    for i, prod in enumerate(prod_list_d):
        with d_tabs[i+1]:
            pdata = f_search[f_search["제품명"] == prod]
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


# ═══ TAB 6: 만족도 ══════════════════════════════════════════════════════════
with tab6:
    @st.cache_data(ttl=60)
    def load_survey():
        try:
            client = _get_gspread_client()
            sh = client.open_by_key(SPREADSHEET_ID)
            ws = sh.worksheet(SURVEY_SHEET)
            rows = ws.get_all_values()
            if len(rows) < 2:
                return None
            sdf = pd.DataFrame(rows[1:], columns=rows[0])
            for c in ["전체만족도","접수편의성","담당자응대","안내및소통"]:
                if c in sdf.columns:
                    sdf[c] = pd.to_numeric(sdf[c], errors="coerce")
            sdf["제출일시"] = pd.to_datetime(sdf["제출일시"], errors="coerce")
            return sdf
        except Exception:
            return None

    sdf = load_survey()

    SURVEY_LABELS = {
        "전체만족도": "전반적인 서비스 만족도",
        "접수편의성": "접수 과정 편의성",
        "담당자응대": "담당자 응대",
        "안내및소통": "진행 안내 및 소통",
    }

    if sdf is None or sdf.empty:
        st.info("아직 만족도 평가 데이터가 없습니다. 보고서 발송 이메일의 링크를 통해 수집됩니다.")
    else:
        total = len(sdf)
        score_cols = ["전체만족도","접수편의성","담당자응대","안내및소통"]
        avgs = {c: round(sdf[c].mean(), 2) for c in score_cols if c in sdf.columns}

        # KPI
        kc = st.columns(len(avgs) + 1)
        kc[0].metric("총 응답 수", f"{total}건")
        for i, (col, val) in enumerate(avgs.items()):
            kc[i+1].metric(SURVEY_LABELS.get(col, col), f"{val} / 5")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        c_left, c_right = st.columns(2)

        # 항목별 평균 가로 막대
        with c_left:
            with st.container(border=True):
                st.markdown("**항목별 평균 점수**")
                fig_avg = go.Figure(go.Bar(
                    y=[SURVEY_LABELS.get(k, k) for k in avgs.keys()],
                    x=list(avgs.values()),
                    orientation="h",
                    marker=dict(color="#F36C21", opacity=0.85),
                    text=[f"{v}점" for v in avgs.values()],
                    textposition="outside",
                    textfont=dict(size=12),
                ))
                fig_avg.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white", font=FONT,
                    height=240, margin=dict(t=10, b=10, l=10, r=60),
                    xaxis=dict(range=[0, 5.5], gridcolor="#f0f4f8", zeroline=False, showticklabels=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", zeroline=False),
                    showlegend=False,
                )
                st.plotly_chart(fig_avg, use_container_width=True)

        # 수리기간 분포
        with c_right:
            with st.container(border=True):
                st.markdown("**수리 기간 평가 분포**")
                if "수리기간" in sdf.columns:
                    sp = sdf["수리기간"].value_counts().reindex(["빠름","보통","느림"], fill_value=0)
                    fig_sp = go.Figure(go.Pie(
                        labels=sp.index, values=sp.values, hole=0.5,
                        marker=dict(colors=["#34a853","#fbbc04","#ea4335"],
                                    line=dict(color="white", width=2)),
                        textinfo="label+percent", textfont=dict(size=12),
                    ))
                    fig_sp.update_layout(
                        height=220, paper_bgcolor="white", font=FONT,
                        margin=dict(t=10, b=10, l=10, r=10), showlegend=False,
                    )
                    st.plotly_chart(fig_sp, use_container_width=True)

        # 전체만족도 분포 + 개별 응답 스캐터
        _tr_left, _tr_right = st.columns(2)

        with _tr_left:
            with st.container(border=True):
                st.markdown("**점수 분포**")
                if "전체만족도" in sdf.columns:
                    _dist = sdf["전체만족도"].dropna().astype(int).value_counts().reindex([1,2,3,4,5], fill_value=0)
                    _score_colors = ["#ea4335","#fbbc04","#fbbc04","#34a853","#34a853"]
                    fig_dist = go.Figure(go.Bar(
                        x=["1점\n매우불만족","2점\n불만족","3점\n보통","4점\n만족","5점\n매우만족"],
                        y=_dist.values,
                        marker=dict(color=_score_colors, opacity=0.85),
                        text=_dist.values,
                        textposition="outside",
                        textfont=dict(size=13, color="#1a1f36"),
                    ))
                    fig_dist.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white", font=FONT,
                        height=220, margin=dict(t=10, b=10, l=20, r=20),
                        xaxis=dict(gridcolor="#f0f4f8", zeroline=False, tickfont=dict(size=11)),
                        yaxis=dict(gridcolor="#f0f4f8", zeroline=False, rangemode="tozero",
                                   tick0=0, dtick=1),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)

        with _tr_right:
            with st.container(border=True):
                st.markdown("**개별 응답 추이**")
                trend = sdf.dropna(subset=["제출일시","전체만족도"]).copy()
                trend = trend.sort_values("제출일시")
                if not trend.empty:
                    _hover = trend.get("업체명", pd.Series([""] * len(trend))).fillna("").astype(str)
                    fig_sc = go.Figure(go.Scatter(
                        x=trend["제출일시"],
                        y=trend["전체만족도"],
                        mode="markers+text",
                        marker=dict(size=14, color="#F36C21",
                                    line=dict(width=2, color="white"),
                                    symbol="circle"),
                        text=trend["전체만족도"].astype(int).astype(str) + "점",
                        textposition="top center",
                        textfont=dict(size=11, color="#F36C21"),
                        hovertext=_hover,
                        hovertemplate="%{hovertext}<br>%{x|%m/%d}<br>%{y}점<extra></extra>",
                    ))
                    fig_sc.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white", font=FONT,
                        height=220, margin=dict(t=30, b=30, l=40, r=10),
                        yaxis=dict(range=[0, 5.8], gridcolor="#f0f4f8", zeroline=False,
                                   tick0=1, dtick=1, tickvals=[1,2,3,4,5]),
                        xaxis=dict(gridcolor="#f0f4f8", zeroline=False),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_sc, use_container_width=True)

        # 최근 응답 목록
        with st.container(border=True):
            st.markdown("**최근 응답 목록**")
            show_cols = [c for c in ["제출일시","업체명","시리얼","전체만족도",
                                      "접수편의성","담당자응대","수리기간","안내및소통"] if c in sdf.columns]
            recent = sdf[show_cols].sort_values("제출일시", ascending=False).head(20).copy()
            recent["제출일시"] = recent["제출일시"].dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(recent, use_container_width=True, hide_index=True, height=300)


# ═══ TAB 7: 업체별 조회 ═════════════════════════════════════════════════════
with tab7:
    import re as _re

    # 수동 별칭 — 같은 업체인데 이름이 다른 경우 여기에 추가
    CO_ALIASES = {
        "태인메딕스 주식회사": "태인메딕스",
        "주식회사 태인메딕스": "태인메딕스",
    }

    def _co_group(name):
        """업체명에서 기본 그룹명 추출"""
        n = str(name).strip()
        # 수동 별칭 우선 적용
        if n in CO_ALIASES:
            return CO_ALIASES[n]
        # _ 기준으로만 분리
        n = n.split('_')[0].strip()
        # 법인 형태 suffix/prefix 제거 (주식회사, 유한회사 등)
        n = _re.sub(r'\s*(주식회사|유한회사|유한책임회사)\s*$', '', n).strip()
        n = _re.sub(r'^(주식회사|유한회사)\s*', '', n).strip()
        # 지역명 suffix 제거
        n = _re.sub(r'\s*(지점|지사|센터|본점|부산|서울|대구|광주|대전|인천|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s*$', '', n).strip()
        return n if n else str(name).strip()

    company_list = sorted(df["업체명"].dropna().unique().tolist())
    if not company_list:
        st.info("업체 데이터가 없습니다.")
    else:
        # 그룹 매핑 생성
        _group_map = {}  # 그룹명 → [업체명 리스트]
        for _c in company_list:
            _g = _co_group(_c)
            _group_map.setdefault(_g, []).append(_c)

        # 검색창
        _ca, _cb = st.columns([4, 1])
        with _ca:
            _co_search = st.text_input("🔍 업체명 검색", placeholder="업체명 입력", label_visibility="collapsed")
        with _cb:
            _co_clear = st.button("초기화", use_container_width=True, key="co_clear")
        if _co_clear:
            _co_search = ""

        # 검색 필터링
        if _co_search.strip():
            _kw = _co_search.strip().lower()
            _filtered_groups = {g: v for g, v in _group_map.items() if _kw in g.lower() or any(_kw in c.lower() for c in v)}
        else:
            _filtered_groups = _group_map

        if not _filtered_groups:
            st.warning("검색 결과가 없습니다.")
        else:
            # 드롭다운 표시명 (그룹에 여러 업체면 N개 표시)
            _display_list = sorted([
                f"{g} ({len(v)}개)" if len(v) > 1 else g
                for g, v in _filtered_groups.items()
            ])
            _sel_display = st.selectbox("업체 선택", _display_list, key="co_sel")

            # 선택된 그룹명 역추출
            _sel_group = _re.sub(r'\s*\(\d+개\)$', '', _sel_display).strip()
            _sel_companies = _filtered_groups.get(_sel_group, [_sel_group])

            if len(_sel_companies) > 1:
                st.caption(f"포함 업체: {' / '.join(_sel_companies)}")

            co_df = df[df["업체명"].isin(_sel_companies)].copy()

            st.divider()

            # ── KPI ──────────────────────────────────────────────────────────
            _co_total = len(co_df)
            _co_done  = len(co_df[co_df["상태"] == "완료"])
            _co_prog  = _co_total - _co_done
            _co_comp  = co_df[co_df["상태"] == "완료"].copy()
            _co_comp["처리일수"] = (_co_comp["완료일자"] - _co_comp["접수일자"]).dt.days
            _co_avg_days = round(_co_comp["처리일수"].dropna().mean(), 1) if not _co_comp.empty else "-"
            _co_dup = int(co_df["시리얼"].isin(dup_sns.index).sum())

            ck1, ck2, ck3, ck4, ck5 = st.columns(5)
            ck1.metric("총 접수", f"{_co_total}건")
            ck2.metric("완료", f"{_co_done}건")
            ck3.metric("진행중", f"{_co_prog}건", delta_color="off")
            ck4.metric("평균 처리기간", f"{_co_avg_days}일" if _co_avg_days != "-" else "-", delta_color="off")
            ck5.metric("중복 S/N", f"{_co_dup}건",
                       "⚠ 재접수 주의" if _co_dup else "이상 없음",
                       delta_color="inverse" if _co_dup else "off")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 제품별 + 유형별 분포 ─────────────────────────────────────────
            _cc1, _cc2 = st.columns(2)

            with _cc1:
                with st.container(border=True):
                    st.markdown("**제품별 접수 현황**")
                    _cp = co_df.groupby("제품명")["수량"].sum().reset_index().sort_values("수량", ascending=True)
                    if not _cp.empty:
                        fig_cp = go.Figure(go.Bar(
                            y=_cp["제품명"], x=_cp["수량"], orientation="h",
                            marker=dict(color=[PALETTE[i % len(PALETTE)][0] for i in range(len(_cp))], opacity=0.85),
                            text=_cp["수량"], textposition="outside", textfont=dict(size=12),
                        ))
                        fig_cp.update_layout(
                            plot_bgcolor="white", paper_bgcolor="white", font=FONT,
                            height=max(160, len(_cp) * 44 + 40),
                            margin=dict(t=10, b=10, l=10, r=50),
                            xaxis=dict(gridcolor="#f0f4f8", zeroline=False, showticklabels=False),
                            yaxis=dict(zeroline=False, tickfont=dict(size=12)),
                            showlegend=False,
                        )
                        st.plotly_chart(fig_cp, use_container_width=True)

            with _cc2:
                with st.container(border=True):
                    st.markdown("**유형별 접수 현황**")
                    if "유형" in co_df.columns:
                        _ct = co_df[co_df["유형"].astype(str).str.strip() != ""].groupby("유형")["수량"].sum().reset_index().sort_values("수량", ascending=True)
                        if not _ct.empty:
                            fig_ct = go.Figure(go.Bar(
                                y=_ct["유형"], x=_ct["수량"], orientation="h",
                                marker=dict(color=[PALETTE[i % len(PALETTE)][0] for i in range(len(_ct))], opacity=0.85),
                                text=_ct["수량"], textposition="outside", textfont=dict(size=12),
                            ))
                            fig_ct.update_layout(
                                plot_bgcolor="white", paper_bgcolor="white", font=FONT,
                                height=max(160, len(_ct) * 44 + 40),
                                margin=dict(t=10, b=10, l=10, r=50),
                                xaxis=dict(gridcolor="#f0f4f8", zeroline=False, showticklabels=False),
                                yaxis=dict(zeroline=False, tickfont=dict(size=12)),
                                showlegend=False,
                            )
                            st.plotly_chart(fig_ct, use_container_width=True)

            # ── 만족도 ───────────────────────────────────────────────────────
            @st.cache_data(ttl=60)
            def load_survey_co():
                try:
                    client = _get_gspread_client()
                    sh = client.open_by_key(SPREADSHEET_ID)
                    ws = sh.worksheet(SURVEY_SHEET)
                    rows = ws.get_all_values()
                    if len(rows) < 2:
                        return None
                    sdf2 = pd.DataFrame(rows[1:], columns=rows[0])
                    for c in ["전체만족도","접수편의성","담당자응대","안내및소통"]:
                        if c in sdf2.columns:
                            sdf2[c] = pd.to_numeric(sdf2[c], errors="coerce")
                    return sdf2
                except Exception:
                    return None

            sdf2 = load_survey_co()
            if sdf2 is not None and not sdf2.empty and "업체명" in sdf2.columns:
                co_survey = sdf2[sdf2["업체명"].isin(_sel_companies)]
                if not co_survey.empty:
                    with st.container(border=True):
                        st.markdown("**만족도 평가 결과**")
                        _s_cols = ["전체만족도","접수편의성","담당자응대","안내및소통"]
                        _s_avgs = {c: round(co_survey[c].mean(), 2) for c in _s_cols if c in co_survey.columns}
                        _sc = st.columns(len(_s_avgs) + 1)
                        _sc[0].metric("응답 수", f"{len(co_survey)}건")
                        for i, (col, val) in enumerate(_s_avgs.items()):
                            _sc[i+1].metric(SURVEY_LABELS.get(col, col), f"{val} / 5")

            # ── 전체 AS 이력 ─────────────────────────────────────────────────
            with st.container(border=True):
                st.markdown("**전체 AS 이력**")
                _dcols = [c for c in ["순번","접수일자","HA번호","제품명","시리얼",
                                       "유형","증상","원인","처치","상태","완료일자"] if c in co_df.columns]
                _co_view = co_df[_dcols].sort_values("접수일자", ascending=False).copy()
                for col in ["접수일자","완료일자"]:
                    if col in _co_view.columns:
                        _co_view[col] = pd.to_datetime(_co_view[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
                def _hl_co(row):
                    if row.get("상태") == "진행중": return ["background-color:#fffbf0"] * len(row)
                    return [""] * len(row)
                st.dataframe(_co_view.style.apply(_hl_co, axis=1),
                             use_container_width=True, hide_index=True, height=400)
