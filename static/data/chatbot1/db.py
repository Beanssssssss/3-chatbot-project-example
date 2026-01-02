import os
import uuid
import json
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# ========== 기본 설정 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 항상 chatbot1 기준 경로로 고정
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# ========= DB 초기화 함수 =========
def init_text_db(db_path="chardb_embedding"):
    db_path = os.path.join(BASE_DIR, db_path)
    os.makedirs(db_path, exist_ok=True)
    dbclient = chromadb.PersistentClient(path=db_path)
    collection = dbclient.create_collection(name="rag_collection", get_or_create=True)
    return dbclient, collection

def init_image_db(db_path="imagedb_embedding"):
    db_path = os.path.join(BASE_DIR, db_path)
    os.makedirs(db_path, exist_ok=True)
    dbclient = chromadb.PersistentClient(path=db_path)
    collection = dbclient.create_collection(name="rag_collection", get_or_create=True)
    return dbclient, collection

# ========= 텍스트 데이터 처리 =========
def load_text_files(folder_path):
    folder_path = os.path.join(BASE_DIR, folder_path)
    if not os.path.exists(folder_path):
        print(f"⚠️ 경로 없음: {folder_path}, 폴더를 생성합니다.")
        os.makedirs(folder_path, exist_ok=True)
        return []
    docs = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                docs.append((filename, text))
                print(f"[불러옴] {filename}")
    return docs

def get_text_embedding(text, model="text-embedding-3-large"):
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

def parse_qa_blocks(filename, raw_text):
    blocks = []
    for raw in raw_text.strip().split("\n\n"):
        lines = raw.strip().split("\n")
        keywords, questions, answer = [], [], ""
        for line in lines:
            if line.startswith("키워드:"):
                keywords = [kw.strip() for kw in line.replace("키워드:", "").split(",") if kw.strip()]
            elif line.startswith("질문:"):
                questions.append(line.replace("질문:", "").strip())
            elif line.startswith("답변:"):
                answer = line.replace("답변:", "").strip()
        if questions and answer:
            embedding_text = " ".join(keywords + questions)
            metadata = {
                "type": "qa_block",
                "keywords": ", ".join(keywords),
                "questions": " / ".join(questions),
                "filename": filename
            }
            blocks.append((embedding_text, answer, metadata))
    return blocks

text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)

# ========= 이미지 데이터 처리 =========
def load_json_mapping(file_path):
    file_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(file_path):
        print(f"⚠️ JSON 파일 없음: {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_image_embedding(text, embedder):
    return embedder.embed_query(text)

# ========= 실행 =========
if __name__ == "__main__":
    # -- 텍스트 데이터 임베딩 처리 --
    text_folder_path = "chardb_text"
    docs = load_text_files(text_folder_path)

    dbclient, text_collection = init_text_db("chardb_embedding")
    doc_id = 0

    for filename, text in docs:
        if filename == "질문답변식.txt":
            qa_blocks = parse_qa_blocks(filename, text)
            for emb_text, answer, metadata in qa_blocks:
                doc_id += 1
                embedding = get_text_embedding(emb_text)
                text_collection.add(
                    documents=[answer],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[str(doc_id)]
                )
        else:
            chunks = text_splitter.split_text(text)
            for idx, chunk in enumerate(chunks):
                doc_id += 1
                embedding = get_text_embedding(chunk)
                text_collection.add(
                    documents=[chunk],
                    embeddings=[embedding],
                    metadatas=[{
                        "type": "text",
                        "filename": filename,
                        "chunk_index": idx
                    }],
                    ids=[str(doc_id)]
                )

    print("✅ 질문답변 블록 + 일반 텍스트 임베딩 완료!")

    # -- 이미지 데이터 임베딩 처리 --
    image_dbclient, image_collection = init_image_db("imagedb_embedding")
    embedder = OpenAIEmbeddings(model="text-embedding-3-large")
    mapping = load_json_mapping("imagedb_text/photo_data.json")

    doc_id_image = 0
    for key, description in mapping.items():
        doc_id_image += 1
        embedding = get_image_embedding(description, embedder)
        image_collection.add(
            documents=[description],
            embeddings=[embedding],
            metadatas=[{"key": key, "description": description}],
            ids=[str(doc_id_image)]
        )

    print("✅ 모든 이미지 매핑 데이터의 임베딩 완료!")