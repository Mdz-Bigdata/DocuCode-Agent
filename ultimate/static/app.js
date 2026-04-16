function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function initDashboard() {
    const quickChatBtn = document.getElementById('quickChatBtn');
    const quickChatModal = document.getElementById('quickChatModal');
    const closeQuickChatBtn = document.getElementById('closeQuickChatBtn');
    const quickChatSendBtn = document.getElementById('quickChatSendBtn');
    const quickChatInput = document.getElementById('quickChatInput');
    const quickChatMessages = document.getElementById('quickChatMessages');
    
    let ws = null;
    
    function connectWebSocket() {
        if (ws) return;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/chat`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('WebSocket connected');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        ws.onclose = () => {
            console.log('WebSocket closed');
            ws = null;
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            showToast('连接错误', 'error');
        };
    }
    
    let currentAssistantMessage = null;
    
    function handleWebSocketMessage(data) {
        if (data.type === 'start') {
            const welcomeDiv = quickChatMessages.querySelector('.quick-chat-welcome');
            if (welcomeDiv) welcomeDiv.style.display = 'none';
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'quick-chat-message assistant';
            messageDiv.innerHTML = `
                <div class="quick-chat-bubble"></div>
            `;
            quickChatMessages.appendChild(messageDiv);
            currentAssistantMessage = messageDiv.querySelector('.quick-chat-bubble');
            quickChatMessages.scrollTop = quickChatMessages.scrollHeight;
        } else if (data.type === 'stream') {
            if (currentAssistantMessage) {
                currentAssistantMessage.textContent += data.content;
                quickChatMessages.scrollTop = quickChatMessages.scrollHeight;
            }
        } else if (data.type === 'end') {
            currentAssistantMessage = null;
        } else if (data.type === 'error') {
            showToast(data.message, 'error');
        }
    }
    
    function sendQuickMessage() {
        const message = quickChatInput.value.trim();
        if (!message) return;
        
        const welcomeDiv = quickChatMessages.querySelector('.quick-chat-welcome');
        if (welcomeDiv) welcomeDiv.style.display = 'none';
        
        const userDiv = document.createElement('div');
        userDiv.className = 'quick-chat-message user';
        userDiv.innerHTML = `<div class="quick-chat-bubble">${message}</div>`;
        quickChatMessages.appendChild(userDiv);
        
        quickChatInput.value = '';
        quickChatMessages.scrollTop = quickChatMessages.scrollHeight;
        
        connectWebSocket();
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                message: message,
                agent_type: 'default',
                history: []
            }));
        }
    }
    
    if (quickChatBtn) {
        quickChatBtn.addEventListener('click', () => {
            quickChatModal.classList.add('active');
            connectWebSocket();
        });
    }
    
    if (closeQuickChatBtn) {
        closeQuickChatBtn.addEventListener('click', () => {
            quickChatModal.classList.remove('active');
            if (ws) {
                ws.close();
                ws = null;
            }
        });
    }
    
    if (quickChatSendBtn) {
        quickChatSendBtn.addEventListener('click', sendQuickMessage);
    }
    
    if (quickChatInput) {
        quickChatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendQuickMessage();
            }
        });
    }
    
    loadDocCount();
}

async function loadDocCount() {
    try {
        const response = await fetch('/api/rag/documents');
        const data = await response.json();
        const docCountEl = document.getElementById('docCount');
        if (docCountEl && data.documents) {
            docCountEl.textContent = data.documents.length;
        }
    } catch (error) {
        console.error('Failed to load document count:', error);
    }
}

function deleteActivity(id) {
    const activityItem = document.querySelector(`.activity-item[data-id="${id}"]`);
    if (activityItem) {
        activityItem.style.transform = 'translateX(100%)';
        activityItem.style.opacity = '0';
        activityItem.style.transition = 'all 0.3s ease';
        setTimeout(() => {
            activityItem.remove();
            showToast('记录已删除', 'success');
        }, 300);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('quickChatBtn')) {
        initDashboard();
    }
});
