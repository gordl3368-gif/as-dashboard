# -*- coding: utf-8 -*-
import streamlit as st
from google.oauth2 import service_account
import gspread
import datetime
import os

SPREADSHEET_ID = "1tsdHzv1l__d63BQpTf6yFnxRn22KhpCwo7HJG61oYwg"
SURVEY_SHEET   = "만족도평가"
SA_PATH        = r"C:\Users\user\AS자동화\보고서발송\service_account.json"

st.set_page_config(page_title="AS 만족도 평가 | CGBIO", page_icon="⭐", layout="centered")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html,body,[class*="css"],.stApp{font-family:'Noto Sans KR','Malgun Gothic',sans-serif!important;}
[data-testid="stSidebarNav"]{display:none!important;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
header[data-testid="stHeader"]{display:none!important;}
.block-container{padding-top:1.5rem!important;max-width:560px!important;margin:0 auto!important;}
div[data-testid="stForm"]{border:none!important;padding:0!important;}
.stRadio>div{gap:8px!important;}
</style>""", unsafe_allow_html=True)

params  = st.query_params
seq     = params.get("seq", "")
company = params.get("company", "")
serial  = params.get("serial", "")

# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#F36C21;padding:22px 28px;border-radius:12px;margin-bottom:24px;">
  <div style="color:white;font-size:20px;font-weight:700;letter-spacing:-0.3px;">㈜시지바이오 A/S센터</div>
  <div style="color:rgba(255,255,255,0.85);font-size:13px;margin-top:4px;">A/S 서비스 만족도 평가</div>
</div>
""", unsafe_allow_html=True)

if company:
    st.markdown(f"**{company}** 담당자님, A/S 서비스를 이용해 주셔서 감사합니다.")
else:
    st.markdown("A/S 서비스를 이용해 주셔서 감사합니다.")

if serial:
    st.caption(f"제품 S/N: {serial}")

st.markdown("평가해 주신 내용은 서비스 개선에 소중하게 활용됩니다.")
st.divider()

# ── 이미 제출됐으면 감사 메시지 ────────────────────────────────────────────────
if st.session_state.get("survey_done"):
    st.success("✅ 소중한 평가를 남겨주셔서 감사합니다!")
    st.markdown("<div style='text-align:center;color:#9ca3af;font-size:13px;margin-top:32px;'>㈜시지바이오 A/S센터</div>", unsafe_allow_html=True)
    st.stop()

# ── 설문 폼 ───────────────────────────────────────────────────────────────────
OPTS  = ["매우 불만족", "불만족", "보통", "만족", "매우 만족"]
SCORE = {s: i+1 for i, s in enumerate(OPTS)}

with st.form("survey"):
    st.markdown("**1. 전체 만족도**")
    q1 = st.radio("전체만족도", OPTS, index=4, horizontal=True, label_visibility="collapsed")

    st.markdown("**2. 접수 편의성** — 접수 과정이 불편하진 않으셨나요?")
    q2 = st.radio("접수편의성", OPTS, index=4, horizontal=True, label_visibility="collapsed")

    st.markdown("**3. 담당자 응대** — 담당자가 친절하고 전문적이었나요?")
    q3 = st.radio("담당자응대", OPTS, index=4, horizontal=True, label_visibility="collapsed")

    st.markdown("**4. 수리 기간** — 수리 처리 속도는 어떠셨나요?")
    q4 = st.radio("수리기간", ["빠름", "보통", "느림"], index=0, horizontal=True, label_visibility="collapsed")

    st.markdown("**5. 안내 및 소통** — 진행 상황을 잘 안내받으셨나요?")
    q5 = st.radio("안내및소통", OPTS, index=4, horizontal=True, label_visibility="collapsed")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    submitted = st.form_submit_button("제출하기", use_container_width=True, type="primary")

if submitted:
    try:
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        try:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=SCOPES)
        except Exception:
            creds = service_account.Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SPREADSHEET_ID)

        try:
            ws = sh.worksheet(SURVEY_SHEET)
        except Exception:
            ws = sh.add_worksheet(title=SURVEY_SHEET, rows=1000, cols=20)
            ws.append_row(["제출일시","순번","업체명","시리얼",
                           "전체만족도","접수편의성","담당자응대","수리기간","안내및소통"])

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([now, seq, company, serial,
                       SCORE[q1], SCORE[q2], SCORE[q3], q4, SCORE[q5]])

        st.session_state.survey_done = True
        st.rerun()

    except Exception as e:
        st.error(f"제출 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.\n\n오류: {e}")
