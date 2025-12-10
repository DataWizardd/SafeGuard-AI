import os
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from rag_setup import get_retriever
from pdf_gen import generate_permit_pdf

# LLM 설정
llm = ChatOpenAI(model="gpt-4o", temperature=0)
retriever = get_retriever()

# --- [NEW] 프롬프트 로더 함수 ---
def load_prompt(filename, **kwargs):
    """
    prompts 폴더의 md 파일을 읽어서 변수({key})를 채워주는 함수
    """
    file_path = os.path.join("prompts", filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # 파일 내용에 변수값 주입 (format 사용)
            return content.format(**kwargs)
    except Exception as e:
        print(f"❌ 프롬프트 로드 실패 ({filename}): {e}")
        return ""

# --- 1. 상태(State) 정의 ---
class AgentState(TypedDict):
    user_input: str
    chat_history: str
    messages: List[str]
    context: str
    risk_level: str
    risk_score: int
    final_output: str
    pdf_path: str
    needs_more_info: bool

# --- 2. 노드(Agent) 정의 ---

def coordinator(state: AgentState):
    """Main Orchestrator: 의도 파악 및 정보 병합"""
    print("🤖 [Coordinator] 지능형 분석 중...")
    
    # [수정] 파일에서 프롬프트 로드
    prompt = load_prompt(
        "coordinator.md", 
        chat_history=state.get('chat_history', '없음'),
        user_input=state['user_input']
    )
    
    response = llm.invoke([HumanMessage(content=prompt)]).content
    
    if response.startswith("MISSING"):
        question = response.replace("MISSING:", "").strip()
        return {"needs_more_info": True, "messages": [question]}
    
    return {"needs_more_info": False}

def regulation_finder(state: AgentState):
    print("📚 [Regulation Agent] 규정 검색 중 (이중 검색)...")
    query = state['user_input']
    
    # [전략 1] 일반 검색 (법령, 가이드북 위주)
    docs_general = retriever.invoke(query)
    
    # [전략 2] 사내 규정 강제 검색 (S-Chem 키워드 추가)
    # 쿼리에 회사 이름을 강제로 붙여서 검색기가 사내 규정을 찾도록 유도
    company_query = f"{query} S-Chem 사내 안전 작업 규정 절차"
    docs_company = retriever.invoke(company_query)
    
    # [전략 3] 결과 병합 (중복 제거 및 우선순위 조정)
    # 사내 규정 검색 결과(docs_company)를 리스트 앞쪽에 배치하여 강조
    combined_docs = docs_company[:2] + docs_general 
    
    # 중복 제거 (내용 기준)
    seen = set()
    unique_docs = []
    for doc in combined_docs:
        # 문서 내용의 앞 50글자를 키로 사용하여 중복 체크
        doc_key = doc.page_content[:50]
        if doc_key not in seen:
            seen.add(doc_key)
            unique_docs.append(doc)
    
    # 최종 상위 6~8개만 선택
    final_docs = unique_docs[:8]

    # [디버깅] 검색 결과 출력
    print(f"🔍 최종 확보된 문서: {len(final_docs)}건")

    if not final_docs:
        return {"context": "관련 규정을 찾을 수 없습니다."}

    formatted_docs = []
    for doc in final_docs:
        filename = os.path.basename(doc.metadata.get("source", "파일_없음"))
        content = doc.page_content.strip()
        if not content: continue
            
        formatted_docs.append(f"📄 [출처: {filename}]\n{content}")
    
    context_text = "\n\n---\n\n".join(formatted_docs)
    return {"context": context_text}

def risk_analyst(state: AgentState):
    """Fine-Kinney 알고리즘 기반 정량적 위험성 평가"""
    print("⚠️ [Risk Analyst] 위험도 계산 중 (Fine-Kinney)...")
    
    # [수정] 파일에서 프롬프트 로드
    prompt = load_prompt(
        "risk_analyst.md",
        chat_history=state.get('chat_history', '없음'),
        user_input=state['user_input'],
        context=state['context']
    )
    
    response = llm.invoke([HumanMessage(content=prompt)]).content
    
    try:
        # 정규표현식 파싱
        p_match = re.search(r"P\s*[:=]\s*([\d\.]+)", response)
        e_match = re.search(r"E\s*[:=]\s*([\d\.]+)", response)
        c_match = re.search(r"C\s*[:=]\s*([\d\.]+)", response)
        r_match = re.search(r"R\s*[:=]\s*([\d\.]+)", response)
        
        p_score = float(p_match.group(1)) if p_match else 0
        e_score = float(e_match.group(1)) if e_match else 0
        c_score = float(c_match.group(1)) if c_match else 0
        
        if r_match:
            r_score = float(r_match.group(1))
        else:
            r_score = p_score * e_score * c_score
            
        type_match = re.search(r"재해유형\s*[:=]\s*(.+)", response)
        accident_type = type_match.group(1).strip() if type_match else "복합 위험"

        if r_score >= 320: level = "Very High"
        elif r_score >= 160: level = "High"
        elif r_score >= 70: level = "Medium"
        else: level = "Low"
        
        final_report = f"""
**🎯 Fine-Kinney 위험성 평가 결과**
* **재해 형태:** {accident_type}
* **계산 공식:** $Risk = P \\times E \\times C$
* **상세 점수:**
    * 가능성(P): **{p_score}**
    * 노출빈도(E): **{e_score}**
    * 강도(C): **{c_score}**
* **최종 위험도(R):** <span style='color:red; font-size:1.2em; font-weight:bold;'>{int(r_score)}점</span> ({level})
"""
    except Exception as e:
        print(f"파싱 에러: {e} / LLM 응답: {response}")
        r_score = 0; level = "Error"; final_report = "위험성 평가 데이터를 추출할 수 없습니다."

    return {"risk_score": int(r_score), "risk_level": level, "context": state['context'] + "\n\n" + final_report}

def admin_agent(state: AgentState):
    """최종 PDF 생성 및 메시지 작성 (프롬프트 파일 분리 버전)"""
    print("📝 [Admin Agent] 작업 내용 요약 및 PDF 생성 중...")
    
    score = state['risk_score']
    context = state['context']
    history = state.get('chat_history', '')
    last_input = state['user_input']
    
    # ------------------------------------------------------------------
    # [STEP 1] 대화 기록을 바탕으로 '통합 작업 내용' 요약하기
    # ------------------------------------------------------------------
    # [수정] 하드코딩 대신 work_summary.md 파일 로드
    summary_prompt = load_prompt(
        "work_summary.md",
        history=history,
        last_input=last_input
    )
    
    # 만약 파일 로드 실패 시 대비용 안전장치
    if not summary_prompt:
        summary_prompt = f"대화기록: {history}\n마지막입력: {last_input}\n위 내용을 포함해 작업 내용을 한 문장으로 요약해."

    # 작업 제목을 LLM이 다시 씁니다.
    consolidated_work_info = llm.invoke([HumanMessage(content=summary_prompt)]).content.replace('"', '').strip()
    print(f"📌 통합된 작업 내용: {consolidated_work_info}")

    # ------------------------------------------------------------------
    # [STEP 2] 위험 요인 분석
    # ------------------------------------------------------------------
    # admin_agent.md 파일 로드
    reasoning_prompt_content = load_prompt(
        "admin_agent.md",
        user_input=consolidated_work_info, # 요약된 내용을 넣어줌
        context=context
    )
    
    reason_summary = llm.invoke([HumanMessage(content=reasoning_prompt_content)]).content
    
    # ------------------------------------------------------------------
    # [STEP 3] PDF 생성
    # ------------------------------------------------------------------
    try:
        # 요약된 작업 내용(consolidated_work_info)을 PDF 제목으로 전달
        pdf_file = generate_permit_pdf(score, state['risk_level'], reason_summary, consolidated_work_info)
    except Exception as e:
        print(f"PDF 에러: {e}")
        pdf_file = None
    
    # UI 메시지 생성
    if score >= 160:
        short_msg = f"🚨 **반려 (High Risk / {score}점)**\n상세 사유는 PDF 확인 필요."
    elif score >= 70:
        short_msg = f"⚠️ **조건부 승인 (Medium Risk / {score}점)**\n안전 조치 이행 후 작업 가능."
    else:
        short_msg = f"✅ **승인 (Low Risk / {score}점)**\n작업 허가서 발급 완료."
        
    return {"final_output": short_msg, "pdf_path": pdf_file}

# --- 3. 그래프 연결 ---
workflow = StateGraph(AgentState)
workflow.add_node("coordinator", coordinator)
workflow.add_node("regulation_finder", regulation_finder)
workflow.add_node("risk_analyst", risk_analyst)
workflow.add_node("admin_agent", admin_agent)
workflow.set_entry_point("coordinator")

def check_info(state):
    return "end" if state['needs_more_info'] else "next"

workflow.add_conditional_edges("coordinator", check_info, {"end": END, "next": "regulation_finder"})
workflow.add_edge("regulation_finder", "risk_analyst")
workflow.add_edge("risk_analyst", "admin_agent")
workflow.add_edge("admin_agent", END)

app_graph = workflow.compile()