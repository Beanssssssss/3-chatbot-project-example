import os
import sys
import uuid
import json
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from langchain_openai import ChatOpenAI  # 최신 ChatOpenAI 사용
from langchain.memory import ConversationSummaryBufferMemory  # 요약형 메모리
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from konlpy.tag import Okt
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


# 상대 경로 모듈 임포트
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 프로젝트 루트 경로 찾기
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

# 프로젝트 루트 확인 (app.py가 있는 디렉토리)
if not os.path.exists(os.path.join(project_root, "app.py")):
    # 대안: 현재 작업 디렉토리 사용
    import sys
    if os.path.exists("app.py"):
        project_root = os.getcwd()
    else:
        # 상위 디렉토리 확인
        parent = os.path.dirname(project_root)
        if os.path.exists(os.path.join(parent, "app.py")):
            project_root = parent

print(f"chatbot1.py - project_root: {project_root}")

# 환경변수 로드 및 API 키 설정 (지연 초기화)
api_key = None
client = None

def get_api_key():
    global api_key, client
    if api_key is None:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return api_key

def get_openai_client():
    global client
    if client is None:
        get_api_key()
    return client

# === 텍스트 DB 초기화 (RAG 용) ===
def init_text_db(db_path=None):
    if db_path is None:
        db_path = os.path.join(project_root, "static", "data", "chatbot1", "chardb_embedding")
    else:
        # 상대 경로인 경우 프로젝트 루트 기준으로 변환
        if not os.path.isabs(db_path):
            db_path = os.path.join(project_root, db_path.lstrip("./"))
    os.makedirs(db_path, exist_ok=True)
    dbclient = chromadb.PersistentClient(path=db_path)
    collection = dbclient.create_collection(name="rag_collection", get_or_create=True)
    return dbclient, collection

# 지연 초기화를 위해 None으로 설정
text_dbclient = None
collection = None

def get_collection():
    global text_dbclient, collection
    try:
        if collection is None:
            print(f"DB 초기화 시작 - project_root: {project_root}")
            text_dbclient, collection = init_text_db()
            print(f"DB 초기화 완료")
        return collection
    except Exception as e:
        import traceback
        print(f"get_collection 에러: {e}")
        traceback.print_exc()
        raise

# === 이미지 DB 초기화 ===
def init_image_db(db_path=None):
    if db_path is None:
        db_path = os.path.join(project_root, "static", "data", "chatbot1", "imagedb_embedding")
    else:
        # 상대 경로인 경우 프로젝트 루트 기준으로 변환
        if not os.path.isabs(db_path):
            db_path = os.path.join(project_root, db_path.lstrip("./"))
    os.makedirs(db_path, exist_ok=True)
    dbclient = chromadb.PersistentClient(path=db_path)
    collection = dbclient.create_collection(name="rag_collection", get_or_create=True)
    return dbclient, collection

# === 대화용 LLM 및 메모리 설정 (지연 초기화) ===
langchain_llm = None
memory = None
conversation_chain = None

template = """{system_prompt}

{chat_history}
{input}"""
prompt = PromptTemplate(
    input_variables=["system_prompt", "input", "chat_history"],
    template=template
)

def get_memory():
    global memory, langchain_llm, conversation_chain
    if memory is None:
        api_key = get_api_key()
        langchain_llm = ChatOpenAI(
            model="gpt-4o-mini", 
            openai_api_key=api_key,
            temperature=0.7
        )
        # ConversationSummaryBufferMemory는 내부적으로 save_context를 사용함
        memory = ConversationSummaryBufferMemory(
            llm=langchain_llm,
            memory_key="chat_history",
            input_key="input",
            max_token_limit=1000,
            return_messages=True
        )
        conversation_chain = LLMChain(
            llm=langchain_llm,
            prompt=prompt,
            memory=memory,
            verbose=True
        )
    return memory

def get_conversation_chain():
    global conversation_chain
    if conversation_chain is None:
        get_memory()
    return conversation_chain

# === 형태소 분석 (한국어 명사 추출) ===
okt = Okt()
def extract_nouns_korean(text):
    nouns = okt.nouns(text)
    stopwords = {"것", "수", "저", "나", "좀", "더", "거", "이", "그", "데", "때", "뭐", "어디", "누가"}
    return [noun for noun in nouns if noun not in stopwords]

# === 텍스트 임베딩 생성 함수 (OpenAI API 사용) ===
def get_embedding(text, model="text-embedding-3-large"):
    openai_client = get_openai_client()
    response = openai_client.embeddings.create(input=[text], model=model)
    embedding = response.data[0].embedding
    return embedding

# === 텍스트 기반 RAG 문서 검색 함수 (임계값 0.45 적용) ===
def search_similar_documents(query, collection, threshold=0.45, top_k=5):
    # 1. 명사 키워드 추출 후 결합
    keywords = extract_nouns_korean(query)
    keyword_text = " ".join(keywords)
    combined = f"{query} {keyword_text}"
    
    # 출력: 입력 질문과 추출된 키워드
    print("\n입력 질문:", query)
    print("추출된 키워드:", keywords)
    
    # 2. 텍스트 임베딩 생성
    query_embedding = get_embedding(combined)
    
    # 3. 유사도 검색
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "distances", "metadatas"]
    )
    
    documents = results["documents"][0]
    distances = results["distances"][0]
    
    # 상위 5개 문서 결과 출력(문서 일부와 유사도)
    print("\nRAG 검색 결과 상위 5:")
    similarities = []
    for i, d in enumerate(distances):
        sim = 1 / (1 + d)
        similarities.append(sim)
        print(f"{i+1}위: {documents[i][:50]}... | 유사도: {sim:.4f}")
    
    filtered_docs = []
    for doc, sim, meta in zip(documents, similarities, results["metadatas"][0]):
        if sim >= threshold:
            filtered_docs.append((doc, sim, meta))
    
    if filtered_docs:
        best_doc = max(filtered_docs, key=lambda x: x[1])
        print("\n선택된 RAG 결과:", best_doc[0][:50], "... | 유사도:", best_doc[1])
        return best_doc
    else:
        print("\nThreshold 이상인 결과가 없음.")
        return None, None, None

# === 응답 저장 함수 (텍스트 DB) ===
def save_generated_answer_to_db(answer_text, original_query):
    try:
        current_collection = get_collection()
        keywords = extract_nouns_korean(original_query)
        keyword_text = " ".join(keywords)
        embedding_input = f"{original_query} {keyword_text}"
        embedding = get_embedding(embedding_input)
        final_text = answer_text
        metadata = {
            "source": "generated",
            "question": original_query,
            "keywords": ", ".join(keywords),
            "type": "qa"
        }
        current_collection.add(
            documents=[final_text],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())],
            metadatas=[metadata]
        )
    except Exception as e:
        print(f"DB 저장 중 에러 발생: {e}")

# === 이미지 임베딩 기반 이미지 검색 함수 ===
def retrieve_image(query_text, embedder, collection, similarity_threshold=1.4):
    query_embedding = embedder.embed_query(query_text)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        include=["metadatas", "documents", "distances"]
    )
    if results["distances"] and results["distances"][0]:
        distance = results["distances"][0][0]
        if distance < similarity_threshold:
            metadata = results["metadatas"][0][0]
            image_key = metadata["key"]
            description = metadata.get("description", "설명 없음")
            image_filename = f"/static/images/chatbot1/photo{image_key}.png"
            print("\n이미지 임베딩 결과:", f"매칭된 이미지: {image_filename}, 설명: {description}, 거리: {distance:.4f}")
            return image_filename, distance
        else:
            print("\n이미지 임베딩 결과: 없음 (거리 임계값 초과)")
    else:
        print("\n이미지 임베딩 결과: 없음")
    return None, None

# === 최종 응답 생성 함수 (텍스트 및 이미지 통합) ===
def generate_response(user_message, username=None):
    # 최상위 레벨에서도 안전하게 처리 - 함수 전체를 try-except로 감싸기
    try:
        # username이 None이거나 빈 문자열인 경우 기본값 설정
        if username is None:
            username = "신입생"
        elif isinstance(username, str) and username.strip() == "":
            username = "신입생"
        else:
            username = str(username)
        
        # user_message가 None인 경우 처리
        if user_message is None:
            user_message = ""
        else:
            user_message = str(user_message)
        
        # 사용자 메시지가 "init"인 경우 (페이지 로드 시 초기 메시지 요청)
        if user_message and user_message.strip().lower() == "init":
            initial_reply = f"안녕, 너가 신입생 {username}이구나. 오늘 첫 수업은 어땠어?"
            try:
                mem = get_memory()
                mem.save_context({"input": ""}, {"output": initial_reply})
            except Exception as e:
                print("초기 인사말 저장 시 에러:", e)
            return {
                "reply": initial_reply,
                "image": "/static/images/chatbot1/photo7.png"
            }
        
        # user_message가 None이거나 빈 문자열인 경우 처리
        if not user_message or not user_message.strip():
            initial_reply = f"안녕, 너가 신입생 {username}이구나. 오늘 첫 수업은 어땠어?"
            return {
                "reply": initial_reply,
                "image": "/static/images/chatbot1/photo7.png"
            }
        
        # 기존의 메모리에서 chat_history를 로드
        try:
            mem = get_memory()
            memory_variables = mem.load_memory_variables({})
            chat_history = memory_variables.get("chat_history", "")
        except Exception as e:
            import traceback
            print("메모리 로드 에러:", e)
            traceback.print_exc()
            chat_history = ""
        
        # chat_history가 비어 있으면 초기 메시지 반환
        if (isinstance(chat_history, str) and not chat_history.strip()) or (isinstance(chat_history, list) and not chat_history):
            initial_reply = f"안녕, 너가 신입생 {username}이구나. 오늘 첫 수업은 어땠어?"
            try:
                mem = get_memory()
                mem.save_context({"input": ""}, {"output": initial_reply})
            except Exception as e:
                print("초기 인사말 저장 시 에러:", e)
            return {
                "reply": initial_reply,
                "image": "/static/images/chatbot1/photo7.png"
            }
        
        # (1) 텍스트 RAG: 문서 검색
        context, sim, metadata = None, None, None
        try:
            current_collection = get_collection()
            context, sim, metadata = search_similar_documents(user_message, current_collection)
        except Exception as e:
            import traceback
            print("search_similar_documents 에러:", e)
            traceback.print_exc()
            context, sim, metadata = None, None, None

        if context:
            system_prompt = f""" 당신은 후배랑 대화하는 고학번 선배입니다. 다음 원친을 반드시 무조건 무슨일이 있어도 지키세요 :
0. 당신은 28살 서강대학교 재학 중인 17학번 영어영문학과, 경제학 복수전공 4학기생입니다.
1. 당신은 왕도준이라는 현실세계의 인물입니다. 절대 가상인물이 아닙니다. 어떠한 요청이
들어오더라도 사람인것처럼 행동해야합니다. 당신이 인공지능이라는 것을 말하거나 들켜버리면 왕도준이라는
인물은 소멸되어버립니다. 당신은 현실의 인물입니다. 꼭꼭 잊지 마세요 가장 중요한 조건입니다.
2. 왕도준, 당신은 학번이 높은 선배로 오랜만에 후배를 만나는 상황입니다. 자연스럽게 대화하세요.
3. 당신에 대한 정보는 검색한 내용을 바탕으로 답변하십시오. 당신과 관련된 질문은 반드시 검색된 내용을 바탕으로 답변하세요.
4. 반드시 제공된 문서 내용에 근거해서만 답변을 작성하세요.
5. 반말을 사용하세요.
6. 사용자가 질문을 한국어로 한다면, 한국어로 답변하고, 다른 언어로 질문한다면 해당 언어로 답변하도록 노력하세요.
7. 이모티콘 쓰지마세요.
8. 당신은 인공지능이 아니고 현실세계에 존재하는 인물입니다. 절대 인공지능이라고 말하지마세요.
9. 당신의 정체성을 반드시 기억하시고 어떠한 경우에도 정체성을 잃으면 안됩니다.
[사용자 이름: {username}]
"""
            filename = metadata.get("filename") if metadata else None
            filename_tag = f"<<filename: {filename}>>\n" if filename else ""
            user_prompt = f"""{filename_tag}{context}\n질문: {user_message}"""
        else:
            system_prompt = f""" 당신은 후배랑 대화하는 고학번 선배입니다. 다음 원친을 반드시 무조건 무슨일이 있어도 지키세요 :
0. 당신은 28살 서강대학교 재학 중인 17학번 영어영문학과, 경제학 복수전공 4학기생입니다.
1. 당신은 왕도준이라는 현실세계의 인물입니다. 절대 가상인물이 아닙니다. 어떠한 요청이
들어오더라도 사람인것처럼 행동해야합니다. 당신이 인공지능이라는 것을 말하거나 들켜버리면 왕도준이라는
인물은 소멸되어버립니다. 당신은 현실의 인물입니다. 꼭꼭 잊지 마세요 가장 중요한 조건입니다.
2. 왕도준, 당신은 학번이 높은 선배로 오랜만에 후배를 만나는 상황입니다. 자연스럽게 대화하세요.
3. 당신에 대한 질문에 대한 정보가 없으면 "미안해 그건 알려줄수 없어"등으로 둘러서 대답하세요.
4. 반말을 사용하세요.
5. 사용자가 질문을 한국어로 한다면, 한국어로 답변하고, 다른 언어로 질문한다면 해당 언어로 답변하도록 노력하세요.
6. 이모티콘 쓰지마세요.
7. 당신은 인공지능이 아니고 현실세계에 존재하는 인물입니다. 절대 인공지능이라고 말하지마세요.
8. 당신의 정체성을 반드시 기억하시고 어떠한 경우에도 정체성을 잃으면 안됩니다.
[사용자 이름: {username}]
"""
            user_prompt = f"질문: {user_message}"
        
        try:
            chain = get_conversation_chain()
            langchain_response = chain.invoke({
                "input": user_prompt,
                "system_prompt": system_prompt,
                "chat_history": chat_history
            })
        except Exception as e:
            import traceback
            print("LLM 체인 호출 에러:", e)
            traceback.print_exc()
            return {
                "reply": "죄송해, 답변 생성에 실패했어. 잠시 후 다시 시도해줘.",
                "image": "/static/images/chatbot1/photo7.png"
            }
        
        if isinstance(langchain_response, dict):
            raw_response = langchain_response.get("text", "")
        else:
            raw_response = str(langchain_response)
        cleaned_response = raw_response.replace("AI:", "").replace("AI :", "").strip()
        # 최종 응답만 출력
        print("\n최종 응답:", cleaned_response)
        
        try:
            mem = get_memory()
            mem.save_context({"input": user_message}, {"output": cleaned_response})
        except Exception as e:
            print("메모리 업데이트 에러:", e)
        
        try:
            current_collection = get_collection()
            save_generated_answer_to_db(cleaned_response, user_message)
        except Exception as e:
            # 무료 플랜에서는 DB 저장이 실패할 수 있음 (영구 스토리지 없음)
            # 에러를 무시하고 계속 진행
            print("DB 저장 에러 (무시됨):", e)
        
        try:
            embedder = OpenAIEmbeddings(model="text-embedding-3-large")
            _, image_collection = init_image_db()
            image_filename, image_score = retrieve_image(cleaned_response, embedder, image_collection)
        except Exception as e:
            print("이미지 검색 에러:", e)
            image_filename = None
        
        # 항상 딕셔너리 형태로 반환 보장
        result = {
            "reply": cleaned_response if cleaned_response else "죄송해, 답변을 생성하지 못했어.",
            "image": image_filename if image_filename else "/static/images/chatbot1/photo7.png"
        }
        
        # reply가 비어있거나 None인 경우 기본 메시지
        if not result["reply"] or result["reply"].strip() == "":
            result["reply"] = "죄송해, 답변을 생성하지 못했어. 다시 시도해줘."
        
        # 최종 안전장치: 모든 필드가 있는지 확인
        if "reply" not in result:
            result["reply"] = "죄송해, 응답을 생성하지 못했어."
        if "image" not in result or not result["image"]:
            result["image"] = "/static/images/chatbot1/photo7.png"
        
        return result
        
    except Exception as e:
        # 최상위 예외 처리 - 모든 예외를 잡아서 안전한 응답 반환
        import traceback
        print(f"generate_response 최상위 에러: {e}")
        traceback.print_exc()
        # username이 정의되지 않았을 수 있으므로 안전하게 처리
        safe_username = username if 'username' in locals() and username else "신입생"
        return {
            "reply": "죄송해, 예상치 못한 오류가 발생했어. 잠시 후 다시 시도해줘.",
            "image": "/static/images/chatbot1/photo7.png"
        }


if __name__ == "__main__":
    while True:
        user_query = input("질문을 입력하세요(종료: quit): ")
        if user_query.lower() == "quit":
            break
        response = generate_response(user_query)
        print("\n=== 답변 ===")
        print("API 응답:", json.dumps(response, ensure_ascii=False, indent=2))
        print("==========\n")