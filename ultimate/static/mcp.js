let mcpTools = [
    {
        id: 'calculator',
        name: '计算器',
        description: '执行数学计算',
        icon: 'calculator',
        category: '数学',
        params: [
            { name: 'expression', label: '数学表达式', type: 'text', placeholder: '例如: 2 + 2 * 3' }
        ]
    },
    {
        id: 'weather',
        name: '天气查询',
        description: '查询城市天气',
        icon: 'cloud-sun',
        category: '生活',
        params: [
            { name: 'city', label: '城市名称', type: 'text', placeholder: '例如: 北京' }
        ]
    },
    {
        id: 'translator',
        name: '翻译器',
        description: '文本翻译',
        icon: 'language',
        category: '语言',
        params: [
            { name: 'text', label: '待翻译文本', type: 'text', placeholder: '输入要翻译的文本' },
            { name: 'target_lang', label: '目标语言', type: 'text', placeholder: '例如: en' }
        ]
    },
    {
        id: 'web_search',
        name: '网页搜索',
        description: '搜索互联网信息',
        icon: 'search',
        category: '信息',
        params: [
            { name: 'query', label: '搜索关键词', type: 'text', placeholder: '输入搜索关键词' }
        ]
    },
    {
        id: 'file_analyzer',
        name: '文件分析器',
        description: '分析文件内容',
        icon: 'file-alt',
        category: '工具',
        params: [
            { name: 'file_path', label: '文件路径', type: 'text', placeholder: '输入文件路径' }
        ]
    },
    {
        id: 'code_executor',
        name: '代码执行器',
        description: '执行代码',
        icon: 'code',
        category: '编程',
        params: [
            { name: 'code', label: '代码', type: 'textarea', placeholder: '输入要执行的代码' }
        ]
    }
];

let executionHistory = [];
let execCount = 0;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('toolsGrid')) {
        initMCP();
    }
});

function initMCP() {
    const toolsGrid = document.getElementById('toolsGrid');
    const toolModal = document.getElementById('toolModal');
    const addToolModal = document.getElementById('addToolModal');
    const closeToolModal = document.getElementById('closeToolModal');
    const cancelToolBtn = document.getElementById('cancelToolBtn');
    const executeToolBtn = document.getElementById('executeToolBtn');
    const toolParams = document.getElementById('toolParams');
    const categoryFilters = document.querySelectorAll('.category-filter');
    const executionResults = document.getElementById('executionResults');
    const clearResultsBtn = document.getElementById('clearResultsBtn');
    const historyTable = document.getElementById('historyTable');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
    const refreshToolsBtn = document.getElementById('refreshToolsBtn');
    const addToolBtn = document.getElementById('addToolBtn');
    const closeAddToolModal = document.getElementById('closeAddToolModal');
    const cancelAddToolBtn = document.getElementById('cancelAddToolBtn');
    const confirmAddToolBtn = document.getElementById('confirmAddToolBtn');
    
    let currentTool = null;
    
    loadTools();
    
    function loadTools() {
        fetch('/api/mcp/tools')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.tools) {
                    mcpTools = data.tools.map(t => ({
                        ...t,
                        params: getToolParams(t.id)
                    }));
                }
                renderTools();
            })
            .catch(err => {
                renderTools();
            });
    }
    
    function getToolParams(toolId) {
        const paramMap = {
            'calculator': [{ name: 'expression', label: '数学表达式', type: 'text', placeholder: '例如: 2 + 2 * 3' }],
            'weather': [{ name: 'city', label: '城市名称', type: 'text', placeholder: '例如: 北京' }],
            'translator': [
                { name: 'text', label: '待翻译文本', type: 'text', placeholder: '输入要翻译的文本' },
                { name: 'target_lang', label: '目标语言', type: 'text', placeholder: '例如: en' }
            ],
            'web_search': [{ name: 'query', label: '搜索关键词', type: 'text', placeholder: '输入搜索关键词' }],
            'file_analyzer': [{ name: 'file_path', label: '文件路径', type: 'text', placeholder: '输入文件路径' }],
            'code_executor': [{ name: 'code', label: '代码', type: 'textarea', placeholder: '输入要执行的代码' }]
        };
        return paramMap[toolId] || [{ name: 'input', label: '输入', type: 'text', placeholder: '请输入...' }];
    }
    
    function renderTools(category = 'all') {
        const filteredTools = category === 'all' 
            ? mcpTools 
            : mcpTools.filter(t => t.category === category);
        
        toolsGrid.innerHTML = filteredTools.map(tool => `
            <div class="tool-card ${tool.custom ? 'custom' : ''}">
                <div class="tool-card-header">
                    <div class="tool-icon" style="background: ${tool.custom ? 'linear-gradient(135deg, #f093fb, #f5576c)' : 'linear-gradient(135deg, #667eea, #764ba2)'}">
                        <i class="fas fa-${tool.icon}"></i>
                    </div>
                    ${tool.custom ? '<span class="custom-badge">自定义</span>' : ''}
                </div>
                <h4>${tool.name}</h4>
                <p>${tool.description}</p>
                <div class="tool-card-actions">
                    <button class="tool-btn" onclick="openToolModal('${tool.id}')">
                        <i class="fas fa-play"></i> 使用
                    </button>
                    ${tool.custom ? `<button class="tool-btn danger" onclick="deleteTool('${tool.id}')">
                        <i class="fas fa-trash"></i> 删除
                    </button>` : ''}
                </div>
            </div>
        `).join('');
        
        document.getElementById('toolCount').textContent = mcpTools.length;
    }
    
    window.openToolModal = (toolId) => {
        currentTool = mcpTools.find(t => t.id === toolId);
        if (!currentTool) return;
        
        document.getElementById('modalToolIcon').innerHTML = `<i class="fas fa-${currentTool.icon}"></i>`;
        document.getElementById('modalToolName').textContent = currentTool.name;
        document.getElementById('modalToolDesc').textContent = currentTool.description;
        
        const params = currentTool.params || getToolParams(toolId);
        toolParams.innerHTML = params.map(param => `
            <div class="param-item">
                <label>${param.label}</label>
                ${param.type === 'textarea' 
                    ? `<textarea name="${param.name}" placeholder="${param.placeholder}"></textarea>`
                    : `<input type="text" name="${param.name}" placeholder="${param.placeholder}">`
                }
            </div>
        `).join('');
        
        toolModal.classList.add('active');
    };
    
    window.deleteTool = (toolId) => {
        if (!confirm('确定要删除这个工具吗？')) return;
        
        fetch(`/api/mcp/tools/${toolId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mcpTools = mcpTools.filter(t => t.id !== toolId);
                    renderTools();
                    showToast('工具已删除', 'success');
                }
            })
            .catch(err => {
                mcpTools = mcpTools.filter(t => t.id !== toolId);
                renderTools();
                showToast('工具已删除', 'success');
            });
    };
    
    closeToolModal?.addEventListener('click', () => toolModal.classList.remove('active'));
    cancelToolBtn?.addEventListener('click', () => toolModal.classList.remove('active'));
    
    executeToolBtn?.addEventListener('click', async () => {
        if (!currentTool) return;
        
        const params = {};
        toolParams.querySelectorAll('input, textarea').forEach(input => {
            params[input.name] = input.value;
        });
        
        const startTime = Date.now();
        
        try {
            executeToolBtn.disabled = true;
            executeToolBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 执行中...';
            
            const response = await fetch(`/api/mcp/${currentTool.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            
            const data = await response.json();
            const endTime = Date.now();
            const duration = endTime - startTime;
            
            if (data.success) {
                showToast('执行成功！', 'success');
                
                execCount++;
                document.getElementById('execCount').textContent = execCount;
                
                const avgTime = Math.round(duration);
                document.getElementById('avgTime').textContent = avgTime + 'ms';
                
                renderExecutionResult(currentTool, params, data.result, duration);
                addToHistory(currentTool, params, data.result, duration);
                
                toolModal.classList.remove('active');
            } else {
                showToast(data.error || '执行失败', 'error');
            }
        } catch (error) {
            showToast('执行失败：' + error.message, 'error');
        } finally {
            executeToolBtn.disabled = false;
            executeToolBtn.innerHTML = '<i class="fas fa-play"></i> 执行';
        }
    });
    
    function renderExecutionResult(tool, params, result, duration) {
        executionResults.innerHTML = `
            <div class="result-item">
                <div class="result-header">
                    <div class="result-icon">
                        <i class="fas fa-${tool.icon}"></i>
                    </div>
                    <div class="result-info">
                        <h4>${tool.name}</h4>
                        <p>${tool.description}</p>
                    </div>
                    <span class="result-status success">成功</span>
                </div>
                <div class="result-content">
                    <p><strong>输入参数：</strong></p>
                    <pre>${JSON.stringify(params, null, 2)}</pre>
                    <br>
                    <p><strong>执行结果：</strong></p>
                    <pre>${typeof result === 'object' ? JSON.stringify(result, null, 2) : result}</pre>
                </div>
            </div>
        `;
    }
    
    function addToHistory(tool, params, result, duration) {
        executionHistory.unshift({
            tool,
            params,
            result,
            duration,
            timestamp: new Date().toISOString()
        });
        
        renderHistory();
    }
    
    function renderHistory() {
        if (executionHistory.length === 0) {
            historyTable.innerHTML = '<div class="empty-state small"><i class="fas fa-history"></i><p>暂无执行历史</p></div>';
        } else {
            historyTable.innerHTML = executionHistory.slice(0, 10).map(item => `
                <div class="history-row">
                    <div class="history-cell">
                        <div class="tool-icon small">
                            <i class="fas fa-${item.tool.icon}"></i>
                        </div>
                        <span>${item.tool.name}</span>
                    </div>
                    <div class="history-cell">
                        <span class="status-badge success">${item.duration}ms</span>
                    </div>
                    <div class="history-cell">${new Date(item.timestamp).toLocaleTimeString()}</div>
                </div>
            `).join('');
        }
    }
    
    clearResultsBtn?.addEventListener('click', () => {
        executionResults.innerHTML = '<div class="empty-state small"><i class="fas fa-terminal"></i><p>选择工具开始执行</p></div>';
    });
    
    refreshHistoryBtn?.addEventListener('click', renderHistory);
    
    refreshToolsBtn?.addEventListener('click', () => {
        loadTools();
        showToast('工具列表已刷新', 'success');
    });
    
    categoryFilters.forEach(filter => {
        filter.addEventListener('click', () => {
            categoryFilters.forEach(f => f.classList.remove('active'));
            filter.classList.add('active');
            renderTools(filter.dataset.category);
        });
    });
    
    addToolBtn?.addEventListener('click', () => {
        addToolModal.classList.add('active');
    });
    
    closeAddToolModal?.addEventListener('click', () => addToolModal.classList.remove('active'));
    cancelAddToolBtn?.addEventListener('click', () => addToolModal.classList.remove('active'));
    
    confirmAddToolBtn?.addEventListener('click', () => {
        const configText = document.getElementById('mcpConfigJson').value.trim();
        
        if (!configText) {
            showToast('请输入 MCP 配置 JSON', 'warning');
            return;
        }
        
        try {
            const config = JSON.parse(configText);
            
            if (config.mcpServers) {
                let addedCount = 0;
                for (const [serverId, serverConfig] of Object.entries(config.mcpServers)) {
                    const toolId = serverId;
                    mcpTools.push({
                        id: toolId,
                        name: serverId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                        description: serverConfig.command 
                            ? `${serverConfig.command} ${(serverConfig.args || []).join(' ')}`
                            : 'MCP 服务器工具',
                        icon: 'server',
                        category: '自定义',
                        custom: true,
                        params: [{ name: 'input', label: '输入', type: 'text', placeholder: '请输入...' }]
                    });
                    addedCount++;
                }
                renderTools();
                addToolModal.classList.remove('active');
                document.getElementById('mcpConfigJson').value = '';
                showToast(`成功添加 ${addedCount} 个 MCP 服务器！`, 'success');
            } else {
                showToast('未找到 mcpServers 配置', 'error');
            }
        } catch (e) {
            showToast('JSON 解析错误: ' + e.message, 'error');
        }
    });
    
    addToolModal?.addEventListener('click', (e) => {
        if (e.target === addToolModal) addToolModal.classList.remove('active');
    });
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}
