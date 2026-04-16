function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function initCodeHelper() {
    const editorTabs = document.querySelectorAll('.editor-tab');
    const editorPanels = document.querySelectorAll('.editor-panel');
    const codeRequest = document.getElementById('codeRequest');
    const codeOutput = document.getElementById('codeOutput');
    const codeChatInput = document.getElementById('codeChatInput');
    const codeChatSendBtn = document.getElementById('codeChatSendBtn');
    const codeMessages = document.getElementById('codeMessages');
    const generateCodeBtn = document.getElementById('generateCodeBtn');
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    const downloadCodeBtn = document.getElementById('downloadCodeBtn');
    const clearEditorBtn = document.getElementById('clearEditorBtn');
    const analyzeCodeBtn = document.getElementById('analyzeCodeBtn');
    const templateItems = document.querySelectorAll('.template-item');
    const languageItems = document.querySelectorAll('.language-item');
    const runCodeBtn = document.getElementById('runCodeBtn');
    const codeExecutionOutput = document.getElementById('codeExecutionOutput');
    
    let currentLang = 'python';
    let ws = null;
    let currentAssistantMessage = null;
    
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
    
    setTimeout(() => {
        const initialCode = codeOutput.textContent || '# 代码将在这里显示';
        updateCodeDisplay(initialCode);
    }, 100);
    
    const templates = {
        hello: {
            python: `print("Hello, World!")`,
            javascript: `console.log("Hello, World!");`,
            java: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}`,
            cpp: `#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    return 0;
}`,
            go: `package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}`,
            rust: `fn main() {
    println!("Hello, World!");
}`,
            r: `print("Hello, World!")`,
            scala: `object Main {
  def main(args: Array[String]): Unit = {
    println("Hello, World!")
  }
}`,
            typescript: `console.log("Hello, World!");`,
            react: `import React from 'react';

function App() {
  return (
    <div>
      <h1>Hello, World!</h1>
    </div>
  );
}

export default App;`,
            sql: `SELECT 'Hello, World!' AS message;`,
            shell: `#!/bin/bash
echo "Hello, World!"`
        },
        api: {
            python: `from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}`,
            javascript: `const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
    res.json({ message: 'Hello, World!' });
});

app.get('/items/:id', (req, res) => {
    res.json({ item_id: req.params.id, q: req.query.q });
});

app.listen(port, () => {
    console.log(\`Server running on port \${port}\`);
});`
        },
        web: {
            python: `<!DOCTYPE html>
<html>
<head>
    <title>My Page</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>Welcome to my webpage.</p>
</body>
</html>`,
            javascript: `<!DOCTYPE html>
<html>
<head>
    <title>My Page</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; }
    </style>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>Welcome to my webpage.</p>
    <script>
        alert('Welcome!');
    </script>
</body>
</html>`
        },
        data: {
            python: `import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

data = pd.DataFrame({
    'x': np.random.randn(100),
    'y': np.random.randn(100)
})

print(data.describe())
print("\\nCorrelation:", data['x'].corr(data['y']))

plt.scatter(data['x'], data['y'])
plt.title('Scatter Plot')
plt.show()`,
            javascript: `const data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const mean = data.reduce((a, b) => a + b, 0) / data.length;
const variance = data.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / data.length;
const stdDev = Math.sqrt(variance);

console.log('Data:', data);
console.log('Mean:', mean);
console.log('Variance:', variance);
console.log('Standard Deviation:', stdDev);`
        },
        sort: {
            python: `def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

def bubblesort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

data = [64, 34, 25, 12, 22, 11, 90]
print('Original:', data)
print('QuickSort:', quicksort(data.copy()))
print('BubbleSort:', bubblesort(data.copy()))`,
            javascript: `function quicksort(arr) {
    if (arr.length <= 1) return arr;
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    return [...quicksort(left), ...middle, ...quicksort(right)];
}

function bubblesort(arr) {
    const n = arr.length;
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
            }
        }
    }
    return arr;
}

const data = [64, 34, 25, 12, 22, 11, 90];
console.log('Original:', data);
console.log('QuickSort:', quicksort([...data]));
console.log('BubbleSort:', bubblesort([...data]));`
        }
    };
    
    editorTabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
            editorTabs.forEach(t => t.classList.remove('active'));
            editorPanels.forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            editorPanels[index].classList.add('active');
        });
    });
    
    function updateCodeDisplay(code) {
        const langMap = {
            'python': 'python',
            'javascript': 'javascript',
            'java': 'java',
            'cpp': 'cpp',
            'go': 'go',
            'rust': 'rust',
            'r': 'r',
            'scala': 'scala',
            'typescript': 'typescript',
            'react': 'jsx',
            'sql': 'sql',
            'shell': 'bash'
        };
        
        codeOutput.className = `language-${langMap[currentLang] || 'python'}`;
        codeOutput.textContent = code;
        
        if (typeof Prism !== 'undefined') {
            Prism.highlightElement(codeOutput);
        }
        
        document.getElementById('codeLines').textContent = code.split('\n').length + ' 行';
    }
    
    templateItems.forEach(item => {
        item.addEventListener('click', () => {
            const template = templates[item.dataset.template];
            if (template) {
                const code = template[currentLang] || template['python'] || Object.values(template)[0];
                updateCodeDisplay(code);
                editorTabs[1].click();
            }
        });
    });
    
    languageItems.forEach(item => {
        item.addEventListener('click', () => {
            languageItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            currentLang = item.dataset.lang;
            document.getElementById('currentLang').textContent = item.textContent.trim();
            
            const currentCode = codeOutput.textContent;
            if (currentCode && !currentCode.startsWith('# 代码')) {
                updateCodeDisplay(currentCode);
            }
        });
    });
    
    generateCodeBtn?.addEventListener('click', async () => {
        const request = codeRequest.value.trim();
        if (!request) {
            showToast('请输入代码需求', 'error');
            return;
        }
        
        generateCodeBtn.disabled = true;
        generateCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';
        
        try {
            const response = await fetch('/api/code-helper/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    request: request,
                    language: currentLang,
                    add_comments: false,
                    add_tests: false,
                    explain_code: false
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                const code = data.code || '# Code generation in demo mode\n# Please connect to Qwen API';
                updateCodeDisplay(code);
                editorTabs[1].click();
                showToast('代码生成成功！');
                
                document.getElementById('codeSnippets').textContent = parseInt(document.getElementById('codeSnippets').textContent || 0) + 1;
                document.getElementById('problemsSolved').textContent = parseInt(document.getElementById('problemsSolved').textContent || 0) + 1;
            } else {
                showToast(data.error || '生成失败', 'error');
            }
        } catch (error) {
            showToast('生成失败：' + error.message, 'error');
            const demoCode = '# Demo: ' + request + '\n# ' + currentLang + ' code will appear here';
            updateCodeDisplay(demoCode);
        } finally {
            generateCodeBtn.disabled = false;
            generateCodeBtn.innerHTML = '<i class="fas fa-magic"></i> 生成代码';
        }
    });
    
    runCodeBtn?.addEventListener('click', async () => {
        const code = codeOutput.textContent;
        if (!code || code.startsWith('# 代码')) {
            showToast('请先生成或选择代码', 'error');
            return;
        }
        
        runCodeBtn.disabled = true;
        runCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 运行中...';
        editorTabs[2].click();
        
        try {
            const response = await fetch('/api/code-helper/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    language: currentLang
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                codeExecutionOutput.innerHTML = data.output.split('\n').map(line => 
                    `<div class="output-line">${line}</div>`
                ).join('');
                showToast('代码运行成功！');
            } else {
                codeExecutionOutput.innerHTML = `<div class="output-line error">${data.output}</div>`;
                showToast('代码运行失败', 'error');
            }
        } catch (error) {
            codeExecutionOutput.innerHTML = `<div class="output-line error">运行错误：${error.message}</div>`;
            showToast('运行失败：' + error.message, 'error');
        } finally {
            runCodeBtn.disabled = false;
            runCodeBtn.innerHTML = '<i class="fas fa-play"></i> 运行代码';
        }
    });
    
    copyCodeBtn?.addEventListener('click', () => {
        navigator.clipboard.writeText(codeOutput.textContent).then(() => {
            showToast('代码已复制！');
        });
    });
    
    downloadCodeBtn?.addEventListener('click', () => {
        const ext = {
            python: 'py',
            javascript: 'js',
            java: 'java',
            cpp: 'cpp'
        }[currentLang] || 'txt';
        
        const blob = new Blob([codeOutput.textContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'code.' + ext;
        a.click();
        URL.revokeObjectURL(url);
        showToast('代码已下载！');
    });
    
    clearEditorBtn?.addEventListener('click', () => {
        codeRequest.value = '';
        codeOutput.textContent = '# ' + currentLang + ' code will appear here';
        document.getElementById('codeLines').textContent = '0 行';
    });

    analyzeCodeBtn?.addEventListener('click', async () => {
        const code = codeOutput.textContent;
        if (!code || code.startsWith('# 代码') || code.startsWith('# ' + currentLang)) {
            showToast('请先生成或选择代码', 'error');
            return;
        }

        analyzeCodeBtn.disabled = true;
        analyzeCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch('/api/code-helper/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    language: currentLang
                })
            });

            const data = await response.json();

            if (data.success) {
                const analysis = data.analysis;
                
                const messageDiv = document.createElement('div');
                messageDiv.className = 'code-message assistant';
                messageDiv.innerHTML = `
                    <div class="code-message-avatar"><i class="fas fa-search"></i></div>
                    <div class="code-message-content">
                        <div class="code-message-bubble" style="white-space: pre-wrap;">${escapeHtml(analysis)}</div>
                    </div>
                `;
                codeMessages.appendChild(messageDiv);
                codeMessages.scrollTop = codeMessages.scrollHeight;
                
                showToast('代码分析完成！');
            } else {
                showToast(data.error || '分析失败', 'error');
            }
        } catch (error) {
            showToast('分析失败：' + error.message, 'error');
        } finally {
            analyzeCodeBtn.disabled = false;
            analyzeCodeBtn.innerHTML = '<i class="fas fa-search-plus"></i>';
        }
    });

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    let codeChatHistory = [];
    
    async function sendChatMessage(message) {
        if (!message.trim()) return;
        
        const userDiv = document.createElement('div');
        userDiv.className = 'code-message user';
        userDiv.innerHTML = `
            <div class="code-message-avatar"><i class="fas fa-user"></i></div>
            <div class="code-message-content">
                <div class="code-message-bubble">${escapeHtml(message)}</div>
            </div>
        `;
        codeMessages.appendChild(userDiv);
        
        codeChatHistory.push({ role: 'user', content: message });
        
        codeChatInput.value = '';
        codeChatInput.style.height = 'auto';
        codeMessages.scrollTop = codeMessages.scrollHeight;
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'code-message assistant';
        loadingDiv.innerHTML = `
            <div class="code-message-avatar"><i class="fas fa-code"></i></div>
            <div class="code-message-content">
                <div class="code-message-bubble"><i class="fas fa-spinner fa-spin"></i> 思考中...</div>
            </div>
        `;
        codeMessages.appendChild(loadingDiv);
        codeMessages.scrollTop = codeMessages.scrollHeight;
        
        try {
            const response = await fetch('/api/code-helper/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    history: codeChatHistory.slice(0, -1)
                })
            });
            
            const data = await response.json();
            
            loadingDiv.remove();
            
            if (data.success) {
                const assistantDiv = document.createElement('div');
                assistantDiv.className = 'code-message assistant';
                assistantDiv.innerHTML = `
                    <div class="code-message-avatar"><i class="fas fa-code"></i></div>
                    <div class="code-message-content">
                        <div class="code-message-bubble">${formatMessage(data.message)}</div>
                    </div>
                `;
                codeMessages.appendChild(assistantDiv);
                codeChatHistory.push({ role: 'assistant', content: data.message });
            } else {
                showToast(data.error || '发送失败', 'error');
            }
        } catch (error) {
            loadingDiv.remove();
            showToast('发送失败：' + error.message, 'error');
        }
        
        codeMessages.scrollTop = codeMessages.scrollHeight;
    }
    
    function formatMessage(text) {
        if (!text) return '';
        
        let formatted = escapeHtml(text);
        
        formatted = formatted.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<pre style="background: var(--bg-tertiary); padding: 12px; border-radius: var(--radius-sm); overflow-x: auto; margin: 8px 0;"><code>${code}</code></pre>`;
        });
        
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }
    
    codeChatSendBtn?.addEventListener('click', () => sendChatMessage(codeChatInput.value));
    
    codeChatInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage(codeChatInput.value);
        }
    });
    
    codeChatInput?.addEventListener('input', () => {
        codeChatInput.style.height = 'auto';
        codeChatInput.style.height = Math.min(codeChatInput.scrollHeight, 200) + 'px';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('codeRequest')) {
        initCodeHelper();
    }
});
