// utils/config.js - 配置管理工具

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
    
    const targetWidth = result.targetWidth === undefined
      ? 1920
      : (result.targetWidth === null ? null : result.targetWidth);
    const targetHeight = result.targetHeight === undefined
      ? 1080
      : (result.targetHeight === null ? null : result.targetHeight);
    
    return {
      enabled: result.enabled !== false, // 默认启用
      downloadPath: result.downloadPath || '',
      enabledSites: result.enabledSites || ['doubao.com'],
      tinypngApiKey: result.tinypngApiKey || '',
      targetWidth,
      targetHeight,
      preserveAspectRatio: result.preserveAspectRatio !== false,
      tinypngEnabled: result.tinypngEnabled !== false // 默认启用
    };
  }
  
  static async isEnabled() {
    const config = await this.getConfig();
    return config.enabled;
  }
  
  static async isSiteEnabled(url) {
    const config = await this.getConfig();
    const hostname = new URL(url).hostname;
    
    return config.enabledSites.some(site => {
      // 支持通配符匹配
      const pattern = site.replace(/\*/g, '.*');
      const regex = new RegExp(`^${pattern}$`, 'i');
      return regex.test(hostname);
    });
  }
  
  static async getTinyPNGConfig() {
    const config = await this.getConfig();
    return {
      apiKey: config.tinypngApiKey,
      targetWidth: config.targetWidth,
      targetHeight: config.targetHeight,
      preserveAspectRatio: config.preserveAspectRatio,
      enabled: config.tinypngEnabled !== false // 默认启用
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
      error: error.message || error,
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

