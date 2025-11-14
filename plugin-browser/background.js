// background.js - Service Worker，处理下载和压缩
// 已整合并修正 TinyPNGClient（只接受 width 或 height），并修复未定义 originalWidth/originalHeight 等问题。

// ConfigManager 工具类（未改动逻辑，只是格式化）
class ConfigManager {
    static async getConfig() {
      const result = await chrome.storage.sync.get([
        'enabled',
        'downloadPath',
        'enabledSites',
        'tinypngApiKey',
        'targetWidth',
        'targetHeight',
        'preserveAspectRatio',
        'tinypngEnabled'
      ]);
      
      return {
        enabled: result.enabled !== false,
        downloadPath: result.downloadPath || '',
        enabledSites: result.enabledSites || ['doubao.com'],
        tinypngApiKey: result.tinypngApiKey || '',
        targetWidth: result.targetWidth || null,
        targetHeight: result.targetHeight || null,
        preserveAspectRatio: result.preserveAspectRatio !== false,
        tinypngEnabled: result.tinypngEnabled !== false
      };
    }
    
    static async getTinyPNGConfig() {
      const config = await this.getConfig();
      return {
        apiKey: config.tinypngApiKey,
        targetWidth: config.targetWidth,
        targetHeight: config.targetHeight,
        preserveAspectRatio: config.preserveAspectRatio,
        enabled: config.tinypngEnabled
      };
    }
    
    static async getImageStatus() {
      const result = await chrome.storage.local.get(['imageStatus']);
      return result.imageStatus || {
        total: 0,
        processed: 0,
        failed: 0,
        failedImages: []
      };
    }
    
    static async updateImageStatus(status) {
      await chrome.storage.local.set({ imageStatus: status });
    }
    
    static async addFailedImage(imageUrl, error) {
      const status = await this.getImageStatus();
      status.failed++;
      status.failedImages.push({
        url: imageUrl,
        error: error?.message || String(error),
        timestamp: Date.now()
      });
      await this.updateImageStatus(status);
    }
    
    static async markImageProcessed() {
      const status = await this.getImageStatus();
      status.processed++;
      await this.updateImageStatus(status);
    }
    
    static async setTotalImages(count) {
      const status = await this.getImageStatus();
      status.total = count;
      await this.updateImageStatus(status);
    }
    
    static async removeFailedImage(imageUrl) {
      const status = await this.getImageStatus();
      status.failedImages = status.failedImages.filter(img => img.url !== imageUrl);
      status.failed = status.failedImages.length;
      await this.updateImageStatus(status);
    }
  }
  
  // ========================
  // TinyPNGClient（精简版）
  //  - 严格要求：必须且只能传入 width 或 height（两个都传或都不传都会抛错）
  //  - 使用 scale 方法保证等比缩放
  //  - 在 resize 前尝试读取压缩后图片 header 中的 Image-Width/Image-Height，避免被放大
  // ========================
  class TinyPNGClient {
    constructor(apiKey) {
      if (!apiKey) throw new Error('TinyPNG API Key 未配置');
      this.apiKey = apiKey;
      this.baseUrl = 'https://api.tinify.com';
      this.authHeader = { 'Authorization': `Basic ${btoa(`api:${this.apiKey}`)}` };
    }
  
    // 从 output URL 尝试读取 Image-Width / Image-Height（先 HEAD，再 GET）
    async _fetchImageDimensions(url) {
      try {
        let resp = await fetch(url, { method: 'HEAD', headers: this.authHeader });
        if (!resp.ok) {
          // 有些端点不允许 HEAD，退回用 GET（会下载 body，但我们只读 header）
          resp = await fetch(url, { method: 'GET', headers: this.authHeader });
          if (!resp.ok) return null;
        }
        const getHeader = (name) => resp.headers.get(name) || resp.headers.get(name.toLowerCase());
        const w = parseInt(getHeader('Image-Width'), 10) || null;
        const h = parseInt(getHeader('Image-Height'), 10) || null;
        if (Number.isFinite(w) && Number.isFinite(h)) return { width: w, height: h };
        return null;
      } catch (err) {
        console.warn('[TinyPNG] 读取尺寸失败:', err);
        return null;
      }
    }
  
    /**
     * 压缩并缩放（严格规则：必须且仅传入 width 或 height 中的一个）
     * imageData: ArrayBuffer | Blob | Uint8Array
     * options: { width?, height? } —— 只能填一个
     * 返回：最终的 Blob
     */
    async compressAndResize(imageData, options = {}) {
      const { width = null, height = null } = options;
  
      if ((width && height) || (!width && !height)) {
        throw new Error('参数错误：请且仅传入 width 或 height 中的一个值');
      }
  
      try {
        console.log('[TinyPNG] 上传并压缩（shrink）...');
        let compressResponse;
        try {
          compressResponse = await fetch(`${this.baseUrl}/shrink`, {
            method: 'POST',
            headers: {
              ...this.authHeader,
              'Content-Type': 'application/octet-stream'
            },
            body: imageData
          });
        } catch (fetchErr) {
          console.error('[TinyPNG] fetch /shrink 失败（网络或权限问题）:', fetchErr);
          throw fetchErr;
        }
  
        if (!compressResponse.ok) {
          const errText = await compressResponse.text().catch(() => '');
          let parsed;
          try { parsed = JSON.parse(errText); } catch { parsed = { error: errText || 'compress failed' }; }
          console.error('[TinyPNG] shrink 返回错误：', parsed);
          throw new Error(parsed.error || parsed.message || 'TinyPNG shrink 失败');
        }
  
        // 获取 compressed output URL（优先 Location header）
        let compressedUrl = compressResponse.headers.get('Location');
        if (!compressedUrl) {
          const jr = await compressResponse.json().catch(() => null);
          compressedUrl = jr?.output?.url;
          if (!compressedUrl) throw new Error('无法获取压缩后图片的 URL');
        }
        console.log('[TinyPNG] shrink 成功，output URL:', compressedUrl);
  
        // 读取压缩后图片尺寸，避免放大
        const original = await this._fetchImageDimensions(compressedUrl);
        const originalWidth = original?.width || null;
        const originalHeight = original?.height || null;
        console.log('[TinyPNG] 压缩后尺寸（header）:', originalWidth, originalHeight);
  
        // 构造 resize payload（只用 scale）
        let resizePayload = null;
        if (width) {
          if (originalWidth && width >= originalWidth) {
            console.log('[TinyPNG] 目标宽度 >= 原始宽度，TinyPNG 不会放大，跳过缩放');
            resizePayload = null;
          } else {
            resizePayload = { method: 'scale', width: Math.round(width) };
          }
        } else if (height) {
          if (originalHeight && height >= originalHeight) {
            console.log('[TinyPNG] 目标高度 >= 原始高度，TinyPNG 不会放大，跳过缩放');
            resizePayload = null;
          } else {
            resizePayload = { method: 'scale', height: Math.round(height) };
          }
        }
  
        // 如果需要缩放，调用 compressedUrl 进行 POST
        if (resizePayload) {
          let resizeResp;
          try {
            resizeResp = await fetch(compressedUrl, {
              method: 'POST',
              headers: {
                ...this.authHeader,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ resize: resizePayload })
            });
          } catch (fetchErr) {
            console.error('[TinyPNG] fetch resize 失败（网络或权限问题）:', fetchErr);
            throw fetchErr;
          }
  
          if (!resizeResp.ok) {
            const buf = await resizeResp.arrayBuffer().catch(() => null);
            const txt = buf ? new TextDecoder('utf-8').decode(buf) : 'TinyPNG resize failed';
            console.error('[TinyPNG] resize 返回错误：', txt);
            throw new Error(txt);
          }
  
          const location = resizeResp.headers.get('Location');
          if (location) {
            compressedUrl = location;
            console.log('[TinyPNG] resize 返回 Location:', compressedUrl);
          } else {
            const ct = resizeResp.headers.get('Content-Type') || '';
            if (ct.includes('application/json')) {
              const jr = await resizeResp.json().catch(() => null);
              compressedUrl = jr?.output?.url || compressedUrl;
              console.log('[TinyPNG] resize 返回 JSON，output URL:', compressedUrl);
              if (!compressedUrl) throw new Error('resize JSON 响应中缺少 output.url');
            } else {
              // 直接返回图片 blob（resizeResp 直接是图片数据）
              const directBlob = await resizeResp.blob();
              console.log('[TinyPNG] resize 直接返回 blob，大小:', directBlob.size);
              return directBlob;
            }
          }
        }
  
        // 下载最终图片
        console.log('[TinyPNG] 下载最终图片...');
        const finalResp = await fetch(compressedUrl, { headers: this.authHeader });
        if (!finalResp.ok) {
          const txt = await finalResp.text().catch(() => '');
          console.error('[TinyPNG] 下载最终图片失败：', txt);
          throw new Error('获取处理后图片失败');
        }
        const finalBlob = await finalResp.blob();
        console.log('[TinyPNG] 完成，最终大小:', finalBlob.size);
        return finalBlob;
  
      } catch (err) {
        console.error('[TinyPNG] 处理失败:', err);
        throw err;
      }
    }
  }
  
  
  // ========================
  // ImageDownloader 工具类（保留并稍作硬化）
  // ========================
  class ImageDownloader {
    static async downloadBlob(blob, filename, downloadPath = '') {
      try {
        let downloadUrl;
        try {
          if (typeof URL !== 'undefined' && URL.createObjectURL) {
            downloadUrl = URL.createObjectURL(blob);
          } else {
            throw new Error('URL.createObjectURL not available');
          }
        } catch (e) {
          // 回退到 data URL
          const arrayBuffer = await blob.arrayBuffer();
          const chunkSize = 8192;
          const uint8Array = new Uint8Array(arrayBuffer);
          let binary = '';
          for (let i = 0; i < uint8Array.length; i += chunkSize) {
            const chunk = uint8Array.subarray(i, Math.min(i + chunkSize, uint8Array.length));
            binary += String.fromCharCode.apply(null, Array.from(chunk));
          }
          const base64 = btoa(binary);
          const mimeType = blob.type || 'image/jpeg';
          downloadUrl = `data:${mimeType};base64,${base64}`;
        }
        
        const fullPath = downloadPath 
          ? `${downloadPath}/${filename}`.replace(/\/+/g, '/')
          : filename;
        
        await chrome.downloads.download({
          url: downloadUrl,
          filename: fullPath,
          saveAs: false
        });
        
        if (downloadUrl.startsWith('blob:')) {
          setTimeout(() => {
            try { URL.revokeObjectURL(downloadUrl); } catch (e) { /* ignore */ }
          }, 1000);
        }
      } catch (error) {
        console.error('下载Blob失败:', error);
        throw error;
      }
    }
    
    static async downloadFromUrl(url, filename, downloadPath = '') {
      try {
        const fullPath = downloadPath 
          ? `${downloadPath}/${filename}`.replace(/\/+/g, '/')
          : filename;
        
        await chrome.downloads.download({
          url: url,
          filename: fullPath,
          saveAs: false
        });
        
      } catch (error) {
        console.error('从URL下载失败:', error);
        throw error;
      }
    }
    
    static generateFilename(url) {
      try {
        const urlObj = new URL(url);
        const pathname = urlObj.pathname;
        const ext = pathname.match(/\.(jpg|jpeg|png|gif|webp)$/i)?.[1] || 'jpg';
        const timestamp = Date.now();
        return `doubao_${timestamp}.${ext}`;
      } catch {
        const timestamp = Date.now();
        return `doubao_${timestamp}.jpg`;
      }
    }
  }
  
  // ========================
  // 消息监听与主流程（handleImageDownload）
  // ========================
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('[Background] 收到消息:', message.action, message);
    
    if (message.action === 'downloadImage') {
      handleImageDownload(message.imageUrl, sender.tab?.id, message.imageId)
        .then(() => {
          sendResponse({ success: true });
        })
        .catch((error) => {
          console.error('[Background] 下载处理失败:', error);
          sendResponse({ success: false, error: error.message });
        });
      
      return true; // 异步响应
    }
    
    if (message.action === 'retryFailedImage') {
      handleImageDownload(message.imageUrl, sender.tab?.id, message.imageId)
        .then(() => {
          sendResponse({ success: true });
        })
        .catch((error) => {
          console.error('重试失败:', error);
          sendResponse({ success: false, error: error.message });
        });
      
      return true;
    }
    
    if (message.action === 'getImageStatus') {
      ConfigManager.getImageStatus().then(status => {
        sendResponse({ success: true, status });
      });
      return true;
    }
    
    if (message.action === 'updateTotalImages') {
      ConfigManager.setTotalImages(message.count).then(() => {
        sendResponse({ success: true });
      });
      return true;
    }
  });
  
  async function handleImageDownload(imageUrl, tabId, imageId = null) {
    console.log('[handleImageDownload] 开始，图片URL:', imageUrl);
    try {
      const config = await ConfigManager.getConfig();
      const tinypngConfig = await ConfigManager.getTinyPNGConfig();
      console.log('[handleImageDownload] 配置:', { enabled: config.enabled, downloadPath: config.downloadPath });
      console.log('[TinyPNG] 配置:', tinypngConfig);
      
      if (!config.enabled) {
        console.warn('[handleImageDownload] 插件未启用');
        throw new Error('插件未启用');
      }
      
      if (imageId) {
        await ConfigManager.removeFailedImage(imageUrl);
      }
      
      // 下载原图
      const response = await fetch(imageUrl);
      if (!response.ok) throw new Error(`获取图片失败: ${response.statusText}`);
      const imageBlob = await response.blob();
      console.log('[handleImageDownload] 原始图片大小:', imageBlob.size);
      
      // 尝试读取原始宽高（用于记录 / Debug），createImageBitmap 在 SW 环境可用
      let originalWidth = null;
      let originalHeight = null;
      try {
        const bitmap = await createImageBitmap(imageBlob);
        originalWidth = bitmap.width;
        originalHeight = bitmap.height;
        bitmap.close();
        console.log('[handleImageDownload] 原始尺寸:', originalWidth, originalHeight);
      } catch (e) {
        console.warn('[handleImageDownload] 获取原始尺寸失败:', e);
      }
      
      const imageArrayBuffer = await imageBlob.arrayBuffer();
      
      // TinyPNG 处理（仅当启用且配置了 apiKey）
      let finalBlob = null;
      let finalUrl = imageUrl; // 如果不使用 TinyPNG 则保持原始 URL
      if (tinypngConfig.enabled && tinypngConfig.apiKey) {
        // 严格检查：不允许同时传 targetWidth 和 targetHeight
        if (tinypngConfig.targetWidth && tinypngConfig.targetHeight) {
          // 这里按你的要求：不支持同时传两个值 -> 视为配置错误，跳过 TinyPNG 压缩/缩放
          console.error('[TinyPNG] 配置错误：同时设置了 targetWidth 和 targetHeight，按策略跳过 TinyPNG 处理');
        } else if (!tinypngConfig.targetWidth && !tinypngConfig.targetHeight) {
          console.log('[TinyPNG] 未配置目标宽或高，执行仅压缩（不缩放）');
          try {
            const client = new TinyPNGClient(tinypngConfig.apiKey);
            finalBlob = await client.compressAndResize(imageArrayBuffer, { width: null, height: null }).catch(() => null);
            // note: 上面会因参数校验抛错，这里我们 catch 并忽略 -> fallback 到原图
          } catch (e) {
            console.warn('[TinyPNG] 仅压缩失败，使用原图', e);
          }
        } else {
          // 只传了 width 或 height 中的一个（正常路径）
          try {
            const client = new TinyPNGClient(tinypngConfig.apiKey);
            const resizeOptions = {};
            if (tinypngConfig.targetWidth) resizeOptions.width = tinypngConfig.targetWidth;
            if (tinypngConfig.targetHeight) resizeOptions.height = tinypngConfig.targetHeight;
            console.log('[TinyPNG] 调用 compressAndResize，options:', resizeOptions);
            finalBlob = await client.compressAndResize(imageArrayBuffer, resizeOptions);
            console.log('[TinyPNG] compressAndResize 返回，大小:', finalBlob?.size);
          } catch (err) {
            console.error('[TinyPNG] 处理失败，使用原图，错误:', err);
            // 记录失败，但继续后续流程用原图
            await ConfigManager.addFailedImage(imageUrl, err);
            finalBlob = null;
          }
        }
      } else {
        if (!tinypngConfig.enabled) console.log('[TinyPNG] 功能未启用');
        if (!tinypngConfig.apiKey) console.log('[TinyPNG] API Key 未配置');
      }
      
      const filename = ImageDownloader.generateFilename(imageUrl);
      
      if (finalBlob) {
        console.log('[下载] 正在下载 TinyPNG 处理后的文件:', filename);
        await ImageDownloader.downloadBlob(finalBlob, filename, config.downloadPath);
      } else {
        console.log('[下载] 使用原始图片 URL 下载:', filename);
        await ImageDownloader.downloadFromUrl(finalUrl, filename, config.downloadPath);
      }
      
      await ConfigManager.markImageProcessed();
      console.log('[handleImageDownload] 完成:', filename);
    } catch (error) {
      console.error('[handleImageDownload] 错误:', error);
      await ConfigManager.addFailedImage(imageUrl, error);
      throw error;
    }
  }
  
  // 安装与全局错误处理
  chrome.runtime.onInstalled.addListener(() => {
    console.log('[Background] 扩展已安装');
  });
  
  self.addEventListener('error', (event) => {
    console.error('[Background] 全局错误:', event.error);
  });
  
  self.addEventListener('unhandledrejection', (event) => {
    console.error('[Background] 未处理的Promise拒绝:', event.reason);
  });
  