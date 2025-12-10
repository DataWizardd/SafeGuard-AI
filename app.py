import streamlit as st
import phoenix as px
from phoenix.otel import register
import os 
# ---------------------------------------------------------
# [Phoenix 설정] 최신 register 방식 적용
# ---------------------------------------------------------
@st.cache_resource
def setup_phoenix():
    # 1. Phoenix 서버 시작 (UI 실행)
    session = px.launch_app()
    
    # 2. Tracer 등록 및 자동 기기화 (Auto-Instrumentation)
    # 설치된 라이브러리(LangChain, OpenAI)를 자동으로 감지해서 추적합니다.
    register(
        project_name="SafeGuard-AI",  # <--- 요청하신 프로젝트명
        endpoint="http://localhost:6006/v1/traces",
        auto_instrument=True
    )
    
    print(f"🦅 Phoenix가 실행되었습니다: {session.url}")
    return session

# Phoenix 실행 (반드시 다른 import보다 먼저 실행되어야 함)
phoenix_session = setup_phoenix()

# ---------------------------------------------------------
# [중요] Phoenix 설정 완료 후 그래프 가져오기
# ---------------------------------------------------------
from agent_graph import app_graph  # <--- 위치 중요!

st.set_page_config(page_title="SafeGuard-AI", layout="wide")
st.title("🛡️ SafeGuard-AI (Smart Factory Safety)")
st.caption("제조 현장 작업 허가 및 위험성 평가 자동화 시스템")

# [사이드바]
with st.sidebar:
    st.header("🔧 개발자 도구")
    st.success("🦅 Phoenix Tracing 활성화됨")
    if phoenix_session:
        st.link_button("🚀 추적 대시보드 열기", phoenix_session.url)
    st.divider()

# [메인 로직]
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("is_html"):
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.write(msg["content"])

# 사용자 입력 처리
if prompt := st.chat_input("작업 내용을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        status_container = st.container(border=True)
        status_text = status_container.empty()
        
        inputs = {"user_input": prompt, "messages": [], "context": "", "risk_score": 0, "needs_more_info": False}
        final_res = None
        pdf_path = None
        
        try:
            status_text.info("🚀 안전 분석 프로세스를 시작합니다...")
            
            # 그래프 실행
            for output in app_graph.stream(inputs):
                for key, value in output.items():
                    # --- Coordinator ---
                    if key == "coordinator":
                        with status_container:
                            if value.get("needs_more_info"):
                                st.warning("🤖 **Main Coordinator:** 정보 부족 감지! 추가 질문을 생성합니다.")
                                final_res = value['messages'][0]
                            else:
                                st.success("🤖 **Main Coordinator:** 작업 의도 파악 완료. 규정 검색 에이전트를 호출합니다.")

                    # --- Regulation Agent ---
                    elif key == "regulation_finder":
                        with status_container:
                            st.info("📚 **Regulation Agent:** 관련 법령 및 사내 규정을 검색했습니다.")
                            raw_context = value['context']
                            if "\n\n---\n\n" in raw_context:
                                docs = raw_context.split("\n\n---\n\n")
                            else:
                                docs = [raw_context]

                            with st.expander(f"🔍 검색된 근거 자료 ({len(docs)}건) 상세보기"):
                                for i, doc in enumerate(docs):
                                    lines = doc.split("\n")
                                    source_line = lines[0] if lines else "출처 미상"
                                    content_text = "\n".join(lines[1:])
                                    st.markdown(f"**{i+1}. {source_line}**")
                                    st.caption(content_text[:200] + "..." if len(content_text) > 200 else content_text)
                                    st.divider()

                    # --- Risk Analyst ---
                    elif key == "risk_analyst":
                        score = value.get('risk_score', 0)
                        try:
                            if "**🎯 Fine-Kinney 위험성 평가 결과**" in value['context']:
                                report_content = value['context'].split("**🎯 Fine-Kinney 위험성 평가 결과**")[1]
                            else:
                                report_content = "상세 리포트 생성 실패"
                        except:
                            report_content = "분석 결과 없음"

                        with status_container:
                            if score >= 160:
                                st.error(f"⚠️ **Risk Analyst:** 고위험 판정! (Score: {score})")
                            else:
                                st.success(f"✅ **Risk Analyst:** 허용 가능 범위 (Score: {score})")
                            
                            st.markdown("---")
                            st.markdown("**🎯 정량적 위험성 평가 (Fine-Kinney)**")
                            st.markdown(report_content, unsafe_allow_html=True)

                    # --- Admin Agent ---
                    elif key == "admin_agent":
                        with status_container:
                            st.write("📝 **Admin Agent:** 최종 결과 보고서 및 PDF를 생성 중입니다...")
                        final_res = value.get('final_output', "결과 생성 실패")
                        pdf_path = value.get('pdf_path', None)

            status_text.empty()
            
        except Exception as e:
            st.error(f"에러 발생: {e}")

        # 최종 결과 출력
        if final_res:
            res_container = st.container(border=True)
            res_container.markdown(final_res)
            
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as file:
                    res_container.download_button(
                        label="📄 정식 작업허가서(PDF) 다운로드",
                        data=file,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )
            
            st.session_state.messages.append({"role": "assistant", "content": final_res})