// content.js - 内容脚本，注入到网页中
// 结合原版通用实现和豆包特定需求

class ImageDownloadInjector {
  constructor() {
    this.enabled = false;
    this.observer = null;
    this.processedImages = new WeakSet();
    this.imageMap = new Map(); // 存储图片URL和对应的按钮
    this.config = {
      enabled: true,
      enabledSites: ['doubao.com'],
      minWidth: 200
    };
    this.init();
  }
  
  async init() {
    console.log('[豆包图片下载器] 初始化开始...');
    
    try {
      // 加载配置
      await this.loadConfig();
      
      // 检查插件是否启用
      if (!this.config.enabled) {
        console.log('[豆包图片下载器] 插件未启用');
        return;
      }
      
      // 检查当前网站是否在生效列表中
      const isSiteEnabled = this.isSiteEnabled(window.location.href);
      console.log('[豆包图片下载器] 当前网站:', window.location.href);
      console.log('[豆包图片下载器] 网站是否生效:', isSiteEnabled);
      
      if (!isSiteEnabled) {
        console.warn('[豆包图片下载器] 当前网站不在生效列表中');
        return;
      }
      
      // 开始监听图片
      console.log('[豆包图片下载器] 开始监听图片...');
      this.startObserving();
      
      // 监听配置变化
      chrome.storage.onChanged.addListener((changes, namespace) => {
        if (namespace === 'sync') {
          this.loadConfig().then(() => {
            if (!this.config.enabled) {
              this.stopObserving();
            } else {
              this.startObserving();
            }
          });
        }
      });
      
      // 监听来自popup的消息
      chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
        if (message.action === 'updateEnabled') {
          this.config.enabled = message.enabled;
          if (this.config.enabled) {
            this.startObserving();
          } else {
            this.stopObserving();
          }
        }
        
        if (message.action === 'getImageStatus') {
          const status = await this.getImageStatus();
          sendResponse({ success: true, status });
          return true;
        }
        
        if (message.action === 'retryFailedImage') {
          const button = this.imageMap.get(message.imageUrl);
          if (button) {
            const img = button._imgElement;
            if (img) {
              await this.handleDownload(img);
              sendResponse({ success: true });
            } else {
              sendResponse({ success: false, error: '未找到图片元素' });
            }
          } else {
            sendResponse({ success: false, error: '未找到对应的按钮' });
          }
          return true;
        }
      });
    } catch (error) {
      console.error('[豆包图片下载器] 初始化失败:', error);
    }
  }
  
  async loadConfig() {
    const result = await chrome.storage.sync.get([
      'enabled',
      'enabledSites',
      'minWidth'
    ]);
    
    this.config = {
      enabled: result.enabled !== false,
      enabledSites: result.enabledSites || ['doubao.com'],
      minWidth: result.minWidth || 200
    };
  }
  
  isSiteEnabled(url) {
    try {
      const hostname = new URL(url).hostname;
      return this.config.enabledSites.some(site => {
        // 支持通配符匹配
        const pattern = site.replace(/\*/g, '.*');
        const regex = new RegExp(`^${pattern}$`, 'i');
        return regex.test(hostname) || hostname.includes(site);
      });
    } catch {
      return false;
    }
  }
  
  startObserving() {
    // 先处理已存在的图片
    this.processExistingImages();
    
    // 使用MutationObserver监听新添加的图片
    this.observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              // 延迟处理，避免干扰页面的DOM操作
              setTimeout(() => {
                this.processImagesInNode(node);
              }, 100);
            }
          });
        }
      });
    });
    
    this.observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    
    console.log('[豆包图片下载器] MutationObserver已启动');
  }
  
  stopObserving() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    
    // 移除所有下载按钮
    document.querySelectorAll('.doubao-download-btn').forEach(btn => {
      const wrapper = btn.closest('.doubao-download-wrapper');
      if (wrapper) {
        wrapper.remove();
      } else {
        btn.remove();
      }
    });
    this.processedImages = new WeakSet();
    this.imageMap.clear();
    console.log('[豆包图片下载器] 已停止监听');
  }
  
  async processExistingImages() {
    console.log('[豆包图片下载器] 开始处理已存在的图片...');
    
    // 延迟初始处理，确保页面完全加载
    setTimeout(() => {
      this.processImagesInNode(document.body);
    }, 500);
  }
  
  processImagesInNode(node) {
    if (!this.config.enabled) return;
    
    // 优先查找豆包的特定容器
    const doubaoContainers = node.querySelectorAll ? 
      node.querySelectorAll('[data-testid="canvas_image_container"]') : [];
    
    if (doubaoContainers.length > 0) {
      console.log('[豆包图片下载器] 找到豆包容器:', doubaoContainers.length);
      Array.from(doubaoContainers).forEach(container => {
        const img = container.querySelector('img[data-testid="in_painting_picture"]') || 
                    container.querySelector('img');
        if (img) {
          this.processImage(img, container);
        }
      });
    } else {
      // 回退到通用图片检测
      const images = node.querySelectorAll ? node.querySelectorAll('img') : [];
      images.forEach(img => this.processImage(img));
    }
  }
  
  processImage(img, container = null) {
    if (this.processedImages.has(img)) return;
    
    // 检查图片是否已经加载完成
    if (img.complete && img.naturalWidth > 0) {
      this.checkAndAddButton(img, container);
    } else {
      // 使用更安全的事件监听方式
      const handleLoad = () => {
        this.checkAndAddButton(img, container);
        img.removeEventListener('load', handleLoad);
        img.removeEventListener('error', handleError);
      };
      const handleError = () => {
        img.removeEventListener('load', handleLoad);
        img.removeEventListener('error', handleError);
      };
      
      img.addEventListener('load', handleLoad, { once: true });
      img.addEventListener('error', handleError, { once: true });
    }
  }
  
  checkAndAddButton(img, container = null) {
    // 检查图片尺寸
    let imageWidth = 0;
    
    if (img.naturalWidth > 0) {
      imageWidth = img.naturalWidth;
    } else if (img.clientWidth > 0) {
      imageWidth = img.clientWidth;
    } else if (img.width > 0) {
      imageWidth = img.width;
    }
    
    // 如果图片尺寸太小，不添加按钮
    if (imageWidth < this.config.minWidth) {
      return;
    }
    
    // 检查图片是否有有效的src
    if (!img.src || img.src.startsWith('data:image/svg+xml')) {
      return;
    }
    
    this.addDownloadButton(img, container);
  }
  
  addDownloadButton(img, container = null) {
    // 确定父容器
    const parent = container || img.parentNode;
    if (!parent) return;
    
    // 确保容器有定位
    const containerStyle = window.getComputedStyle(parent);
    if (containerStyle.position === 'static') {
      parent.style.position = 'relative';
    }
    
    // 检查是否已经有下载按钮
    if (parent.querySelector('.doubao-download-wrapper')) {
      return;
    }
    
    // 创建一个悬浮层
    const wrapper = document.createElement('div');
    wrapper.className = 'doubao-download-wrapper';
    wrapper.style.cssText = `
      position: absolute;
      top: 8px;
      right: 8px;
      z-index: 10000;
      display: none;
    `;
    
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'doubao-download-btn';
    downloadBtn.title = '下载图片';
    downloadBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
      </svg>
    `;
    
    // 保存图片元素引用
    downloadBtn._imgElement = img;
    
    downloadBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      await this.handleDownload(img);
    });
    
    wrapper.appendChild(downloadBtn);
    parent.appendChild(wrapper);
    
    // 鼠标悬停显示按钮
    parent.addEventListener('mouseenter', () => {
      wrapper.style.display = 'block';
    });
    parent.addEventListener('mouseleave', () => {
      wrapper.style.display = 'none';
    });
    
    this.processedImages.add(img);
    this.imageMap.set(img.src, downloadBtn);
    
    console.log('[豆包图片下载器] 为图片添加下载按钮:', img.src.substring(0, 50) + '...');
  }
  
  async handleDownload(img) {
    try {
      const imageUrl = img.src;
      
      // 更新按钮状态
      const button = this.imageMap.get(imageUrl);
      if (button) {
        button.classList.add('loading');
        button.disabled = true;
      }
      
      // 发送下载请求到background
      chrome.runtime.sendMessage({
        action: 'downloadImage',
        imageUrl: imageUrl,
        imageId: null
      }, async (response) => {
        if (button) {
          button.classList.remove('loading');
          button.disabled = false;
        }
        
        if (chrome.runtime.lastError) {
          console.error('[豆包图片下载器] 下载失败:', chrome.runtime.lastError);
          await this.addFailedImage(imageUrl, chrome.runtime.lastError.message);
          if (button) {
            button.classList.add('error');
            setTimeout(() => button.classList.remove('error'), 2000);
          }
          return;
        }
        
        if (response && response.success) {
          console.log('[豆包图片下载器] 下载成功');
          await this.markImageProcessed();
          if (button) {
            button.classList.add('success');
            setTimeout(() => button.classList.remove('success'), 2000);
          }
        } else {
          console.error('[豆包图片下载器] 下载失败:', response?.error);
          await this.addFailedImage(imageUrl, response?.error || '下载失败');
          if (button) {
            button.classList.add('error');
            setTimeout(() => button.classList.remove('error'), 2000);
          }
        }
      });
      
    } catch (error) {
      console.error('[豆包图片下载器] 下载失败:', error);
      await this.addFailedImage(img.src, error.message);
    }
  }
  
  async getImageStatus() {
    const result = await chrome.storage.local.get(['imageStatus']);
    return result.imageStatus || {
      total: 0,
      processed: 0,
      failed: 0,
      failedImages: []
    };
  }
  
  async addFailedImage(imageUrl, error) {
    const status = await this.getImageStatus();
    status.failed++;
    status.failedImages.push({
      url: imageUrl,
      error: error,
      timestamp: Date.now()
    });
    await chrome.storage.local.set({ imageStatus: status });
  }
  
  async markImageProcessed() {
    const status = await this.getImageStatus();
    status.processed++;
    await chrome.storage.local.set({ imageStatus: status });
  }
}

// 初始化
console.log('[豆包图片下载器] Content script 已加载');
console.log('[豆包图片下载器] 当前页面URL:', window.location.href);
console.log('[豆包图片下载器] 文档状态:', document.readyState);

let injectorInstance = null;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('[豆包图片下载器] DOM加载完成，开始初始化');
    injectorInstance = new ImageDownloadInjector();
    window._doubaoInjector = injectorInstance;
  });
} else {
  console.log('[豆包图片下载器] DOM已就绪，立即初始化');
  injectorInstance = new ImageDownloadInjector();
  window._doubaoInjector = injectorInstance;
}

// 添加调试函数
window.debugDoubaoDownloader = async function() {
  console.log('=== 豆包图片下载器调试信息 ===');
  console.log('1. 检查插件状态...');
  const injector = window._doubaoInjector;
  if (!injector) {
    console.error('❌ Injector未初始化');
    return;
  }
  
  console.log('   插件状态:', injector.config.enabled ? '✅ 已启用' : '❌ 已禁用');
  console.log('   网站是否生效:', injector.isSiteEnabled(window.location.href) ? '✅ 是' : '❌ 否');
  console.log('   当前网站:', window.location.href);
  
  console.log('2. 检查图片容器...');
  const containers = document.querySelectorAll('[data-testid="canvas_image_container"]');
  console.log('   找到豆包容器数量:', containers.length);
  
  const allImages = document.querySelectorAll('img');
  console.log('   页面中所有图片数量:', allImages.length);
  
  console.log('3. 检查下载按钮...');
  const buttons = document.querySelectorAll('.doubao-download-btn');
  console.log('   下载按钮数量:', buttons.length);
  
  console.log('4. 检查MutationObserver...');
  if (injector.observer) {
    console.log('   ✅ MutationObserver正在运行');
  } else {
    console.warn('   ⚠️ MutationObserver未运行');
  }
  
  console.log('=== 调试信息结束 ===');
};

console.log('[豆包图片下载器] 提示: 在控制台输入 debugDoubaoDownloader() 可以查看调试信息');
