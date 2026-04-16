function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

let currentDocuments = [];

function initRAG() {
    const uploadDocBtn = document.getElementById('uploadDocBtn');
    const configDocBtn = document.getElementById('configDocBtn');
    const emptyUploadBtn = document.getElementById('emptyUploadBtn');
    const uploadModal = document.getElementById('uploadModal');
    const configModal = document.getElementById('configModal');
    const closeUploadModal = document.getElementById('closeUploadModal');
    const closeConfigModal = document.getElementById('closeConfigModal');
    const cancelUploadBtn = document.getElementById('cancelUploadBtn');
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const confirmUploadBtn = document.getElementById('confirmUploadBtn');
    const fileList = document.getElementById('fileList');
    const uploadPreview = document.getElementById('uploadPreview');
    const documentsGrid = document.getElementById('documentsGrid');
    const refreshDocsBtn = document.getElementById('refreshDocsBtn');
    const ragSearchBtn = document.getElementById('ragSearchBtn');
    const ragSearchInput = document.getElementById('ragSearchInput');
    const ragSearchResults = document.getElementById('ragSearchResults');
    const resultsList = document.getElementById('resultsList');
    const docDetailModal = document.getElementById('docDetailModal');
    const closeDocDetailModal = document.getElementById('closeDocDetailModal');
    const closeDocDetailBtn2 = document.getElementById('closeDocDetailBtn2');
    const deleteDocBtn = document.getElementById('deleteDocBtn');
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    const resetConfigBtn = document.getElementById('resetConfigBtn');
    const toggleChatBtn = document.getElementById('toggleChatBtn');
    const chatSection = document.getElementById('chatSection');
    const documentsSection = document.getElementById('documentsSection');
    const chatModeBtns = document.querySelectorAll('.chat-mode-btn');
    const docSelector = document.getElementById('docSelector');
    const chatDocSelect = document.getElementById('chatDocSelect');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const startChatWithDocBtn = document.getElementById('startChatWithDocBtn');
    const chatSourceLabel = document.getElementById('chatSourceLabel');
    
    let selectedFiles = [];
    let selectedDocId = null;
    let chatHistory = [];
    let currentChatMode = 'knowledge_base';
    let currentChatDocId = null;
    let sourceDocuments = [];
    
    uploadDocBtn?.addEventListener('click', () => uploadModal.classList.add('active'));
    configDocBtn?.addEventListener('click', () => {
        loadConfig();
        configModal.classList.add('active');
    });
    emptyUploadBtn?.addEventListener('click', () => uploadModal.classList.add('active'));
    
    closeUploadModal?.addEventListener('click', () => {
        uploadModal.classList.remove('active');
        resetUpload();
    });
    
    closeConfigModal?.addEventListener('click', () => {
        configModal.classList.remove('active');
    });
    
    cancelUploadBtn?.addEventListener('click', () => {
        uploadModal.classList.remove('active');
        resetUpload();
    });
    
    saveConfigBtn?.addEventListener('click', saveConfig);
    resetConfigBtn?.addEventListener('click', resetConfig);
    
    selectFileBtn?.addEventListener('click', () => fileInput.click());
    
    fileInput?.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    uploadZone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.background = 'rgba(99, 102, 241, 0.1)';
    });
    
    uploadZone?.addEventListener('dragleave', () => {
        uploadZone.style.background = 'transparent';
    });
    
    uploadZone?.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.background = 'transparent';
        handleFiles(e.dataTransfer.files);
    });
    
    function handleFiles(files) {
        selectedFiles = Array.from(files);
        renderFileList();
        uploadZone.style.display = 'none';
        uploadPreview.style.display = 'block';
    }
    
    function renderFileList() {
        fileList.innerHTML = selectedFiles.map((file, index) => `
            <div class="file-item">
                <div class="file-icon"><i class="fas fa-file"></i></div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
                <button class="remove-file-btn" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }
    
    window.removeFile = (index) => {
        selectedFiles.splice(index, 1);
        if (selectedFiles.length === 0) {
            resetUpload();
        } else {
            renderFileList();
        }
    };
    
    function resetUpload() {
        selectedFiles = [];
        uploadZone.style.display = 'block';
        uploadPreview.style.display = 'none';
        fileInput.value = '';
    }
    
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
    
    confirmUploadBtn?.addEventListener('click', async () => {
        if (selectedFiles.length === 0) {
            showToast('请选择文件', 'error');
            return;
        }
        
        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('files', file));
        
        try {
            confirmUploadBtn.disabled = true;
            confirmUploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 上传中...';
            
            const response = await fetch('/api/rag/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('上传成功！');
                uploadModal.classList.remove('active');
                resetUpload();
                loadDocuments();
            } else {
                showToast(data.error || '上传失败', 'error');
            }
        } catch (error) {
            showToast('上传失败：' + error.message, 'error');
        } finally {
            confirmUploadBtn.disabled = false;
            confirmUploadBtn.innerHTML = '<i class="fas fa-upload"></i> 上传';
        }
    });
    
    refreshDocsBtn?.addEventListener('click', loadDocuments);
    
    async function loadDocuments() {
        try {
            const [docsResponse, statsResponse] = await Promise.all([
                fetch('/api/rag/documents'),
                fetch('/api/rag/stats')
            ]);
            
            const docsData = await docsResponse.json();
            currentDocuments = docsData.documents || [];
            renderDocuments();
            updateChatDocSelect();
            
            if (statsResponse.ok) {
                const statsData = await statsResponse.json();
                updateStats(statsData.stats);
            } else {
                updateStats(null);
            }
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    }
    
    function renderDocuments() {
        if (currentDocuments.length === 0) {
            documentsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <h3>知识库为空</h3>
                    <p>上传文档开始使用 RAG 功能</p>
                    <button class="btn-primary" id="emptyUploadBtn2">
                        <i class="fas fa-upload"></i>
                        上传文档
                    </button>
                </div>
            `;
            document.getElementById('emptyUploadBtn2')?.addEventListener('click', () => uploadModal.classList.add('active'));
        } else {
            documentsGrid.innerHTML = currentDocuments.map((doc, index) => `
                <div class="document-card" onclick="showDocDetail('${doc.doc_id}')">
                    <div class="document-icon">
                        <i class="${getFileIcon(doc.filename)}"></i>
                    </div>
                    <div class="document-info">
                        <h4>${doc.filename}</h4>
                        <p><i class="fas fa-clock"></i> ${new Date(doc.upload_time).toLocaleString()}</p>
                    </div>
                </div>
            `).join('');
        }
    }
    
    function getFileIcon(filename) {
        const ext = (filename.split('.').pop() || '').toLowerCase();
        const iconMap = {
            'pdf': 'fas fa-file-pdf',
            'doc': 'fas fa-file-word',
            'docx': 'fas fa-file-word',
            'txt': 'fas fa-file-alt',
            'md': 'fas fa-file-alt',
            'html': 'fas fa-file-code',
            'htm': 'fas fa-file-code',
            'py': 'fab fa-python',
            'js': 'fab fa-js',
            'json': 'fas fa-file-code'
        };
        return iconMap[ext] || 'fas fa-file-alt';
    }
    
    function updateStats(stats) {
        document.getElementById('docCount').textContent = currentDocuments.length;
        
        if (stats) {
            document.getElementById('searchCount').textContent = stats.search_count || 0;
            if (stats.total_size_human) {
                document.getElementById('totalSize').textContent = stats.total_size_human;
            } else {
                const totalSize = currentDocuments.reduce((sum, doc) => sum + (doc.file_size || 0), 0);
                document.getElementById('totalSize').textContent = formatFileSize(totalSize);
            }
        } else {
            const totalSize = currentDocuments.reduce((sum, doc) => sum + (doc.file_size || 0), 0);
            document.getElementById('totalSize').textContent = formatFileSize(totalSize);
        }
    }
    
    window.showDocDetail = async (docId) => {
        selectedDocId = docId;
        const doc = currentDocuments.find(d => d.doc_id === docId);
        
        if (doc) {
            document.getElementById('docDetailTitle').textContent = doc.filename;
            document.getElementById('detailFilename').textContent = doc.filename;
            document.getElementById('detailUploadTime').textContent = new Date(doc.upload_time).toLocaleString();
            document.getElementById('detailSize').textContent = formatFileSize(doc.file_size || 0);
            document.getElementById('docContentPreview').textContent = doc.content_preview || '暂无预览';
            
            docDetailModal.classList.add('active');
        }
    };
    
    closeDocDetailModal?.addEventListener('click', () => docDetailModal.classList.remove('active'));
    closeDocDetailBtn2?.addEventListener('click', () => docDetailModal.classList.remove('active'));
    
    deleteDocBtn?.addEventListener('click', async () => {
        if (!selectedDocId) return;
        
        if (!confirm('确定要删除这个文档吗？')) return;
        
        try {
            const response = await fetch(`/api/rag/documents/${selectedDocId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('删除成功！');
                docDetailModal.classList.remove('active');
                loadDocuments();
            } else {
                showToast(data.error || '删除失败', 'error');
            }
        } catch (error) {
            showToast('删除失败：' + error.message, 'error');
        }
    });
    
    ragSearchBtn?.addEventListener('click', performSearch);
    ragSearchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    
    async function performSearch() {
        const query = ragSearchInput.value.trim();
        if (!query) {
            showToast('请输入搜索内容', 'error');
            return;
        }
        
        const topK = parseInt(document.getElementById('topKSelect').value) || 5;
        const searchTitleOnly = document.getElementById('searchTitleOnly')?.checked || false;
        
        try {
            const response = await fetch('/api/rag/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, top_k: topK, search_title_only: searchTitleOnly })
            });
            
            const data = await response.json();
            
            if (data.success) {
                renderSearchResults(data.results);
                document.getElementById('searchCount').textContent = parseInt(document.getElementById('searchCount').textContent || 0) + 1;
            } else {
                showToast(data.error || '搜索失败', 'error');
            }
        } catch (error) {
            showToast('搜索失败：' + error.message, 'error');
        }
    }
    
    function renderSearchResults(results) {
        if (!results || results.length === 0) {
            resultsList.innerHTML = '<div class="empty-state small"><p>未找到相关结果</p></div>';
            document.getElementById('resultsCount').textContent = '0 个结果';
        } else {
            const seenFiles = new Map();
            
            results.forEach(result => {
                const filename = result.filename || (result.metadata && result.metadata.filename) || '未知文档';
                const score = typeof result.score === 'number' ? result.score : 0;
                const content = result.content || '';
                
                if (seenFiles.has(filename)) {
                    const existing = seenFiles.get(filename);
                    if (score > existing.score) {
                        seenFiles.set(filename, { filename, score, content });
                    }
                } else {
                    seenFiles.set(filename, { filename, score, content });
                }
            });
            
            const uniqueResults = Array.from(seenFiles.values());
            uniqueResults.sort((a, b) => b.score - a.score);
            
            resultsList.innerHTML = uniqueResults.map((result, index) => {
                return `
                    <div class="search-result-item">
                        <div class="result-score">${(result.score * 100).toFixed(0)}%</div>
                        <div class="result-content">
                            <h4>${result.filename}</h4>
                            <div class="result-paragraph">${formatContentForDisplay(result.content)}</div>
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('resultsCount').textContent = `${uniqueResults.length} 个结果`;
        }
        
        ragSearchResults.style.display = 'block';
    }

    function formatContentForDisplay(content) {
        if (!content) return '';
        
        let formatted = escapeHtml(content);
        
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    async function loadConfig() {
        try {
            const response = await fetch('/api/rag/config');
            const data = await response.json();
            
            if (data.success && data.config) {
                const cfg = data.config;
                
                document.getElementById('cfgSimilarityThreshold').value = cfg.similarity_threshold || 0.7;
                document.getElementById('cfgSimilarityThresholdValue').textContent = cfg.similarity_threshold || 0.7;
                
                document.getElementById('cfgMaxRetrieveCount').value = cfg.max_retrieve_count || 60;
                document.getElementById('cfgRerankWeight').value = cfg.rerank_weight || 0.5;
                document.getElementById('cfgRerankWeightValue').textContent = cfg.rerank_weight || 0.5;
                
                document.getElementById('cfgVectorWeight').value = cfg.vector_weight || 0.3;
                document.getElementById('cfgVectorWeightValue').textContent = cfg.vector_weight || 0.3;
                document.getElementById('cfgBm25Weight').value = cfg.bm25_weight || 0.7;
                document.getElementById('cfgBm25WeightValue').textContent = cfg.bm25_weight || 0.7;
                
                document.getElementById('cfgChunkSizeSmall').value = cfg.chunk_size_small || 256;
                document.getElementById('cfgChunkSizeBig').value = cfg.chunk_size_big || 1024;
                
                document.getElementById('cfgEnableQueryRewrite').checked = cfg.enable_query_rewrite !== false;
                document.getElementById('cfgEnableHyde').checked = cfg.enable_hyde === true;
            }
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }
    
    async function saveConfig() {
        try {
            const config = {
                similarity_threshold: parseFloat(document.getElementById('cfgSimilarityThreshold').value),
                max_retrieve_count: parseInt(document.getElementById('cfgMaxRetrieveCount').value),
                rerank_weight: parseFloat(document.getElementById('cfgRerankWeight').value),
                memory_window_size: 8,
                memory_compression_threshold: 0.9,
                max_context_tokens: 3500,
                vector_weight: parseFloat(document.getElementById('cfgVectorWeight').value),
                bm25_weight: parseFloat(document.getElementById('cfgBm25Weight').value),
                chunk_size_small: parseInt(document.getElementById('cfgChunkSizeSmall').value),
                chunk_size_big: parseInt(document.getElementById('cfgChunkSizeBig').value),
                enable_query_rewrite: document.getElementById('cfgEnableQueryRewrite').checked,
                enable_hyde: document.getElementById('cfgEnableHyde').checked,
                enable_metadata_filter: true
            };
            
            const response = await fetch('/api/rag/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('配置保存成功！');
                configModal.classList.remove('active');
            } else {
                showToast(data.message || '保存失败', 'error');
            }
        } catch (error) {
            showToast('保存失败：' + error.message, 'error');
        }
    }
    
    function resetConfig() {
        document.getElementById('cfgSimilarityThreshold').value = 0.7;
        document.getElementById('cfgSimilarityThresholdValue').textContent = '0.7';
        document.getElementById('cfgMaxRetrieveCount').value = 60;
        document.getElementById('cfgRerankWeight').value = 0.5;
        document.getElementById('cfgRerankWeightValue').textContent = '0.5';
        document.getElementById('cfgVectorWeight').value = 0.3;
        document.getElementById('cfgVectorWeightValue').textContent = '0.3';
        document.getElementById('cfgBm25Weight').value = 0.7;
        document.getElementById('cfgBm25WeightValue').textContent = '0.7';
        document.getElementById('cfgChunkSizeSmall').value = 256;
        document.getElementById('cfgChunkSizeBig').value = 1024;
        document.getElementById('cfgEnableQueryRewrite').checked = true;
        document.getElementById('cfgEnableHyde').checked = false;
        
        showToast('已重置为默认值');
    }
    
    document.getElementById('cfgSimilarityThreshold')?.addEventListener('input', (e) => {
        document.getElementById('cfgSimilarityThresholdValue').textContent = e.target.value;
    });
    
    document.getElementById('cfgRerankWeight')?.addEventListener('input', (e) => {
        document.getElementById('cfgRerankWeightValue').textContent = e.target.value;
    });
    
    document.getElementById('cfgVectorWeight')?.addEventListener('input', (e) => {
        document.getElementById('cfgVectorWeightValue').textContent = e.target.value;
    });
    
    document.getElementById('cfgBm25Weight')?.addEventListener('input', (e) => {
        document.getElementById('cfgBm25WeightValue').textContent = e.target.value;
    });
    
    toggleChatBtn?.addEventListener('click', () => {
        if (chatSection.style.display === 'none') {
            chatSection.style.display = 'flex';
            documentsSection.style.display = 'none';
            toggleChatBtn.classList.add('primary');
            updateChatDocSelect();
        } else {
            chatSection.style.display = 'none';
            documentsSection.style.display = 'block';
            toggleChatBtn.classList.remove('primary');
        }
    });
    
    chatModeBtns?.forEach(btn => {
        btn.addEventListener('click', () => {
            chatModeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentChatMode = btn.dataset.mode;
            
            if (currentChatMode === 'document') {
                docSelector.style.display = 'block';
            } else {
                docSelector.style.display = 'none';
            }
        });
    });
    
    clearChatBtn?.addEventListener('click', () => {
        chatHistory = [];
        sourceDocuments = [];
        renderChatMessages();
        updateSourceDocs();
    });
    
    startChatWithDocBtn?.addEventListener('click', () => {
        docDetailModal.classList.remove('active');
        currentChatMode = 'document';
        currentChatDocId = selectedDocId;
        
        chatSection.style.display = 'flex';
        documentsSection.style.display = 'none';
        toggleChatBtn.classList.add('primary');
        
        chatModeBtns.forEach(b => b.classList.remove('active'));
        document.querySelector('.chat-mode-btn[data-mode="document"]').classList.add('active');
        docSelector.style.display = 'block';
        
        updateChatDocSelect();
        chatDocSelect.value = selectedDocId;
        
        chatHistory = [];
        renderChatMessages();
    });
    
    function updateChatDocSelect() {
        if (!chatDocSelect) return;
        chatDocSelect.innerHTML = '<option value="">选择要对话的文档</option>' + 
            currentDocuments.map(doc => 
                `<option value="${doc.doc_id}">${doc.filename}</option>`
            ).join('');
    }
    
    chatDocSelect?.addEventListener('change', (e) => {
        currentChatDocId = e.target.value;
    });
    
    chatInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    chatSendBtn?.addEventListener('click', sendChatMessage);
    
    async function sendChatMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        
        chatInput.value = '';
        chatSendBtn.disabled = true;
        
        chatHistory.push({ role: 'user', content: message });
        renderChatMessages();
        
        try {
            const response = await fetch('/api/rag/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: message,
                    doc_id: currentChatMode === 'document' ? currentChatDocId : null,
                    session_id: currentChatDocId ? currentChatDocId : null,
                    history: chatHistory.slice(0, -1)
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                chatHistory.push({ role: 'assistant', content: data.answer });
                sourceDocuments = data.document ? [data.document] : [];
                renderChatMessages();
                updateSourceDocs();
            } else {
                showToast(data.detail || '发送失败', 'error');
            }
        } catch (error) {
            console.error('Chat error:', error);
            showToast('发送失败，请稍后重试', 'error');
        }
        
        chatSendBtn.disabled = false;
    }
    
    function renderChatMessages() {
        if (!chatMessages) return;
        
        if (chatHistory.length === 0) {
            chatMessages.innerHTML = `
                <div class="chat-empty-state">
                    <i class="fas fa-comments"></i>
                    <h3>开始对话</h3>
                    <p>选择对话模式并输入您的问题</p>
                </div>
            `;
            return;
        }
        
        chatMessages.innerHTML = chatHistory.map(msg => `
            <div class="chat-message ${msg.role}">
                <div class="chat-avatar">
                    <i class="fas fa-${msg.role === 'user' ? 'user' : 'robot'}"></i>
                </div>
                <div class="chat-bubble">
                    ${msg.content.replace(/\n/g, '<br>')}
                </div>
            </div>
        `).join('');
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function updateSourceDocs() {
        if (!chatSourceLabel) return;
        
        if (sourceDocuments.length > 0) {
            chatSourceLabel.style.display = 'flex';
            chatSourceLabel.innerHTML = `
                <i class="fas fa-book"></i> 参考来源：
                <span class="chat-source-docs">
                    ${sourceDocuments.map(doc => 
                        `<span class="chat-source-doc">${doc.filename}</span>`
                    ).join('')}
                </span>
            `;
        } else {
            chatSourceLabel.style.display = 'none';
        }
    }
    
    loadDocuments();
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('documentsGrid')) {
        initRAG();
    }
});
