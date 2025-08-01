let ws = null;
const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws";

document.addEventListener("DOMContentLoaded", () => {
    const form     = document.getElementById("form");
    const textarea = document.getElementById("message_text");

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = textarea.value.trim();
        if (!text) return;

        // WebSocket 연결이 아직 안 되어 있으면 열기
        if (!ws) {
            ws = new WebSocket(WEBSOCKET_URL);
            ws.addEventListener("open",  () => sendText(text));
            ws.addEventListener("message", onMessage);
            ws.addEventListener("close",   onClose);
            ws.addEventListener("error",   (err) => console.error("WebSocket error:", err));
        } else {
            // 이미 연결되어 있으면 바로 전송
            sendText(text);
        }

        // 사용자 메시지 화면에 추가
        updateScreen(text, true);
        textarea.value = "";
    });

    // Enter 단일키로도 전송
    textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.requestSubmit();
        }
    });
});

function sendText(text) {
    ws.send(JSON.stringify({ type: "text", payload: text }));
}

function onMessage(event) {
    const msg = event.data;
    if (msg === "<EOS>") {
        ws.close();
        return;
    }
    updateScreen(msg, false);
}

function onClose() {
    ws = null;
}

function updateScreen(text, isUser) {
    const list = document.getElementById("messages");
    if (isUser) {
        const li = document.createElement("li");
        li.classList.add("message", "message-user");
        li.textContent = text;
        list.appendChild(li);

        // 서버 답변 placeholder
        const placeholder = document.createElement("li");
        placeholder.classList.add("message", "message-server", "d-none");
        placeholder.innerHTML = '<i class="fas fa-robot icon"></i>';
        list.appendChild(placeholder);
    } else {
        const last = list.lastElementChild;
        if (last && last.classList.contains("d-none")) {
            last.classList.remove("d-none");
            last.innerHTML += text;
        }
    }
    list.scrollTop = list.scrollHeight;
}
