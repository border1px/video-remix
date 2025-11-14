// utils/image-downloader.js - 图片下载工具类

class ImageDownloader {
  /**
   * 从URL下载图片
   * @param {string} imageUrl - 图片URL
   * @param {string} filename - 文件名
   * @param {string} downloadPath - 保存路径（相对下载目录）
   * @returns {Promise<void>}
   */
  static async downloadImage(imageUrl, filename, downloadPath = '') {
    try {
      // 获取图片数据
      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      
      // 创建下载URL
      const url = URL.createObjectURL(blob);
      
      // 构建完整路径
      const fullPath = downloadPath 
        ? `${downloadPath}/${filename}`.replace(/\/+/g, '/')
        : filename;
      
      // 使用Chrome下载API
      await chrome.downloads.download({
        url: url,
        filename: fullPath,
        saveAs: false
      });
      
      // 清理URL对象
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      
    } catch (error) {
      console.error('下载图片失败:', error);
      throw error;
    }
  }
  
  /**
   * 从Blob下载图片
   * @param {Blob} blob - 图片Blob
   * @param {string} filename - 文件名
   * @param {string} downloadPath - 保存路径
   * @returns {Promise<void>}
   */
  static async downloadBlob(blob, filename, downloadPath = '') {
    try {
      const url = URL.createObjectURL(blob);
      
      const fullPath = downloadPath 
        ? `${downloadPath}/${filename}`.replace(/\/+/g, '/')
        : filename;
      
      await chrome.downloads.download({
        url: url,
        filename: fullPath,
        saveAs: false
      });
      
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      
    } catch (error) {
      console.error('下载Blob失败:', error);
      throw error;
    }
  }
  
  /**
   * 生成文件名
   * @param {string} url - 图片URL
   * @returns {string} 文件名
   */
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


