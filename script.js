let ws = null;
const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws";

document.addEventListener("DOMContentLoaded", () => {
    const form      = document.getElementById("form");
    const textarea  = document.getElementById("message_text");
    const uploadBtn = document.getElementById("upload_btn");
    const pdfInput  = document.getElementById("pdf_input");

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = textarea.value.trim();
        if (!text) return;

        ensureWS(() => sendText(text));

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

    // 업로드 버튼 → 파일 선택
    uploadBtn.addEventListener("click", () => {
        pdfInput.value = ""; // 같은 파일 재선택 허용
        pdfInput.click();
    });

    // 파일 선택 시 전송
    pdfInput.addEventListener("change", async () => {
        const file = pdfInput.files && pdfInput.files[0];
        if (!file) return;

        // 간단한 유효성 검사
        if (file.type !== "application/pdf") {
            alert("PDF 파일만 업로드할 수 있습니다.");
            return;
        }
        // (선택) 용량 제한 예시: 10MB
        const MAX_BYTES = 10 * 1024 * 1024;
        if (file.size > MAX_BYTES) {
            alert("파일이 너무 큽니다. 10MB 이하의 PDF만 업로드해 주세요.");
            return;
        }

        // 화면에 업로드 시작 메시지
        updateScreen(`'${file.name}' 업로드를 시작합니다...`, true);

        try {
            const base64 = await fileToBase64(file);
            ensureWS(() => sendFile(file.name, base64));
        } catch (err) {
            console.error(err);
            updateServerText(`파일 인코딩 중 오류가 발생했습니다: ${String(err)}`);
        }
    });
});

function ensureWS(cb) {
    if (!ws) {
        ws = new WebSocket(WEBSOCKET_URL);
        ws.addEventListener("open",  () => cb && cb());
        ws.addEventListener("message", onMessage);
        ws.addEventListener("close", onClose);
        ws.addEventListener("error", (err) => console.error("WebSocket error:", err));
    } else {
        cb && cb();
    }
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        // readAsDataURL → "data:application/pdf;base64,..." 형식
        reader.readAsDataURL(file);
        reader.onload = () => {
            try {
                const result = String(reader.result);
                const base64 = result.split(",")[1]; // 헤더 제거
                resolve(base64);
            } catch (e) {
                reject(e);
            }
        };
        reader.onerror = (e) => reject(e);
    });
}

function sendText(text) {
    ws.send(JSON.stringify({ type: "text", payload: text }));
}

function sendFile(filename, base64Data) {
    ws.send(JSON.stringify({
        type: "file",
        filename: filename,
        payload: base64Data
    }));
    // 서버 메시지 자리표시자 추가
    addServerPlaceholder();
    // 사용자 업로드 안내 추가(선택)
    updateServerText(`'${filename}' 전송 중...`);
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
        addServerPlaceholder();
    } else {
        const last = list.lastElementChild;
        if (last && last.classList.contains("d-none")) {
            last.classList.remove("d-none");
            last.innerHTML += text;
        } else {
            // 혹시 placeholder가 없으면 새로 추가
            const li = document.createElement("li");
            li.classList.add("message", "message-server");
            li.innerHTML = '<i class="fas fa-robot icon"></i>' + text;
            list.appendChild(li);
        }
    }
    list.scrollTop = list.scrollHeight;
}

function addServerPlaceholder() {
    const list = document.getElementById("messages");
    const placeholder = document.createElement("li");
    placeholder.classList.add("message", "message-server", "d-none");
    placeholder.innerHTML = '<i class="fas fa-robot icon"></i>';
    list.appendChild(placeholder);
}

function updateServerText(text) {
    const list = document.getElementById("messages");
    const last = list.lastElementChild;
    if (last && last.classList.contains("d-none")) {
        last.classList.remove("d-none");
        last.innerHTML += text;
    } else {
        const li = document.createElement("li");
        li.classList.add("message", "message-server");
        li.innerHTML = '<i class="fas fa-robot icon"></i>' + text;
        list.appendChild(li);
    }
    list.scrollTop = list.scrollHeight;
}

