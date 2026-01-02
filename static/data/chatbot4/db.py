import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

# ========== 기본 설정 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # chatbot4 기준 경로
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# ========= 문서 폴더 경로 설정 =========
documents_path = os.path.join(BASE_DIR, "documents")

if not os.path.exists(documents_path):
    print(f"⚠️ documents 폴더가 없습니다. 새로 생성합니다: {documents_path}")
    os.makedirs(documents_path, exist_ok=True)
    print("폴더만 생성하고 종료합니다. 여기에 .txt 파일을 넣고 다시 실행하세요.")
    exit()

# ========= 문서 로드 =========
try:
    loader = DirectoryLoader(
        path=documents_path,
        glob="**/*.txt",
        loader_cls=lambda p: TextLoader(p, encoding="utf-8")
    )
    documents = loader.load()
    if not documents:
        print(f"⚠️ {documents_path} 안에 .txt 문서가 없습니다. 파일을 추가해주세요.")
        exit()
    print(f"📄 문서 {len(documents)}개 불러옴.")
except Exception as e:
    print(f"❌ 문서 로드 중 오류 발생: {e}")
    exit()

# ========= 문서 분할 =========
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)
chunks = text_splitter.split_documents(documents)
print(f"🔹 총 {len(chunks)}개의 청크로 분할 완료.")

# ========= 임베딩 생성 및 저장 =========
try:
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=os.path.join(BASE_DIR, "chroma_db")
    )
    vectordb.persist()
    print(f"✅ 데이터베이스에 저장된 문서 수: {vectordb._collection.count()}")
except Exception as e:
    print(f"❌ 임베딩 또는 DB 저장 중 오류 발생: {e}")