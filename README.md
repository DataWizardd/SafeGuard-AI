# SafeGuard-AI
산업 안전 작업허가를 돕는 Streamlit 기반 멀티 에이전트 애플리케이션입니다. LangGraph로 오케스트레이션된 LLM 에이전트가 작업 설명을 받아 관련 규정(RAG), Fine-Kinney 위험도, PDF 작업허가서를 자동으로 생성합니다. 

## 주요 기능
- **Main Orchestrator** → 입력/이력 검증 후 다음 단계 분기.
- **Regulation Agent** → MSDS·SOP·관련 법령을 RAG로 검색(FAISS + BGE-M3 임베딩).
- **Risk Analyst** → Fine-Kinney 기반 위험도 계산 및 리포트 생성.
- **Admin Agent** → 요약·이유 작성 후 작업허가서 PDF(`outputs/`) 자동 생성.
- **UI** → Streamlit 채팅형 인터페이스, 여러 세션 관리, Phoenix 추적 링크 제공.

## 폴더 구조 참고
- `app.py` — Streamlit UI 및 Phoenix 초기화.
- `agent_graph.py` — LangGraph로 정의한 에이전트 워크플로(오케스트레이터 → 규정 탐색 → 위험도 → PDF).
- `rag_setup.py` — `data/`의 PDF로 FAISS 벡터 DB 구성(BAAI/bge-m3 임베딩).
- `pdf_gen.py` — 위험도·요약을 담은 작업허가서 PDF 생성.
- `prompts/` — 각 에이전트 시스템 프롬프트.