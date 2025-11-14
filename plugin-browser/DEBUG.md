# 调试指南

## 如何查看 Service Worker 日志

Service Worker 的日志不会显示在普通页面的控制台中，需要单独查看：

### 方法1：通过扩展管理页面查看

1. 打开 `chrome://extensions/`
2. 找到"豆包图片下载器"插件
3. 点击"service worker"链接（在"检查视图"旁边）
4. 这会打开 Service Worker 的开发者工具窗口
5. 切换到"Console"标签，就能看到所有日志

### 方法2：通过扩展详情页查看

1. 打开 `chrome://extensions/`
2. 找到"豆包图片下载器"插件
3. 点击"详细信息"
4. 在"检查视图"部分，点击"service worker"链接

## 调试步骤

### 1. 检查 Service Worker 是否运行

打开 Service Worker 控制台后，应该能看到：
```
[Background] 豆包图片下载器已安装
```

如果没有看到，说明 Service Worker 没有正确加载。

### 2. 检查配置是否正确

在 Service Worker 控制台中，运行：
```javascript
chrome.storage.sync.get(['tinypngEnabled', 'tinypngApiKey', 'targetWidth', 'targetHeight'], (result) => {
  console.log('配置:', result);
});
```

### 3. 测试下载功能

点击图片下载按钮后，在 Service Worker 控制台中应该能看到：
- `[Background] 收到消息: downloadImage`
- `[handleImageDownload] 函数开始执行`
- `[TinyPNG] 检查配置:`
- 等等...

### 4. 常见问题排查

#### 问题1：看不到任何日志
- 检查 Service Worker 是否正在运行
- 尝试重新加载插件
- 检查是否有 JavaScript 错误

#### 问题2：看到"压缩功能未启用"或"API Key未配置"
- 打开插件设置页面
- 确认"启用TinyPNG压缩功能"已勾选
- 确认已输入 API Key
- 保存设置后重新测试

#### 问题3：看到 TinyPNG API 错误
- 检查 API Key 是否正确
- 检查 API 使用量是否超限
- 查看错误信息中的详细说明

## 手动测试配置

在 Service Worker 控制台中运行以下代码来测试配置：

```javascript
// 测试获取配置
chrome.storage.sync.get([
  'enabled',
  'tinypngEnabled',
  'tinypngApiKey',
  'targetWidth',
  'targetHeight',
  'preserveAspectRatio'
], (result) => {
  console.log('当前配置:', {
    插件启用: result.enabled !== false,
    TinyPNG启用: result.tinypngEnabled !== false,
    有APIKey: !!result.tinypngApiKey,
    APIKey长度: result.tinypngApiKey ? result.tinypngApiKey.length : 0,
    目标宽度: result.targetWidth || 1920,
    目标高度: result.targetHeight || 1080,
    保持宽高比: result.preserveAspectRatio !== false
  });
});
```

## 查看网络请求

在 Service Worker 控制台中，切换到"Network"标签，可以看到：
- 对 TinyPNG API 的请求
- 请求的状态码
- 响应内容

如果看到 401 错误，说明 API Key 不正确。
如果看到 429 错误，说明 API 使用量超限。


