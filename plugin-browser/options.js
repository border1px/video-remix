// options.js - 设置页面逻辑

const DEFAULT_CONFIG = {
  downloadPath: '',
  enabledSites: ['doubao.com'],
  tinypngEnabled: true,
  tinypngApiKey: '',
  targetWidth: 1080,
  targetHeight: 1920,
  preserveAspectRatio: true
};

document.addEventListener('DOMContentLoaded', async () => {
  const downloadPathInput = document.getElementById('download-path');
  const enabledSitesInput = document.getElementById('enabled-sites');
  const tinypngEnabledInput = document.getElementById('tinypng-enabled');
  const tinypngApiKeyInput = document.getElementById('tinypng-apikey');
  const targetWidthInput = document.getElementById('target-width');
  const targetHeightInput = document.getElementById('target-height');
  const preserveAspectRatioInput = document.getElementById('preserve-aspect-ratio');
  const saveBtn = document.getElementById('save-btn');
  const resetBtn = document.getElementById('reset-btn');
  const messageDiv = document.getElementById('message');
  
  // 加载配置
  const loadConfig = async () => {
    const result = await chrome.storage.sync.get([
      'downloadPath',
      'enabledSites',
      'tinypngEnabled',
      'tinypngApiKey',
      'targetWidth',
      'targetHeight',
      'preserveAspectRatio'
    ]);
    
    downloadPathInput.value = result.downloadPath || DEFAULT_CONFIG.downloadPath;
    enabledSitesInput.value = (result.enabledSites || DEFAULT_CONFIG.enabledSites).join('\n');
    tinypngEnabledInput.checked = result.tinypngEnabled !== false;
    tinypngApiKeyInput.value = result.tinypngApiKey || DEFAULT_CONFIG.tinypngApiKey;
    targetWidthInput.value = (result.targetWidth === null || result.targetWidth === undefined)
      ? DEFAULT_CONFIG.targetWidth
      : result.targetWidth;
    targetHeightInput.value = (result.targetHeight === null || result.targetHeight === undefined)
      ? ''
      : result.targetHeight;
    preserveAspectRatioInput.checked = result.preserveAspectRatio !== false;
  };
  
  // 保存配置
  const saveConfig = async () => {
    const enabledSites = enabledSitesInput.value
      .split('\n')
      .map(s => s.trim())
      .filter(s => s.length > 0);
    
    if (enabledSites.length === 0) {
      showMessage('请至少配置一个生效网站', 'error');
      return;
    }
    
    const config = {
      downloadPath: downloadPathInput.value.trim(),
      enabledSites,
      tinypngEnabled: tinypngEnabledInput.checked,
      tinypngApiKey: tinypngApiKeyInput.value.trim(),
      targetWidth: (() => {
        const value = parseInt(targetWidthInput.value, 10);
        if (Number.isNaN(value)) {
          return null;
        }
        return value;
      })(),
      targetHeight: (() => {
        const value = parseInt(targetHeightInput.value, 10);
        if (Number.isNaN(value)) {
          return null;
        }
        return value;
      })(),
      preserveAspectRatio: preserveAspectRatioInput.checked
    };
    
    await chrome.storage.sync.set(config);
    showMessage('设置已保存', 'success');
  };
  
  // 重置配置
  const resetConfig = async () => {
    if (confirm('确定要重置所有设置为默认值吗？')) {
      await chrome.storage.sync.set(DEFAULT_CONFIG);
      await loadConfig();
      showMessage('已重置为默认设置', 'success');
    }
  };
  
  // 显示消息
  const showMessage = (text, type = 'info') => {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
      messageDiv.style.display = 'none';
    }, 3000);
  };
  
  // 事件监听
  saveBtn.addEventListener('click', saveConfig);
  resetBtn.addEventListener('click', resetConfig);
  
  // 初始化
  loadConfig();
});

