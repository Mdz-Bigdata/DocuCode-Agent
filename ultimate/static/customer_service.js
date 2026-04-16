function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function formatMessageWithLineBreaks(text) {
    if (!text) return text;
    
    let formatted = text;
    
    formatted = formatted.replace(/(\d+[.、．]\s*)/g, '\n$1');
    formatted = formatted.replace(/([（(]\d+[)）]\s*)/g, '\n$1');
    formatted = formatted.replace(/([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*)/g, '\n$1');
    formatted = formatted.replace(/^[ \t]*\n+/, '');
    formatted = formatted.replace(/\n{3,}/g, '\n\n');
    
    return formatted;
}

function initCustomerService() {
    const csMessages = document.getElementById('csMessages');
    const csInput = document.getElementById('csInput');
    const csSendBtn = document.getElementById('csSendBtn');
    const faqItems = document.querySelectorAll('.faq-item');
    const emojiBtn = document.querySelector('.tool-btn[title="表情"]');
    const imageBtn = document.querySelector('.tool-btn[title="图片"]');
    const attachmentBtn = document.querySelector('.tool-btn[title="附件"]');
    const modelSelector = document.getElementById('modelSelector');
    const clearFaqBtn = document.getElementById('clearFaqBtn');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const faqList = document.getElementById('faqList');
    const historyList = document.getElementById('historyList');
    
    const imageInput = document.createElement('input');
    imageInput.type = 'file';
    imageInput.accept = 'image/*';
    imageInput.style.display = 'none';
    
    const attachmentInput = document.createElement('input');
    attachmentInput.type = 'file';
    attachmentInput.accept = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt';
    attachmentInput.style.display = 'none';
    
    document.body.appendChild(imageInput);
    document.body.appendChild(attachmentInput);
    
    const EMOJIS = ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '🥸', '😎', '🤓', '🧐', '👍', '👎', '👏', '🙌', '🤝', '❤️', '💔', '🔥', '✨', '🎉', '🎊', '💯'];
    
    let emojiPicker = null;
    
    function createEmojiPicker() {
        if (emojiPicker) return emojiPicker;
        
        emojiPicker = document.createElement('div');
        emojiPicker.className = 'emoji-picker';
        emojiPicker.style.cssText = `
            position: absolute;
            bottom: 100%;
            left: 0;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            display: none;
            max-width: 320px;
        `;
        
        const emojiGrid = document.createElement('div');
        emojiGrid.style.cssText = `
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            gap: 8px;
        `;
        
        EMOJIS.forEach(emoji => {
            const emojiBtn = document.createElement('button');
            emojiBtn.textContent = emoji;
            emojiBtn.style.cssText = `
                background: none;
                border: none;
                font-size: 20px;
                padding: 4px;
                cursor: pointer;
                border-radius: 4px;
                transition: background 0.2s;
            `;
            emojiBtn.onmouseenter = () => emojiBtn.style.background = '#f0f0f0';
            emojiBtn.onmouseleave = () => emojiBtn.style.background = 'transparent';
            emojiBtn.onclick = () => {
                csInput.value += emoji;
                csInput.focus();
                emojiPicker.style.display = 'none';
            };
            emojiGrid.appendChild(emojiBtn);
        });
        
        emojiPicker.appendChild(emojiGrid);
        return emojiPicker;
    }
    
    let ws = null;
    let currentAssistantMessage = null;
    
    function connectWebSocket() {
        if (ws) return;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/chat`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('Customer service WebSocket connected');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        ws.onclose = () => {
            console.log('Customer service WebSocket closed');
            ws = null;
        };
    }
    
    function handleWebSocketMessage(data) {
        if (data.type === 'start') {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'cs-message assistant';
            messageDiv.innerHTML = `
                <div class="cs-message-avatar"><i class="fas fa-headset"></i></div>
                <div class="cs-message-content">
                    <div class="cs-message-bubble"></div>
                    <div class="cs-message-time">刚刚</div>
                </div>
            `;
            csMessages.appendChild(messageDiv);
            currentAssistantMessage = messageDiv.querySelector('.cs-message-bubble');
            csMessages.scrollTop = csMessages.scrollHeight;
        } else if (data.type === 'stream') {
            if (currentAssistantMessage) {
                let content = (currentAssistantMessage.dataset.fullText || '') + data.content;
                currentAssistantMessage.dataset.fullText = content;
                
                let formatted = formatMessageWithLineBreaks(content);
                currentAssistantMessage.textContent = formatted;
                currentAssistantMessage.style.whiteSpace = 'pre-wrap';
                currentAssistantMessage.style.wordBreak = 'break-word';
                
                csMessages.scrollTop = csMessages.scrollHeight;
            }
        } else if (data.type === 'end') {
            currentAssistantMessage = null;
        } else if (data.type === 'error') {
            showToast(data.message, 'error');
        }
    }
    
    function sendMessage(message, attachments = []) {
        if (!message.trim() && attachments.length === 0) return;
        
        const userDiv = document.createElement('div');
        userDiv.className = 'cs-message user';
        
        let attachmentsHtml = '';
        attachments.forEach(att => {
            if (att.type === 'image') {
                attachmentsHtml += `
                    <div class="message-attachment" style="margin-top: 8px;">
                        <img src="${att.url}" alt="${att.name}" style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                    </div>
                `;
            } else {
                attachmentsHtml += `
                    <div class="message-attachment" style="margin-top: 8px; display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                        <i class="fas fa-file"></i>
                        <span>${att.name}</span>
                    </div>
                `;
            }
        });
        
        userDiv.innerHTML = `
            <div class="cs-message-avatar"><i class="fas fa-user"></i></div>
            <div class="cs-message-content">
                <div class="cs-message-bubble">${message}${attachmentsHtml}</div>
                <div class="cs-message-time">刚刚</div>
            </div>
        `;
        csMessages.appendChild(userDiv);
        
        csInput.value = '';
        csInput.style.height = 'auto';
        csMessages.scrollTop = csMessages.scrollHeight;
        
        connectWebSocket();
        
        const currentModel = modelSelector ? modelSelector.value : 'local';
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                message: message,
                agent_type: 'customer_service',
                model_type: currentModel,
                history: []
            }));
        }
    }
    
    if (csSendBtn) {
        csSendBtn.addEventListener('click', () => {
            sendMessage(csInput.value);
        });
    }
    
    if (csInput) {
        csInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(csInput.value);
            }
        });
        
        csInput.addEventListener('input', () => {
            csInput.style.height = 'auto';
            csInput.style.height = Math.min(csInput.scrollHeight, 150) + 'px';
        });
    }
    
    if (emojiBtn) {
        emojiBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const picker = createEmojiPicker();
            if (!picker.parentNode) {
                emojiBtn.parentNode.style.position = 'relative';
                emojiBtn.parentNode.appendChild(picker);
            }
            picker.style.display = picker.style.display === 'none' ? 'block' : 'none';
        });
        
        document.addEventListener('click', () => {
            if (emojiPicker) {
                emojiPicker.style.display = 'none';
            }
        });
    }
    
    if (imageBtn) {
        imageBtn.addEventListener('click', () => {
            imageInput.click();
        });
        
        imageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    sendMessage('[图片]', [{
                        type: 'image',
                        url: event.target.result,
                        name: file.name
                    }]);
                };
                reader.readAsDataURL(file);
            }
            imageInput.value = '';
        });
    }
    
    if (attachmentBtn) {
        attachmentBtn.addEventListener('click', () => {
            attachmentInput.click();
        });
        
        attachmentInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                sendMessage('[附件]', [{
                    type: 'file',
                    name: file.name
                }]);
            }
            attachmentInput.value = '';
        });
    }
    
    if (modelSelector) {
        modelSelector.addEventListener('change', async (e) => {
            const selectedModel = e.target.value;
            try {
                const response = await fetch('/api/models/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_type: selectedModel })
                });
                if (response.ok) {
                    showToast(`已切换到 ${selectedModel === 'local' ? '本地 Qwen' : '阿里云 DashScope'} 模型`, 'success');
                }
            } catch (err) {
                console.error('切换模型失败:', err);
                showToast('切换模型失败', 'error');
            }
        });
    }
    
    faqItems.forEach(item => {
        item.addEventListener('click', () => {
            const question = item.dataset.question;
            sendMessage(question);
        });
    });
    
    if (clearFaqBtn && faqList) {
        clearFaqBtn.addEventListener('click', () => {
            faqList.innerHTML = '';
            showToast('常见问题已清除', 'success');
        });
    }
    
    if (clearHistoryBtn && historyList) {
        clearHistoryBtn.addEventListener('click', () => {
            historyList.innerHTML = '';
            showToast('历史对话已清除', 'success');
        });
    }
    
    connectWebSocket();
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('csMessages')) {
        initCustomerService();
    }
});
