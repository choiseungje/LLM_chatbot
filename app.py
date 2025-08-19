from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import base64
import json
import PyPDF2
from io import BytesIO
import google.generativeai as genai
from src import DataTree
from datetime import datetime
from typing import Dict, List, Optional
import uuid

# DataTree 인스턴스 생성
data_tree = DataTree.get_data_tree()

# Gemini AI 설정
genai.configure(api_key="AIzaSyC0Vj3AsAbdQezsc6M3_TZE3cLdYcqh0Fw")  # 실제 API 키로 교체해주세요
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

app = FastAPI()

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory=".", html=False), name="static")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 설정
PDF_DIR = "received_pdfs"
ARCHIVE_DIR = "chat_archives"

for directory in [PDF_DIR, ARCHIVE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# 채팅 세션 관리
chat_sessions: Dict[str, Dict] = {}

class ChatArchiveManager:
    """채팅 히스토리 아카이브 관리자"""

    @staticmethod
    def create_session(session_id: str) -> Dict:
        """새로운 채팅 세션 생성"""
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "files_processed": [],
            "concepts_learned": []
        }
        chat_sessions[session_id] = session_data
        return session_data

    @staticmethod
    def add_message(session_id: str, message_type: str, content: str, sender: str = "user"):
        """세션에 메시지 추가"""
        if session_id not in chat_sessions:
            ChatArchiveManager.create_session(session_id)

        message = {
            "timestamp": datetime.now().isoformat(),
            "type": message_type,
            "sender": sender,
            "content": content
        }

        chat_sessions[session_id]["messages"].append(message)

    @staticmethod
    def add_file_processed(session_id: str, filename: str, concepts: List[str]):
        """처리된 파일 정보 추가"""
        if session_id not in chat_sessions:
            ChatArchiveManager.create_session(session_id)

        file_info = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "concepts_extracted": concepts
        }

        chat_sessions[session_id]["files_processed"].append(file_info)
        chat_sessions[session_id]["concepts_learned"].extend(concepts)

    @staticmethod
    def save_session_to_archive(session_id: str) -> str:
        """세션을 아카이브 파일로 저장"""
        if session_id not in chat_sessions:
            return None

        session_data = chat_sessions[session_id]
        session_data["archived_at"] = datetime.now().isoformat()
        session_data["total_messages"] = len(session_data["messages"])
        session_data["total_files"] = len(session_data["files_processed"])
        session_data["unique_concepts"] = len(set(session_data["concepts_learned"]))

        # 파일명 생성 (날짜_시간_세션ID)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_archive_{timestamp}_{session_id[:8]}.json"
        filepath = os.path.join(ARCHIVE_DIR, filename)

        # JSON 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return filepath

    @staticmethod
    def load_archive_files() -> List[Dict]:
        """저장된 아카이브 파일 목록 반환"""
        archives = []

        for filename in os.listdir(ARCHIVE_DIR):
            if filename.endswith('.json') and filename.startswith('chat_archive_'):
                filepath = os.path.join(ARCHIVE_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    archives.append({
                        "filename": filename,
                        "session_id": data.get("session_id"),
                        "created_at": data.get("created_at"),
                        "archived_at": data.get("archived_at"),
                        "total_messages": data.get("total_messages", 0),
                        "total_files": data.get("total_files", 0),
                        "unique_concepts": data.get("unique_concepts", 0)
                    })
                except Exception as e:
                    print(f"아카이브 파일 {filename} 읽기 오류: {e}")

        # 생성 날짜순으로 정렬
        archives.sort(key=lambda x: x["created_at"], reverse=True)
        return archives

    @staticmethod
    def load_archive_content(filename: str) -> Optional[Dict]:
        """특정 아카이브 파일의 전체 내용 반환"""
        filepath = os.path.join(ARCHIVE_DIR, filename)

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"아카이브 파일 로드 오류: {e}")
            return None

@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.get("/api/archives")
async def get_archives():
    """저장된 채팅 아카이브 목록 반환"""
    archives = ChatArchiveManager.load_archive_files()
    return {"archives": archives}

@app.get("/api/archives/{filename}")
async def get_archive_content(filename: str):
    """특정 아카이브 파일의 내용 반환"""
    content = ChatArchiveManager.load_archive_content(filename)

    if content is None:
        return {"error": "Archive file not found"}

    return {"archive": content}

@app.post("/api/sessions/{session_id}/archive")
async def archive_session(session_id: str):
    """현재 세션을 아카이브로 저장"""
    filepath = ChatArchiveManager.save_session_to_archive(session_id)

    if filepath:
        # 세션 데이터 초기화 (선택적)
        # del chat_sessions[session_id]
        return {"success": True, "archive_path": filepath}
    else:
        return {"error": "Session not found"}

def extract_text_from_pdf(pdf_bytes):
    """PDF 바이트에서 텍스트 추출"""
    try:
        pdf_file = BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            text += f"\n[페이지 {page_num + 1}]\n{page_text}\n"

        return text.strip()
    except Exception as e:
        print(f"PDF 텍스트 추출 오류: {e}")
        return None

def extract_concepts_from_text(text):
    """텍스트에서 주요 개념들을 추출"""
    try:
        prompt = f"""
        다음 텍스트에서 주요 개념들을 추출해주세요. 
        각 개념은 한 줄에 하나씩, 간단명료하게 작성해주세요.
        최대 20개의 중요한 개념만 추출해주세요.
        
        텍스트:
        {text[:3000]}  # 텍스트가 너무 길면 처음 3000자만 사용
        
        형식:
        개념1
        개념2
        개념3
        ...
        """

        response = model.generate_content(prompt)
        concepts = [concept.strip() for concept in response.text.split('\n') if concept.strip()]
        return concepts[:20]  # 최대 20개로 제한
    except Exception as e:
        print(f"개념 추출 오류: {e}")
        return []

def generate_answer_with_context(question, context_nodes, session_id=None, chat_history_limit=5):
    """컨텍스트와 채팅 히스토리를 바탕으로 질문에 답변 생성"""
    try:
        # 관련 개념들
        context_text = "\n".join([f"- {node.data}" for node in context_nodes])

        # 이전 대화 히스토리 가져오기
        chat_history = ""
        if session_id and session_id in chat_sessions:
            recent_messages = chat_sessions[session_id]["messages"][-chat_history_limit*2:]  # 최근 대화만
            history_parts = []

            for msg in recent_messages:
                if msg["sender"] == "user" and msg["type"] == "text":
                    history_parts.append(f"사용자: {msg['content']}")
                elif msg["sender"] == "bot" and msg["type"] == "message":
                    history_parts.append(f"봇: {msg['content']}")

            if history_parts:
                chat_history = "\n".join(history_parts[-10:])  # 최근 10개 메시지만

        prompt = f"""
        다음 정보를 바탕으로 질문에 답변해주세요:
        
        === 학습된 개념들 ===
        {context_text}
        
        === 이전 대화 내용 ===
        {chat_history}
        
        === 현재 질문 ===
        {question}
        
        답변 시 고려사항:
        1. 이전 대화의 맥락을 참고하여 일관성 있게 답변하세요
        2. 학습된 개념들을 활용하여 구체적으로 설명하세요
        3. 사용자가 이전에 물어본 내용과 연관된다면 언급해주세요
        4. 친절하고 자세하게 설명해주세요
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"답변 생성 오류: {e}")
        return "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다."

def generate_general_answer_with_history(question, session_id=None):
    """일반적인 질문에 대해 채팅 히스토리를 참고하여 답변 생성"""
    try:
        # 이전 대화 히스토리 가져오기
        chat_history = ""
        if session_id and session_id in chat_sessions:
            recent_messages = chat_sessions[session_id]["messages"][-10:]  # 최근 10개 메시지
            history_parts = []

            for msg in recent_messages:
                if msg["sender"] == "user" and msg["type"] == "text":
                    history_parts.append(f"사용자: {msg['content']}")
                elif msg["sender"] == "bot" and msg["type"] == "message":
                    history_parts.append(f"봇: {msg['content'][:100]}...")  # 봇 답변은 100자로 제한

            if history_parts:
                chat_history = "\n".join(history_parts)

        if chat_history:
            prompt = f"""
            이전 대화 내용을 참고하여 질문에 답변해주세요:
            
            === 이전 대화 ===
            {chat_history}
            
            === 현재 질문 ===
            {question}
            
            이전 대화의 맥락을 고려하여 일관성 있고 친절하게 답변해주세요.
            """
        else:
            prompt = f"다음 질문에 친절하게 답변해주세요: {question}"

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"답변 생성 오류: {e}")
        return "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다."

async def send_message(websocket: WebSocket, message_type: str, content: str):
    """WebSocket으로 메시지 전송"""
    await websocket.send_text(json.dumps({
        "type": message_type,
        "content": content
    }))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 세션 ID 생성
    session_id = str(uuid.uuid4())
    print(f"새로운 세션 시작: {session_id}")

    # 세션 생성
    ChatArchiveManager.create_session(session_id)

    await send_message(websocket, "session_info", json.dumps({"session_id": session_id}))
    await send_message(websocket, "message", "안녕하세요! 챗봇입니다. 질문을 하시거나 PDF 파일을 업로드해주세요.")

    # 시스템 메시지 기록
    ChatArchiveManager.add_message(session_id, "message",
                                   "안녕하세요! 챗봇입니다. 질문을 하시거나 PDF 파일을 업로드해주세요.", "bot")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data['type'] == 'text':
                question = message_data['content']
                print(f"사용자 질문: {question}")

                # 사용자 메시지 기록
                ChatArchiveManager.add_message(session_id, "text", question, "user")

                # DataTree에서 관련 노드 검색
                related_nodes = []
                for node in data_tree.get_nodes():
                    if any(word in node.data.lower() for word in question.lower().split()):
                        related_nodes.append(node)

                # 항상 이전 대화 히스토리를 포함하여 답변 생성
                try:
                    if related_nodes:
                        # 관련 개념이 있으면 컨텍스트와 히스토리를 바탕으로 답변
                        answer = generate_answer_with_context(question, related_nodes, session_id)
                    else:
                        # 관련 개념이 없어도 히스토리를 참고한 답변
                        answer = generate_general_answer_with_history(question, session_id)

                    await send_message(websocket, "message", answer)
                    ChatArchiveManager.add_message(session_id, "message", answer, "bot")
                except Exception as e:
                    print(f"답변 생성 상세 오류: {e}")
                    error_msg = "답변 생성 중 오류가 발생했습니다."
                    await send_message(websocket, "error", error_msg)
                    ChatArchiveManager.add_message(session_id, "error", error_msg, "bot")

            elif message_data['type'] == 'file':
                filename = message_data['filename']
                file_content = message_data['content']

                try:
                    # Base64 디코딩
                    file_bytes = base64.b64decode(file_content)

                    # 파일 저장
                    file_path = os.path.join(PDF_DIR, filename)
                    with open(file_path, "wb") as f:
                        f.write(file_bytes)

                    print(f"파일 저장됨: {filename}")
                    upload_msg = f"📎 {filename} 파일이 업로드되었습니다. 분석 중..."
                    await send_message(websocket, "file_processed", upload_msg)
                    ChatArchiveManager.add_message(session_id, "file_upload", filename, "user")

                    # PDF에서 텍스트 추출
                    extracted_text = extract_text_from_pdf(file_bytes)

                    if extracted_text:
                        print(f"텍스트 추출 완료: {len(extracted_text)} 글자")

                        # 텍스트에서 개념 추출
                        concepts = extract_concepts_from_text(extracted_text)
                        print(f"추출된 개념 수: {len(concepts)}")

                        # DataTree에 개념들 추가
                        added_concepts = []
                        for concept in concepts:
                            if concept and len(concept.strip()) > 0:
                                # 중복 체크
                                existing_node = data_tree.get_node_by_data(concept)
                                if not existing_node:
                                    node = DataTree.Node(concept)
                                    data_tree.add_node(node)
                                    added_concepts.append(concept)

                        # 파일 처리 결과 기록
                        ChatArchiveManager.add_file_processed(session_id, filename, added_concepts)

                        if added_concepts:
                            concepts_text = "\n".join([f"• {concept}" for concept in added_concepts[:10]])  # 처음 10개만 표시
                            remaining = len(added_concepts) - 10
                            if remaining > 0:
                                concepts_text += f"\n... 외 {remaining}개의 개념"

                            success_msg = f"✅ PDF 분석 완료! 다음 개념들을 학습했습니다:\n\n{concepts_text}\n\n이제 관련 질문을 해보세요!"
                            await send_message(websocket, "file_processed", success_msg)
                            ChatArchiveManager.add_message(session_id, "file_processed", success_msg, "bot")
                        else:
                            no_concept_msg = "PDF 파일을 분석했지만 새로운 개념을 추출하지 못했습니다."
                            await send_message(websocket, "file_processed", no_concept_msg)
                            ChatArchiveManager.add_message(session_id, "file_processed", no_concept_msg, "bot")
                    else:
                        error_msg = "PDF에서 텍스트를 추출할 수 없습니다."
                        await send_message(websocket, "error", error_msg)
                        ChatArchiveManager.add_message(session_id, "error", error_msg, "bot")

                except Exception as e:
                    print(f"파일 처리 오류: {e}")
                    error_msg = f"파일 처리 중 오류가 발생했습니다: {str(e)}"
                    await send_message(websocket, "error", error_msg)
                    ChatArchiveManager.add_message(session_id, "error", error_msg, "bot")

            elif message_data['type'] == 'archive_session':
                # 세션 아카이브 요청
                filepath = ChatArchiveManager.save_session_to_archive(session_id)
                if filepath:
                    archive_msg = f"✅ 채팅 히스토리가 저장되었습니다: {os.path.basename(filepath)}"
                    await send_message(websocket, "message", archive_msg)
                    ChatArchiveManager.add_message(session_id, "message", archive_msg, "bot")
                else:
                    error_msg = "세션 저장에 실패했습니다."
                    await send_message(websocket, "error", error_msg)

    except WebSocketDisconnect:
        print(f"클라이언트 연결 해제 - 세션: {session_id}")
        # 연결 해제 시 자동으로 세션 아카이브 저장
        if session_id in chat_sessions:
            ChatArchiveManager.save_session_to_archive(session_id)
            print(f"세션 {session_id} 자동 저장 완료")
    except Exception as e:
        print(f"WebSocket 오류: {e}")
        try:
            await send_message(websocket, "error", "연결 오류가 발생했습니다.")
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    print("채팅 히스토리 아카이브 기능이 포함된 챗봇 서버 시작...")
    print("브라우저에서 http://127.0.0.1:8000 에 접속하세요.")
    print(f"채팅 아카이브는 {ARCHIVE_DIR} 폴더에 저장됩니다.")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")