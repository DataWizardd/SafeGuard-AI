import os
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# [변경] OpenAI 대신 HuggingFaceEmbeddings 사용
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# 환경 변수 로드
load_dotenv()

DB_PATH = "./faiss_db"

def get_retriever():
    """
    저장된 FAISS DB가 있으면 불러오고, 없으면 BGE-M3 모델로 새로 만듭니다.
    """
    
    # [변경 1] 임베딩 모델을 'BAAI/bge-m3'로 교체
    # bge-m3는 다국어(한국어 포함) 성능이 매우 뛰어난 SOTA 모델입니다.
    print("🧠 임베딩 모델 로드 중 (BAAI/bge-m3)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': 'cpu'}, # GPU가 있다면 'cuda'로 변경
        encode_kwargs={'normalize_embeddings': True} # 코사인 유사도를 위해 정규화
    )

    # 1. 이미 만들어진 DB가 있는지 확인
    if os.path.exists(DB_PATH):
        print("💾 기존 벡터 DB를 로드합니다...")
        try:
            vectorstore = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
            
            # [변경 2] 고급 검색 설정: 유사도 0.7 이상인 것만 최대 8개 가져오기
            return vectorstore.as_retriever(
                search_type="similarity", # threshold 방식 대신 기본 similarity 추천
                search_kwargs={"k": 6}    # 개수는 6개 정도
            )
        except Exception as e:
            print(f"⚠️ 기존 DB 로드 실패 (아마도 임베딩 모델 불일치): {e}")
            print("🗑️ 기존 DB를 삭제하고 새로 생성합니다.")
            shutil.rmtree(DB_PATH) # 폴더 삭제

    # 2. 없으면 새로 생성 (PDF 로드)
    print("🔄 새로운 벡터 DB를 생성합니다...")
    if not os.path.exists("./data"):
        os.makedirs("./data")
        print("⚠️ 'data' 폴더가 비어있습니다. PDF 파일을 넣어주세요.")
        return None

    documents = []
    for file in os.listdir("./data"):
        if file.endswith(".pdf"):
            print(f"   - 로딩 중: {file}")
            loader = PyPDFLoader(f"./data/{file}")
            docs = loader.load()
            documents.extend(docs)

    if not documents:
        print("❌ 로드할 PDF 파일이 없습니다.")
        return None

    # 3. 텍스트 분할 (Chunking)
    # BGE-M3는 긴 문맥도 잘 처리하므로 chunk_size를 조금 넉넉하게 줘도 됩니다.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = text_splitter.split_documents(documents)

    # 4. 벡터 저장소 생성 및 저장
    print("vectors 생성 중... (시간이 조금 걸릴 수 있습니다)")
    vectorstore = FAISS.from_documents(splits, embeddings)
    vectorstore.save_local(DB_PATH)
    print("🎉 DB 생성 및 저장 완료!")

    # 리턴 시에도 동일한 검색 조건 적용
    return vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": 0.4, 
            "k": 8
        }
    )

if __name__ == "__main__":
    get_retriever()