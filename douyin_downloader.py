import gradio as gr
import requests
import re
import os
from urllib.parse import urlparse
import time
from google import genai
from google.genai import types

class DouyinDownloader:
    def __init__(self, gemini_api_key=None):
        self.api_url = "https://api.suxun.site/api/douyin"
        self.downloads_dir = "downloads"
        self.gemini_api_key = gemini_api_key
        self.gemini_client = None
        
        # 确保下载目录存在
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)
        
        # 初始化Gemini客户端
        if self.gemini_api_key:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
    
    def extract_douyin_url(self, text):
        """从文本中提取抖音链接"""
        # 匹配抖音链接的正则表达式
        douyin_pattern = r'https://v\.douyin\.com/[A-Za-z0-9_/]+'
        match = re.search(douyin_pattern, text)
        if match:
            return match.group(0)
        return None
    
    def parse_video(self, url):
        """解析抖音视频获取下载链接"""
        try:
            # 调用解析API
            response = requests.get(self.api_url, params={'url': url}, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') == 200:
                video_info = data.get('data', {})
                return {
                    'success': True,
                    'title': video_info.get('title', '未知标题'),
                    'author': video_info.get('author', '未知作者'),
                    'video_url': video_info.get('url', ''),
                    'cover_url': video_info.get('cover', ''),
                    'duration': video_info.get('duration', 0)
                }
            else:
                return {
                    'success': False,
                    'error': data.get('msg', '解析失败')
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def download_video(self, video_url, title):
        """下载视频文件"""
        try:
            # 清理文件名，移除话题标签和特殊符号
            # 移除话题标签（#开头的内容）
            clean_title = re.sub(r'#\w+', '', title)
            # 移除其他特殊符号，只保留中英文、数字和空格
            clean_title = re.sub(r'[^\u4e00-\u9fff\w\s]', '', clean_title)
            # 移除多余空格
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            # 限制文件名长度
            if len(clean_title) > 30:
                clean_title = clean_title[:30]
            
            # 生成时间戳（年月日时分秒）
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{clean_title}_{timestamp}.mp4"
            filepath = os.path.join(self.downloads_dir, filename)
            
            # 下载视频
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': filename
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'下载失败: {str(e)}'
            }
    
    def process_douyin_link(self, input_text):
        """处理抖音链接的完整流程"""
        # 提取链接
        douyin_url = self.extract_douyin_url(input_text)
        if not douyin_url:
            return "❌ 未找到有效的抖音链接，请检查输入格式", None, None
        
        # 解析视频
        parse_result = self.parse_video(douyin_url)
        if not parse_result['success']:
            return f"❌ 解析失败: {parse_result['error']}", None, None
        
        # 获取视频信息
        title = parse_result['title']
        author = parse_result['author']
        video_url = parse_result['video_url']
        
        if not video_url:
            return "❌ 未获取到视频下载链接", None, None
        
        # 下载视频
        download_result = self.download_video(video_url, title)
        if not download_result['success']:
            return f"❌ 下载失败: {download_result['error']}", None, None
        
        # 返回成功信息
        success_msg = f"✅ 下载成功！\n\n📹 标题: {title}\n👤 作者: {author}\n📁 文件: {download_result['filename']}\n💾 路径: {download_result['filepath']}"
        
        # 返回本地文件路径，不返回任何远程URL
        download_info = f"📥 视频已下载到: {download_result['filepath']}"
        return success_msg, download_result['filepath'], download_info
    
    def upload_video_to_gemini(self, video_path):
        """上传视频到Gemini"""
        try:
            if not self.gemini_client:
                return {
                    'success': False,
                    'error': 'Gemini API密钥未配置'
                }
            
            # 上传视频文件
            uploaded_file = self.gemini_client.files.upload(file=video_path)
            
            # 等待上传完成
            max_wait_time = 300  # 最多等待5分钟
            wait_interval = 2    # 每2秒检查一次
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    # 检查文件状态
                    file_info = self.gemini_client.files.get(name=uploaded_file.name)
                    
                    if file_info.state == "ACTIVE":
                        return {
                            'success': True,
                            'file_uri': uploaded_file.uri,
                            'file_name': uploaded_file.name
                        }
                    elif file_info.state == "FAILED":
                        return {
                            'success': False,
                            'error': '文件处理失败'
                        }
                    elif file_info.state in ["PROCESSING", "PENDING"]:
                        # 文件还在处理中，继续等待
                        pass
                    else:
                        # 其他状态，继续等待
                        pass
                    
                except Exception as e:
                    # 如果获取文件信息失败，可能是文件还在上传中
                    if "not found" in str(e).lower() or "not finalized" in str(e).lower():
                        # 文件还在上传中，继续等待
                        pass
                    else:
                        # 其他错误，返回错误信息
                        return {
                            'success': False,
                            'error': f'检查文件状态失败: {str(e)}'
                        }
                
                # 等待后继续检查
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            return {
                'success': False,
                'error': '文件处理超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'上传失败: {str(e)}'
            }
    
    def generate_copywriting(self, video_path, prompt="请分析这个视频的内容，并生成一个吸引人的抖音文案，要求：1. 突出视频亮点 2. 使用热门话题标签 3. 语言生动有趣 4. 适合抖音平台传播"):
        """使用Gemini生成文案"""
        try:
            if not self.gemini_client:
                return {
                    'success': False,
                    'error': 'Gemini API密钥未配置'
                }
            
            # 上传视频
            upload_result = self.upload_video_to_gemini(video_path)
            if not upload_result['success']:
                return upload_result
            
            # 调用Gemini生成文案
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt)
                ]
            )
            
            return {
                'success': True,
                'copywriting': response.text,
                'file_uri': upload_result['file_uri']
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'生成文案失败: {str(e)}'
            }

# 创建下载器实例
downloader = DouyinDownloader()

def process_video(input_text):
    """Gradio界面处理函数"""
    if not input_text.strip():
        return "❌ 请输入抖音链接或包含链接的文本", None, None
    
    return downloader.process_douyin_link(input_text)

def process_video_with_state(input_text, current_video_path):
    """处理视频下载并更新状态"""
    if not input_text.strip():
        return None, "❌ 请输入抖音链接或包含链接的文本", current_video_path
    
    # 提取链接
    douyin_url = downloader.extract_douyin_url(input_text)
    if not douyin_url:
        return None, "❌ 未找到有效的抖音链接，请检查输入格式", current_video_path
    
    # 解析视频
    parse_result = downloader.parse_video(douyin_url)
    if not parse_result['success']:
        return None, f"❌ 解析失败: {parse_result['error']}", current_video_path
    
    # 获取视频信息
    title = parse_result['title']
    author = parse_result['author']
    video_url = parse_result['video_url']
    
    if not video_url:
        return None, "❌ 未获取到视频下载链接", current_video_path
    
    # 下载视频
    download_result = downloader.download_video(video_url, title)
    if not download_result['success']:
        return None, f"❌ 下载失败: {download_result['error']}", current_video_path
    
    # 更新状态
    new_video_path = download_result['filepath']
    
    # 返回成功信息
    success_msg = f"✅ 下载成功！\n\n📹 标题: {title}\n👤 作者: {author}\n📁 文件: {download_result['filename']}\n💾 路径: {download_result['filepath']}"
    
    return new_video_path, success_msg, new_video_path

def generate_copywriting_with_state(video_upload, prompt, api_key, current_video_path):
    """使用Gemini生成文案的界面函数（带状态管理）"""
    # 确定使用的视频文件
    video_path = None
    if video_upload is not None:
        video_path = video_upload.name
    elif current_video_path is not None:
        video_path = current_video_path
    
    if not video_path:
        return "❌ 请先下载视频或上传视频文件"
    
    if not api_key.strip():
        return "❌ 请先在配置页面输入Gemini API密钥"
    
    # 更新下载器的API密钥
    global downloader
    if downloader.gemini_api_key != api_key:
        downloader = DouyinDownloader(gemini_api_key=api_key)
    
    # 生成文案
    result = downloader.generate_copywriting(video_path, prompt)
    
    if result['success']:
        return f"✅ 文案生成成功！\n\n{result['copywriting']}"
    else:
        return f"❌ 生成失败: {result['error']}"

def save_gemini_config(api_key):
    """保存Gemini API配置"""
    if not api_key.strip():
        return "", "❌ 请输入有效的API密钥"
    
    # 验证API密钥格式（简单验证）
    if len(api_key) < 20:
        return "", "❌ API密钥格式不正确"
    
    return api_key, "✅ 配置保存成功"

# 创建Gradio界面
def create_interface():
    with gr.Blocks(title="作者工具", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🎵 作者工具")
        gr.Markdown("支持抖音视频下载、AI文案生成和配置管理")
        
        # 全局状态管理
        current_video_path = gr.State(value=None)
        gemini_api_key_state = gr.State(value="")
        
        # 创建三个标签页
        with gr.Tabs():
            # 视频下载标签页
            with gr.Tab("视频下载"):
                with gr.Row():
                    with gr.Column(scale=1):
                        input_text = gr.Textbox(
                            label="请输入链接地址",
                            placeholder="请输入抖音链接或包含链接的文本...",
                            lines=12
                        )
                        
                        process_btn = gr.Button("开始下载", variant="primary", size="lg")
                    
                    with gr.Column(scale=1):
                        video_preview = gr.Video(
                            label="视频预览",
                            height=300,
                            show_download_button=True,
                            interactive=False
                        )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        api_response = gr.Textbox(
                            label="接口返回的原始信息",
                            lines=8,
                            interactive=False
                        )
                
                # 绑定事件
                process_btn.click(
                    fn=process_video_with_state,
                    inputs=[input_text, current_video_path],
                    outputs=[video_preview, api_response, current_video_path]
                )
            
            # AI文案生成标签页
            with gr.Tab("AI文案生成"):
                with gr.Row():
                    with gr.Column(scale=1):
                        prompt_template = gr.Textbox(
                            label="提示词模板",
                            value="请分析这个视频的内容，并生成一个吸引人的抖音文案，要求：1. 突出视频亮点 2. 使用热门话题标签 3. 语言生动有趣 4. 适合抖音平台传播",
                            lines=4,
                            placeholder="请输入您想要的文案风格和要求..."
                        )
                        
                        video_upload = gr.File(
                            label="视频上传",
                            file_count="single",
                            file_types=["video"]
                        )
                        
                        generate_btn = gr.Button("开始生成", variant="primary", size="lg")
                    
                    with gr.Column(scale=1):
                        copywriting_result = gr.Markdown(
                            label="gemini输出结果 (markdown)",
                            value="",
                            show_copy_button=True
                        )
                
                # 绑定事件
                generate_btn.click(
                    fn=generate_copywriting_with_state,
                    inputs=[video_upload, prompt_template, gemini_api_key_state, current_video_path],
                    outputs=[copywriting_result]
                )
            
            # 配置标签页
            with gr.Tab("配置"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gemini_api_key = gr.Textbox(
                            label="gemini key配置",
                            type="password",
                            placeholder="请输入您的Gemini API密钥..."
                        )
                        
                        save_config_btn = gr.Button("保存配置", variant="primary")
                        
                        config_status = gr.Textbox(
                            label="配置状态",
                            lines=2,
                            interactive=False,
                            value="未配置"
                        )
                
                # 绑定事件
                save_config_btn.click(
                    fn=save_gemini_config,
                    inputs=[gemini_api_key],
                    outputs=[gemini_api_key_state, config_status]
                )
        
        # 示例
        gr.Markdown("### 💡 示例输入")
        gr.Examples(
            examples=[
                ["5.10 复制打开扌斗🎵，看看【草莓啵啵的作品】适合宝宝磨耳朵的英文儿歌～# 英语启蒙 # 每日英... https://v.douyin.com/_UUPq33ezOI/ O@k.pq zTl:/ 12/14"]
            ],
            inputs=[input_text]
        )
    
    return interface

if __name__ == "__main__":
    # 启动应用
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
