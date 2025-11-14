// popup.js - 插件弹窗逻辑

document.addEventListener('DOMContentLoaded', async () => {
  const enabledCheckbox = document.getElementById('plugin-enabled');
  const statusText = document.getElementById('status-text');
  const openSettingsBtn = document.getElementById('open-settings');
  const refreshStatsBtn = document.getElementById('refresh-stats');
  const statTotal = document.getElementById('stat-total');
  const statProcessed = document.getElementById('stat-processed');
  const statFailed = document.getElementById('stat-failed');
  const statRemaining = document.getElementById('stat-remaining');
  const failedImagesSection = document.getElementById('failed-images-section');
  const failedImagesList = document.getElementById('failed-images-list');
  
  // 加载插件状态
  const loadStatus = async () => {
    const result = await chrome.storage.sync.get(['enabled']);
    const enabled = result.enabled !== false; // 默认启用
    enabledCheckbox.checked = enabled;
    statusText.textContent = enabled ? '已启用' : '已禁用';
    statusText.className = `status-text ${enabled ? 'enabled' : 'disabled'}`;
  };
  
  // 加载图片处理状态
  const loadImageStatus = async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, { action: 'getImageStatus' }, (response) => {
          if (chrome.runtime.lastError) {
            console.error('获取状态失败:', chrome.runtime.lastError);
            return;
          }
          
          if (response && response.success) {
            updateStatsDisplay(response.status);
          }
        });
      } else {
        // 如果无法获取tab，直接从storage读取
        const result = await chrome.storage.local.get(['imageStatus']);
        const status = result.imageStatus || {
          total: 0,
          processed: 0,
          failed: 0,
          failedImages: []
        };
        updateStatsDisplay(status);
      }
    } catch (error) {
      console.error('加载状态失败:', error);
    }
  };
  
  // 更新状态显示
  const updateStatsDisplay = (status) => {
    statTotal.textContent = status.total || 0;
    statProcessed.textContent = status.processed || 0;
    statFailed.textContent = status.failed || 0;
    const remaining = Math.max(0, (status.total || 0) - (status.processed || 0) - (status.failed || 0));
    statRemaining.textContent = remaining;
    
    // 显示失败的图片列表
    if (status.failedImages && status.failedImages.length > 0) {
      failedImagesSection.style.display = 'block';
      failedImagesList.innerHTML = '';
      
      status.failedImages.forEach((failedImage, index) => {
        const item = document.createElement('div');
        item.className = 'failed-image-item';
        item.innerHTML = `
          <div class="failed-image-info">
            <div class="failed-image-url">图片 ${index + 1}</div>
            <div class="failed-image-error">${failedImage.error || '处理失败'}</div>
          </div>
          <button class="btn-retry" data-url="${failedImage.url}">重试</button>
        `;
        
        const retryBtn = item.querySelector('.btn-retry');
        retryBtn.addEventListener('click', async () => {
          retryBtn.disabled = true;
          retryBtn.textContent = '处理中...';
          
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (tab?.id) {
            chrome.tabs.sendMessage(tab.id, {
              action: 'retryFailedImage',
              imageUrl: failedImage.url
            }, (response) => {
              if (response && response.success) {
                loadImageStatus(); // 刷新状态
              } else {
                retryBtn.disabled = false;
                retryBtn.textContent = '重试';
                alert('重试失败: ' + (response?.error || '未知错误'));
              }
            });
          }
        });
        
        failedImagesList.appendChild(item);
      });
    } else {
      failedImagesSection.style.display = 'none';
    }
  };
  
  // 切换插件状态
  enabledCheckbox.addEventListener('change', async (e) => {
    const enabled = e.target.checked;
    await chrome.storage.sync.set({ enabled });
    statusText.textContent = enabled ? '已启用' : '已禁用';
    statusText.className = `status-text ${enabled ? 'enabled' : 'disabled'}`;
    
    // 通知content script更新状态
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      chrome.tabs.sendMessage(tab.id, { action: 'updateEnabled', enabled });
    }
  });
  
  // 打开设置页面
  openSettingsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
  
  // 刷新状态
  refreshStatsBtn.addEventListener('click', () => {
    loadImageStatus();
  });
  
  // 初始化
  loadStatus();
  loadImageStatus();
  
  // 定期刷新状态
  setInterval(loadImageStatus, 2000);
});

