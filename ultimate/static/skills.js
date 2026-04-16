let skillsData = [];

let installHistory = [];
let installCount = 0;
let currentInstallMethod = 'json';

document.addEventListener('DOMContentLoaded', function() {
    initEventListeners();
    loadSkillsFromBackend();
});


function loadSkillsFromBackend() {
    fetch('/api/skills/list')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.skills) {
                skillsData = data.skills;
            }
            renderSkills();
            updateStats();
        })
        .catch(error => {
            console.error('Failed to load skills from backend:', error);
            renderSkills();
            updateStats();
        });
}

function initEventListeners() {
    document.getElementById('refreshSkillsBtn').addEventListener('click', function() {
        this.querySelector('i').classList.add('fa-spin');
        loadSkillsFromBackend();
        setTimeout(() => {
            this.querySelector('i').classList.remove('fa-spin');
            showToast('技能列表已刷新', 'success');
        }, 500);
    });
    
    const installBtn = document.getElementById('installSkillBtn');
    const dropdownMenu = document.getElementById('skillDropdownMenu');
    
    installBtn?.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownMenu.classList.toggle('show');
    });
    
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function() {
            const method = this.dataset.method;
            currentInstallMethod = method;
            
            document.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            dropdownMenu.classList.remove('show');
            
            openInstallModal();
        });
    });
    
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            dropdownMenu?.classList.remove('show');
        }
    });
    
    document.getElementById('closeInstallModal').addEventListener('click', closeInstallModal);
    document.getElementById('cancelInstallBtn').addEventListener('click', closeInstallModal);
    document.getElementById('confirmInstallBtn').addEventListener('click', confirmImportSkill);
    
    document.getElementById('closeSkillDetailModal').addEventListener('click', closeSkillDetailModal);
    document.getElementById('closeSkillDetailBtn').addEventListener('click', closeSkillDetailModal);
    document.getElementById('useSkillBtn').addEventListener('click', useSkill);
    document.getElementById('uninstallSkillBtn').addEventListener('click', uninstallSkill);
    
    document.querySelectorAll('.category-filter').forEach(filter => {
        filter.addEventListener('click', function() {
            document.querySelectorAll('.category-filter').forEach(f => f.classList.remove('active'));
            this.classList.add('active');
            renderSkills(this.dataset.category);
        });
    });
    
    document.querySelector('.modal#installSkillModal')?.addEventListener('click', function(e) {
        if (e.target === this) closeInstallModal();
    });
    document.querySelector('.modal#skillDetailModal')?.addEventListener('click', function(e) {
        if (e.target === this) closeSkillDetailModal();
    });
}

function openInstallModal() {
    updateInstallModalUI();
    document.getElementById('installSkillModal').classList.add('active');
}

function updateInstallModalUI() {
    const modalTitle = document.querySelector('#installSkillModal h3');
    const configTextarea = document.getElementById('skillConfigJson');
    
    const titles = {
        'zip': '上传 .zip 技能包',
        'folder': '上传技能文件夹',
        'github': '从 GitHub 导入技能',
        'json': '技能管理'
    };
    
    if (modalTitle) {
        modalTitle.innerHTML = `<i class="fas fa-plus"></i> ${titles[currentInstallMethod]}`;
    }
    
    const formGroup = document.querySelector('#installSkillModal .form-group');
    if (formGroup) {
        if (currentInstallMethod === 'json') {
            formGroup.querySelector('label').textContent = '输入 JSON Array 格式的技能配置:';
            configTextarea.placeholder = `[
  {
    "id": "english_translator",
    "name": "英翻中",
    "description": "专业的英文翻译至中文助手",
    "handler_type": "prompt",
    "config": {
      "prompt": "你是一个专业的翻译助手，请将用户发送的内容翻译为中文。"
    }
  }
]`;
            configTextarea.style.display = 'block';
        } else if (currentInstallMethod === 'github') {
            formGroup.querySelector('label').textContent = '输入 GitHub 仓库地址:';
            configTextarea.placeholder = 'https://github.com/username/repo';
            configTextarea.style.display = 'block';
        } else if (currentInstallMethod === 'zip' || currentInstallMethod === 'folder') {
            formGroup.querySelector('label').textContent = `选择${currentInstallMethod === 'zip' ? '.zip 文件' : '文件夹'}:`;
            configTextarea.style.display = 'none';
            if (!document.querySelector('#fileInput')) {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.id = 'fileInput';
                fileInput.accept = currentInstallMethod === 'zip' ? '.zip' : '';
                if (currentInstallMethod === 'folder') {
                    fileInput.webkitdirectory = true;
                    fileInput.directory = true;
                }
                fileInput.style.marginTop = '10px';
                formGroup.appendChild(fileInput);
            }
        }
    }
}

function renderSkills(category = 'all') {
    const grid = document.getElementById('skillsGrid');
    
    let filtered = skillsData;
    if (category !== 'all') {
        filtered = skillsData.filter(s => s.category === category);
    }
    
    grid.innerHTML = filtered.map(skill => `
        <div class="tool-card ${skill.installed ? 'active' : ''}" data-id="${skill.id}">
            <div class="tool-card-header">
                <div class="tool-icon" style="background: linear-gradient(135deg, #667eea, #764ba2);">
                    <i class="fas fa-${skill.icon || 'puzzle-piece'}"></i>
                </div>
                <div class="tool-status">
                    ${skill.installed ? '<span class="status-badge installed">已安装</span>' : '<span class="status-badge">可安装</span>'}
                </div>
            </div>
            <h4>${skill.name}</h4>
            <p>${skill.description}</p>
            <div class="skill-meta">
                <span><i class="fas fa-tag"></i> ${skill.category}</span>
                <span><i class="fas fa-code-branch"></i> v${skill.version}</span>
            </div>
            ${skill.tags && skill.tags.length > 0 ? `
            <div class="skill-tags">
                ${skill.tags.map(tag => `<span class="skill-tag">${tag}</span>`).join('')}
            </div>
            ` : ''}
            <div class="tool-card-actions">
                ${skill.installed ? `
                    <button class="tool-btn" onclick="showSkillDetail('${skill.id}')">
                        <i class="fas fa-eye"></i> 详情
                    </button>
                    <button class="tool-btn primary" onclick="showSkillDetail('${skill.id}')">
                        <i class="fas fa-play"></i> 使用
                    </button>
                ` : `
                    <button class="tool-btn" onclick="showSkillDetail('${skill.id}')">
                        <i class="fas fa-info-circle"></i> 详情
                    </button>
                    <button class="tool-btn success" onclick="installSkillDirect('${skill.id}')">
                        <i class="fas fa-download"></i> 安装
                    </button>
                `}
            </div>
        </div>
    `).join('');
}

function updateStats() {
    const total = skillsData.length;
    const installed = skillsData.filter(s => s.installed).length;
    document.getElementById('totalSkills').textContent = total;
    document.getElementById('installedSkills').textContent = installed;
    document.getElementById('installCount').textContent = installCount;
}

function showSkillDetail(skillId) {
    const skill = skillsData.find(s => s.id === skillId);
    if (!skill) return;
    
    document.getElementById('skillDetailIcon').innerHTML = `<i class="fas fa-${skill.icon || 'puzzle-piece'}"></i>`;
    document.getElementById('skillDetailName').textContent = skill.name;
    document.getElementById('skillDetailVersion').textContent = `v${skill.version} · ${skill.author}`;
    document.getElementById('skillDetailDesc').textContent = skill.description;
    document.getElementById('skillDetailCategory').textContent = skill.category;
    document.getElementById('skillDetailStatus').textContent = skill.installed ? '已安装' : '未安装';
    document.getElementById('skillDetailStatus').className = skill.installed ? 'skill-status-badge installed' : 'skill-status-badge';
    
    const tagsSection = document.getElementById('skillTagsSection');
    const tagsContainer = document.getElementById('skillDetailTags');
    
    if (skill.tags && skill.tags.length > 0) {
        tagsContainer.innerHTML = skill.tags.map(tag => `<span class="skill-tag">${tag}</span>`).join('');
        tagsSection.style.display = 'block';
    } else {
        tagsSection.style.display = 'none';
    }
    
    document.getElementById('uninstallSkillBtn').style.display = skill.installed ? 'inline-flex' : 'none';
    document.getElementById('useSkillBtn').style.display = skill.installed ? 'inline-flex' : 'none';
    
    document.getElementById('skillResults').style.display = 'none';
    
    document.getElementById('skillDetailModal').classList.add('active');
    document.getElementById('skillDetailModal').dataset.skillId = skillId;
}

function installSkillDirect(skillId) {
    const skill = skillsData.find(s => s.id === skillId);
    if (!skill) return;
    
    skill.installed = true;
    installCount++;
    renderSkills();
    updateStats();
    addToHistory(skill, 'install');
    showToast(`技能 "${skill.name}" 安装成功！`, 'success');
}

function closeInstallModal() {
    document.getElementById('installSkillModal').classList.remove('active');
    const configTextarea = document.getElementById('skillConfigJson');
    if (configTextarea) {
        configTextarea.value = '';
    }
    const fileInput = document.querySelector('#fileInput');
    if (fileInput) {
        fileInput.remove();
    }
}

function confirmImportSkill() {
    if (currentInstallMethod === 'json') {
        const configText = document.getElementById('skillConfigJson').value.trim();
        
        if (!configText) {
            showToast('请输入技能配置 JSON', 'warning');
            return;
        }
        
        try {
            const skills = JSON.parse(configText);
            
            if (Array.isArray(skills)) {
                let addedCount = 0;
                for (const skill of skills) {
                    const skillId = skill.id || skill.name.toLowerCase().replace(/\s+/g, '_');
                    skillsData.push({
                        id: skillId,
                        name: skill.name || '未知技能',
                        description: skill.description || '',
                        icon: skill.icon || 'puzzle-piece',
                        category: skill.category || '自定义',
                        version: skill.version || '1.0.0',
                        author: skill.author || 'User',
                        installed: true
                    });
                    addedCount++;
                }
                installCount += addedCount;
                renderSkills();
                updateStats();
                closeInstallModal();
                showToast(`成功导入 ${addedCount} 个技能！`, 'success');
            } else {
                showToast('请输入 JSON Array 格式', 'error');
            }
        } catch (e) {
            showToast('JSON 解析错误: ' + e.message, 'error');
        }
    } else if (currentInstallMethod === 'github') {
        const repoUrl = document.getElementById('skillConfigJson').value.trim();
        if (!repoUrl) {
            showToast('请输入 GitHub 仓库地址', 'warning');
            return;
        }
        
        showToast('正在从 GitHub 导入技能，请稍候...', 'info');
        
        fetch('/api/skills/import/github', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_url: repoUrl })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const importedSkills = data.skills || [];
                importedSkills.forEach(skill => {
                    const existing = skillsData.find(s => s.id === skill.id);
                    if (existing) {
                        Object.assign(existing, skill);
                    } else {
                        skillsData.push(skill);
                    }
                });
                installCount += importedSkills.length;
                renderSkills();
                updateStats();
                closeInstallModal();
                showToast(data.message || '技能导入成功！', 'success');
            } else {
                showToast(data.message || '导入失败', 'error');
            }
        })
        .catch(error => {
            showToast('导入失败: ' + error.message, 'error');
        });
    } else if (currentInstallMethod === 'zip' || currentInstallMethod === 'folder') {
        const fileInput = document.querySelector('#fileInput');
        if (fileInput && fileInput.files.length > 0) {
            showToast('正在上传并处理文件，请稍候...', 'info');
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            fetch('/api/skills/import/file', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const importedSkills = data.skills || [];
                    importedSkills.forEach(skill => {
                        const existing = skillsData.find(s => s.id === skill.id);
                        if (existing) {
                            Object.assign(existing, skill);
                        } else {
                            skillsData.push(skill);
                        }
                    });
                    installCount += importedSkills.length;
                    renderSkills();
                    updateStats();
                    closeInstallModal();
                    showToast(data.message || '文件导入成功！', 'success');
                } else {
                    showToast(data.message || '导入失败', 'error');
                }
            })
            .catch(error => {
                showToast('导入失败: ' + error.message, 'error');
            });
        } else {
            showToast('请选择文件', 'warning');
        }
    }
}

function closeSkillDetailModal() {
    document.getElementById('skillDetailModal').classList.remove('active');
}

async function useSkill() {
    const skillId = document.getElementById('skillDetailModal').dataset.skillId;
    const skill = skillsData.find(s => s.id === skillId);
    if (!skill) return;
    
    const useSkillBtn = document.getElementById('useSkillBtn');
    const skillResults = document.getElementById('skillResults');
    const skillResultContent = document.getElementById('skillResultContent');
    
    try {
        useSkillBtn.disabled = true;
        useSkillBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 执行中...';
        skillResults.style.display = 'none';
        
        showToast(`正在使用技能：${skill.name}`, 'info');
        
        const response = await fetch(`/api/skills/use/${skillId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('技能执行成功！', 'success');
            
            skillResultContent.innerHTML = `
                <pre style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; white-space: pre-wrap; word-wrap: break-word;">${data.result}</pre>
            `;
            skillResults.style.display = 'block';
            
            addToHistory(skill, 'use');
        } else {
            showToast(data.message || '执行失败', 'error');
        }
    } catch (error) {
        showToast('执行失败：' + error.message, 'error');
    } finally {
        useSkillBtn.disabled = false;
        useSkillBtn.innerHTML = '<i class="fas fa-play"></i> 使用技能';
    }
}

function uninstallSkill() {
    const skillId = document.getElementById('skillDetailModal').dataset.skillId;
    const skill = skillsData.find(s => s.id === skillId);
    if (!skill) return;
    
    skill.installed = false;
    renderSkills();
    updateStats();
    addToHistory(skill, 'uninstall');
    closeSkillDetailModal();
    showToast(`技能 "${skill.name}" 已卸载`, 'success');
}

function addToHistory(skill, action) {
    const record = {
        skill: skill.name,
        action: action,
        time: new Date().toLocaleString('zh-CN')
    };
    installHistory.unshift(record);
    renderHistory();
}

function renderHistory() {
    const container = document.getElementById('installHistory');
    if (installHistory.length === 0) {
        container.innerHTML = `
            <div class="empty-state small">
                <i class="fas fa-history"></i>
                <p>暂无安装记录</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = installHistory.map(record => `
        <div class="history-row">
            <div class="history-cell">
                <div class="tool-icon small">
                    <i class="fas fa-puzzle-piece"></i>
                </div>
                <span>${record.skill}</span>
            </div>
            <div class="history-cell">
                <span class="status-badge ${record.action === 'install' ? 'success' : record.action === 'uninstall' ? 'danger' : ''}">
                    ${record.action === 'install' ? '安装' : record.action === 'uninstall' ? '卸载' : '使用'}
                </span>
            </div>
            <div class="history-cell">${record.time}</div>
        </div>
    `).join('');
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
