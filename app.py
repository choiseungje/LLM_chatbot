from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import base64

from src import DataTree
from fastapi.staticfiles import StaticFiles

data_tree = DataTree.get_data_tree()

app = FastAPI()
app.mount("/static", StaticFiles(directory=".", html=False), name="static")

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

PDF_DIR = "received_pdfs"
if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

@app.get("/")
async def read_root():
    return FileResponse("index.html")  # index.html을 루트 요청 시 반환

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'text':
                print(f"Message from client: {data['payload']}")

                #테스트로 넣은 임시코드
                data_tree.add_node(DataTree.Node(data['payload']))
                print(f"Current DataTree: {data_tree}")
                await websocket.send_text(f"Server: {data['payload']}")
            elif data['type'] == 'file':
                file_data = data['payload']
                file_name = data['filename']
                file_bytes = base64.b64decode(file_data)

                file_path = os.path.join(PDF_DIR, file_name)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)

                #테스트용 임시코드
                print(f"File '{file_name}' received and saved.")
                await websocket.send_text(f"File '{file_name}' received.")

    except WebSocketDisconnect:
        print("Client disconnected")


def when_get_file():
    concept_list = []
    #concept 갖고 오는 거 만드세요
    for concept in concept_list:
        node = DataTree.Node(concept)
        data_tree.add_node(node)

def when_get_question(q:str)->str:
    node = data_tree.get_node_by_data(q)
    #토큰 사용부분
    return 'question'

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")