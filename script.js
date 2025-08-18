const socket = new WebSocket('ws://localhost:8000/ws');
const messagesElement = document.getElementById('messages');
const form = document.getElementById('form');
const messageInput = document.getElementById('message_text');
const uploadBtn = document.getElementById('upload_btn');
const pdfInput = document.getElementById('pdf_input');

// WebSocket 연결 상태 확인
socket.onopen = function(event) {
    console.log('WebSocket 연결이 열렸습니다.');
    addMessage('시스템', '챗봇에 연결되었습니다. 메시지를 입력하거나 PDF 파일을 업로드해주세요.', 'message-server');
};

socket.onclose = function(event) {
    console.log('WebSocket 연결이 닫혔습니다.');
    addMessage('시스템', '연결이 끊어졌습니다. 페이지를 새로고침해주세요.', 'message-server');
};

socket.onerror = function(error) {
    console.error('WebSocket 오류:', error);
    addMessage('시스템', '연결 오류가 발생했습니다.', 'message-server');
};

// 서버로부터 메시지 수신
socket.onmessage = function(event) {
    const data = JSON.parse(event.data);

    if (data.type === 'message') {
        addMessage('봇', data.content, 'message-server');
    } else if (data.type === 'file_processed') {
        addMessage('시스템', data.content, 'message-server');
    } else if (data.type === 'error') {
        addMessage('오류', data.content, 'message-server');
    }
};

// 메시지를 화면에 추가하는 함수
function addMessage(sender, content, className) {
    const li = document.createElement('li');
    li.className = className;

    if (className === 'message-server') {
        li.innerHTML = `<i class="fas fa-robot icon"></i>${content}`;
    } else {
        li.textContent = content;
    }

    messagesElement.appendChild(li);
    messagesElement.scrollTop = messagesElement.scrollHeight;
}

// 폼 제출 이벤트 (메시지 전송)
form.addEventListener('submit', function(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (message) {
        // 사용자 메시지를 화면에 표시
        addMessage('나', message, 'message-user');

        // 서버로 메시지 전송
        socket.send(JSON.stringify({
            type: 'text',
            content: message
        }));

        messageInput.value = '';
        adjustTextareaHeight();
    }
});

// PDF 업로드 버튼 클릭
uploadBtn.addEventListener('click', function() {
    pdfInput.click();
});

// PDF 파일 선택 시
pdfInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
        uploadPDF(file);
    } else {
        addMessage('오류', 'PDF 파일만 업로드 가능합니다.', 'message-server');
    }
    // 파일 입력 초기화
    pdfInput.value = '';
});

// PDF 파일 업로드 함수
function uploadPDF(file) {
    addMessage('나', `📎 ${file.name} 업로드 중...`, 'message-user');

    const reader = new FileReader();
    reader.onload = function(e) {
        const base64Data = btoa(new Uint8Array(e.target.result).reduce((data, byte) => data + String.fromCharCode(byte), ''));

        // 서버로 파일 전송
        socket.send(JSON.stringify({
            type: 'file',
            filename: file.name,
            content: base64Data
        }));
    };

    reader.onerror = function() {
        addMessage('오류', '파일 읽기에 실패했습니다.', 'message-server');
    };

    reader.readAsArrayBuffer(file);
}

// 텍스트 영역 높이 자동 조절
function adjustTextareaHeight() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 100) + 'px';
}

// 텍스트 입력 시 높이 조절
messageInput.addEventListener('input', adjustTextareaHeight);

// 엔터키로 전송, Shift+엔터로 줄바꿈
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event('submit'));
    }
});

// 드래그 앤 드롭 기능
document.addEventListener('dragover', function(e) {
    e.preventDefault();
    document.body.style.backgroundColor = '#f0f8ff';
});

document.addEventListener('dragleave', function(e) {
    if (e.clientX === 0 && e.clientY === 0) {
        document.body.style.backgroundColor = '#ffffff';
    }
});

document.addEventListener('drop', function(e) {
    e.preventDefault();
    document.body.style.backgroundColor = '#ffffff';

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf') {
            uploadPDF(file);
        } else {
            addMessage('오류', 'PDF 파일만 업로드 가능합니다.', 'message-server');
        }
    }
});

// 초기 텍스트 영역 높이 설정
adjustTextareaHeight();