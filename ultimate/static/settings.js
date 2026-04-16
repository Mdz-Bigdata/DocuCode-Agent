function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function initSettings() {
    const settingsNavItems = document.querySelectorAll('.settings-nav-item');
    const settingsSections = document.querySelectorAll('.settings-section');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const resetSettingsBtn = document.getElementById('resetSettingsBtn');
    const tempSlider = document.getElementById('tempSlider');
    const tempValue = document.getElementById('tempValue');
    const maxTokensSlider = document.getElementById('maxTokensSlider');
    const maxTokensValue = document.getElementById('maxTokensValue');
    const themeOptions = document.querySelectorAll('.theme-option');
    const clearCacheBtn = document.getElementById('clearCacheBtn');
    const exportDataBtn = document.getElementById('exportDataBtn');
    const modelProviderSelect = document.getElementById('modelProviderSelect');
    
    let settings = {
        language: 'zh-CN',
        timezone: 'Asia/Shanghai',
        notifications: true,
        sound: false,
        modelProvider: 'dashscope',
        dashscopeApiKey: '',
        dashscopeModel: 'qwen-max',
        localApiBase: 'http://localhost:8001/v1',
        localModelName: 'Qwen/Qwen2.5-7B-Instruct',
        localApiKey: '',
        temperature: 0.7,
        maxTokens: 2000,
        theme: 'dark',
        fontSize: 'medium',
        compactMode: false,
        autoSave: true,
        proxy: ''
    };
    
    function updateModelConfigUI() {
        const provider = modelProviderSelect?.value || 'dashscope';
        const dashscopeGroup = document.getElementById('dashscopeGroup');
        const localModelGroup = document.getElementById('localModelGroup');
        
        if (provider === 'dashscope') {
            if (dashscopeGroup) dashscopeGroup.style.display = 'block';
            if (localModelGroup) localModelGroup.style.display = 'none';
        } else {
            if (dashscopeGroup) dashscopeGroup.style.display = 'none';
            if (localModelGroup) localModelGroup.style.display = 'block';
        }
    }
    
    function loadSettings() {
        const saved = localStorage.getItem('qwen_agent_settings');
        if (saved) {
            try {
                settings = { ...settings, ...JSON.parse(saved) };
                applySettings();
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        }
    }
    
    function applySettings() {
        document.getElementById('languageSelect').value = settings.language;
        document.getElementById('timezoneSelect').value = settings.timezone;
        document.getElementById('notificationsToggle').checked = settings.notifications;
        document.getElementById('soundToggle').checked = settings.sound;
        
        if (modelProviderSelect) {
            modelProviderSelect.value = settings.modelProvider;
        }
        
        if (document.getElementById('dashscopeApiKey')) {
            document.getElementById('dashscopeApiKey').value = settings.dashscopeApiKey || '';
        }
        
        if (document.getElementById('dashscopeModelSelect')) {
            document.getElementById('dashscopeModelSelect').value = settings.dashscopeModel;
        }
        
        if (document.getElementById('localApiBase')) {
            document.getElementById('localApiBase').value = settings.localApiBase || 'http://localhost:8001/v1';
        }
        
        if (document.getElementById('localModelName')) {
            document.getElementById('localModelName').value = settings.localModelName || 'Qwen/Qwen2.5-7B-Instruct';
        }
        
        if (document.getElementById('localApiKey')) {
            document.getElementById('localApiKey').value = settings.localApiKey || '';
        }
        
        if (tempSlider) {
            tempSlider.value = settings.temperature;
        }
        
        if (tempValue) {
            tempValue.textContent = settings.temperature;
        }
        
        if (maxTokensSlider) {
            maxTokensSlider.value = settings.maxTokens;
        }
        
        if (maxTokensValue) {
            maxTokensValue.textContent = settings.maxTokens;
        }
        
        document.getElementById('fontSizeSelect').value = settings.fontSize;
        document.getElementById('compactToggle').checked = settings.compactMode;
        document.getElementById('autoSaveToggle').checked = settings.autoSave;
        
        if (document.getElementById('proxySetting')) {
            document.getElementById('proxySetting').value = settings.proxy || '';
        }
        
        themeOptions.forEach(opt => {
            opt.classList.toggle('active', opt.dataset.theme === settings.theme);
        });
        
        applyTheme(settings.theme);
        updateModelConfigUI();
    }
    
    function applyTheme(theme) {
        if (theme === 'light') {
            document.documentElement.style.setProperty('--bg-primary', '#f8fafc');
            document.documentElement.style.setProperty('--bg-secondary', '#ffffff');
            document.documentElement.style.setProperty('--bg-card', '#ffffff');
            document.documentElement.style.setProperty('--text-primary', '#1e293b');
            document.documentElement.style.setProperty('--text-secondary', '#64748b');
            document.documentElement.style.setProperty('--border-color', '#e2e8f0');
        } else if (theme === 'blue') {
            document.documentElement.style.setProperty('--bg-primary', '#0c1929');
            document.documentElement.style.setProperty('--bg-secondary', '#1e3a5f');
            document.documentElement.style.setProperty('--bg-card', '#1a2d47');
            document.documentElement.style.setProperty('--primary-color', '#3b82f6');
            document.documentElement.style.setProperty('--primary-dark', '#2563eb');
        } else if (theme === 'purple') {
            document.documentElement.style.setProperty('--bg-primary', '#1a0f2e');
            document.documentElement.style.setProperty('--bg-secondary', '#2d1b4e');
            document.documentElement.style.setProperty('--bg-card', '#271547');
            document.documentElement.style.setProperty('--primary-color', '#8b5cf6');
            document.documentElement.style.setProperty('--primary-dark', '#7c3aed');
        } else {
            document.documentElement.style.setProperty('--bg-primary', '#0f0f1a');
            document.documentElement.style.setProperty('--bg-secondary', '#1a1a2e');
            document.documentElement.style.setProperty('--bg-card', '#1e1e3a');
            document.documentElement.style.setProperty('--text-primary', '#f1f5f9');
            document.documentElement.style.setProperty('--text-secondary', '#94a3b8');
            document.documentElement.style.setProperty('--border-color', '#2d2d50');
            document.documentElement.style.setProperty('--primary-color', '#6366f1');
            document.documentElement.style.setProperty('--primary-dark', '#4f46e5');
        }
    }
    
    settingsNavItems.forEach((item, index) => {
        item.addEventListener('click', () => {
            settingsNavItems.forEach(i => i.classList.remove('active'));
            settingsSections.forEach(s => s.classList.remove('active'));
            item.classList.add('active');
            const sectionId = item.dataset.section + 'Section';
            document.getElementById(sectionId)?.classList.add('active');
        });
    });
    
    modelProviderSelect?.addEventListener('change', updateModelConfigUI);
    
    tempSlider?.addEventListener('input', () => {
        tempValue.textContent = tempSlider.value;
        settings.temperature = parseFloat(tempSlider.value);
    });
    
    maxTokensSlider?.addEventListener('input', () => {
        maxTokensValue.textContent = maxTokensSlider.value;
        settings.maxTokens = parseInt(maxTokensSlider.value);
    });
    
    themeOptions.forEach(option => {
        option.addEventListener('click', () => {
            themeOptions.forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
            settings.theme = option.dataset.theme;
            applyTheme(settings.theme);
        });
    });
    
    saveSettingsBtn?.addEventListener('click', async () => {
        settings.language = document.getElementById('languageSelect').value;
        settings.timezone = document.getElementById('timezoneSelect').value;
        settings.notifications = document.getElementById('notificationsToggle').checked;
        settings.sound = document.getElementById('soundToggle').checked;
        settings.modelProvider = modelProviderSelect.value;
        
        if (document.getElementById('dashscopeApiKey')) {
            settings.dashscopeApiKey = document.getElementById('dashscopeApiKey').value;
        }
        
        if (document.getElementById('dashscopeModelSelect')) {
            settings.dashscopeModel = document.getElementById('dashscopeModelSelect').value;
        }
        
        if (document.getElementById('localApiBase')) {
            settings.localApiBase = document.getElementById('localApiBase').value;
        }
        
        if (document.getElementById('localModelName')) {
            settings.localModelName = document.getElementById('localModelName').value;
        }
        
        if (document.getElementById('localApiKey')) {
            settings.localApiKey = document.getElementById('localApiKey').value;
        }
        
        settings.fontSize = document.getElementById('fontSizeSelect').value;
        settings.compactMode = document.getElementById('compactToggle').checked;
        settings.autoSave = document.getElementById('autoSaveToggle').checked;
        
        if (document.getElementById('proxySetting')) {
            settings.proxy = document.getElementById('proxySetting').value;
        }
        
        localStorage.setItem('qwen_agent_settings', JSON.stringify(settings));
        
        try {
            const response = await fetch('/api/model/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: settings.modelProvider,
                    config: settings.modelProvider === 'dashscope' ? {
                        api_key: settings.dashscopeApiKey,
                        model: settings.dashscopeModel
                    } : {
                        base_url: settings.localApiBase,
                        model: settings.localModelName,
                        api_key: settings.localApiKey
                    }
                })
            });
            
            if (response.ok) {
                showToast('设置已保存并同步到后端！');
            } else {
                showToast('设置已保存本地！', 'warning');
            }
        } catch (e) {
            console.error('Failed to sync config:', e);
            showToast('设置已保存本地！', 'warning');
        }
    });
    
    resetSettingsBtn?.addEventListener('click', () => {
        if (confirm('确定要重置所有设置吗？')) {
            localStorage.removeItem('qwen_agent_settings');
            settings = {
                language: 'zh-CN',
                timezone: 'Asia/Shanghai',
                notifications: true,
                sound: false,
                modelProvider: 'dashscope',
                dashscopeApiKey: '',
                dashscopeModel: 'qwen-max',
                localApiBase: 'http://localhost:8001/v1',
                localModelName: 'Qwen/Qwen2.5-7B-Instruct',
                localApiKey: '',
                temperature: 0.7,
                maxTokens: 2000,
                theme: 'dark',
                fontSize: 'medium',
                compactMode: false,
                autoSave: true,
                proxy: ''
            };
            applySettings();
            showToast('设置已重置！');
        }
    });
    
    clearCacheBtn?.addEventListener('click', () => {
        if (confirm('确定要清除缓存吗？')) {
            localStorage.removeItem('qwen_agent_cache');
            showToast('缓存已清除！');
        }
    });
    
    exportDataBtn?.addEventListener('click', () => {
        const exportData = {
            settings: settings,
            exportDate: new Date().toISOString(),
            version: '4.0.0'
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'docucode-agent-settings.json';
        a.click();
        URL.revokeObjectURL(url);
        showToast('数据已导出！');
    });
    
    loadSettings();
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.settings-nav')) {
        initSettings();
    }
});
