// utils/tinypng.js - TinyPNG API 工具类

class TinyPNGClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'https://api.tinify.com';
  }
  
  /**
   * 压缩并调整图片大小
   * @param {ArrayBuffer} imageData - 图片数据
   * @param {Object} options - 选项 {width, height, preserveAspectRatio}
   * @returns {Promise<Blob>} 处理后的图片Blob
   */
  async compressAndResize(imageData, options = {}) {
    if (!this.apiKey) {
      throw new Error('TinyPNG API Key 未配置');
    }
    
    const { width, height, preserveAspectRatio = true } = options;
    
    try {
      // 第一步：上传并压缩图片
      const compressResponse = await fetch(`${this.baseUrl}/shrink`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${btoa(`api:${this.apiKey}`)}`
        },
        body: imageData
      });
      
      if (!compressResponse.ok) {
        const error = await compressResponse.json();
        throw new Error(error.error || '压缩失败');
      }
      
      const compressResult = await compressResponse.json();
      const outputUrl = compressResult.output.url;
      
      // 第二步：调整大小（如果需要）
      if (width || height) {
        // 使用TinyPNG的resize API
        const resizeOptions = {};
        if (width) resizeOptions.width = width;
        if (height) resizeOptions.height = height;
        resizeOptions.method = preserveAspectRatio ? 'fit' : 'scale';
        
        const resizeResponse = await fetch(outputUrl, {
          method: 'POST',
          headers: {
            'Authorization': `Basic ${btoa(`api:${this.apiKey}`)}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            resize: resizeOptions
          })
        });
        
        if (!resizeResponse.ok) {
          const error = await resizeResponse.json();
          throw new Error(error.error || '调整大小失败');
        }
        
        const resizeResult = await resizeResponse.json();
        const finalUrl = resizeResult.output.url;
        
        // 下载处理后的图片
        const finalResponse = await fetch(finalUrl, {
          headers: {
            'Authorization': `Basic ${btoa(`api:${this.apiKey}`)}`
          }
        });
        
        if (!finalResponse.ok) {
          throw new Error('获取处理后的图片失败');
        }
        
        return await finalResponse.blob();
      }
      
      // 如果没有指定尺寸，只返回压缩后的图片
      const finalResponse = await fetch(outputUrl, {
        headers: {
          'Authorization': `Basic ${btoa(`api:${this.apiKey}`)}`
        }
      });
      
      return await finalResponse.blob();
      
    } catch (error) {
      console.error('TinyPNG处理失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取图片信息（用于计算宽高比）
   * @param {Blob} imageBlob - 图片Blob
   * @returns {Promise<{width: number, height: number}>}
   */
  async getImageDimensions(imageBlob) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(imageBlob);
      
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve({
          width: img.width,
          height: img.height
        });
      };
      
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('无法读取图片尺寸'));
      };
      
      img.src = url;
    });
  }
}

