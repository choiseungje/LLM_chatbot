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

# DataTree 인스턴스 생성
data_tree = DataTree.get_data_tree()

# Gemini AI 설정
genai.configure(api_key="API_KEY")  # 실제 API 키로 교체해주세요
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

# PDF 저장 디렉토리
PDF_DIR = "received_pdfs"
if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

@app.get("/")
async def read_root():
    return FileResponse("index.html")

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

def generate_answer_with_context(question, context_nodes):
    """컨텍스트를 바탕으로 질문에 답변 생성"""
    try:
        context_text = "\n".join([f"- {node.data}" for node in context_nodes])

        prompt = f"""
        다음 개념들을 바탕으로 질문에 답변해주세요:
        
        관련 개념들:
        {context_text}
        
        질문: {question}
        
        답변은 친절하고 자세하게 설명해주세요.
        """

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
    await send_message(websocket, "message", "안녕하세요! 챗봇입니다. 질문을 하시거나 PDF 파일을 업로드해주세요.")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data['type'] == 'text':
                question = message_data['content']
                print(f"사용자 질문: {question}")

                # DataTree에서 관련 노드 검색
                related_nodes = []
                for node in data_tree.get_nodes():
                    if any(word in node.data.lower() for word in question.lower().split()):
                        related_nodes.append(node)

                if related_nodes:
                    # 관련 개념이 있으면 컨텍스트를 바탕으로 답변
                    answer = generate_answer_with_context(question, related_nodes)
                    await send_message(websocket, "message", answer)
                else:
                    # 관련 개념이 없으면 일반적인 답변
                    try:
                        response = model.generate_content(f"다음 질문에 친절하게 답변해주세요: {question}")
                        await send_message(websocket, "message", response.text)
                    except Exception as e:
                        await send_message(websocket, "error", "답변 생성 중 오류가 발생했습니다.")

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
                    await send_message(websocket, "file_processed", f"📎 {filename} 파일이 업로드되었습니다. 분석 중...")

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

                        if added_concepts:
                            concepts_text = "\n".join([f"• {concept}" for concept in added_concepts[:10]])  # 처음 10개만 표시
                            remaining = len(added_concepts) - 10
                            if remaining > 0:
                                concepts_text += f"\n... 외 {remaining}개의 개념"

                            await send_message(websocket, "file_processed",
                                               f"✅ PDF 분석 완료! 다음 개념들을 학습했습니다:\n\n{concepts_text}\n\n이제 관련 질문을 해보세요!")
                        else:
                            await send_message(websocket, "file_processed",
                                               "PDF 파일을 분석했지만 새로운 개념을 추출하지 못했습니다.")
                    else:
                        await send_message(websocket, "error", "PDF에서 텍스트를 추출할 수 없습니다.")

                except Exception as e:
                    print(f"파일 처리 오류: {e}")
                    await send_message(websocket, "error", f"파일 처리 중 오류가 발생했습니다: {str(e)}")

    except WebSocketDisconnect:
        print("클라이언트 연결 해제")
    except Exception as e:
        print(f"WebSocket 오류: {e}")
        try:
            await send_message(websocket, "error", "연결 오류가 발생했습니다.")
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    print("챗봇 서버 시작...")
    print("브라우저에서 http://127.0.0.1:8000 에 접속하세요.")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")