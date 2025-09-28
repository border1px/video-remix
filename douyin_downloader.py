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

def generate_copywriting_with_gemini(video_path, prompt, api_key):
    """使用Gemini生成文案的界面函数"""
    if not video_path:
        yield "❌ 请先下载视频", None
        return
    
    if not api_key.strip():
        yield "❌ 请输入Gemini API密钥", None
        return
    
    # 更新下载器的API密钥
    global downloader
    if downloader.gemini_api_key != api_key:
        downloader = DouyinDownloader(gemini_api_key=api_key)
    
    # 显示上传进度
    yield "🔄 正在上传视频到Gemini...", None
    
    # 生成文案
    result = downloader.generate_copywriting(video_path, prompt)
    
    if result['success']:
        yield f"✅ 文案生成成功！\n\n{result['copywriting']}", result['copywriting']
    else:
        yield f"❌ 生成失败: {result['error']}", None

# 创建Gradio界面
def create_interface():
    with gr.Blocks(title="抖音视频下载器", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🎵 抖音视频下载器")
        gr.Markdown("支持解析抖音短视频链接并下载视频文件")
        
        with gr.Row():
            with gr.Column(scale=2):
                input_text = gr.Textbox(
                    label="抖音链接",
                    placeholder="请输入抖音链接或包含链接的文本...",
                    lines=3,
                    info="支持直接粘贴包含链接的完整文本"
                )
                
                process_btn = gr.Button("🚀 开始下载", variant="primary", size="lg")
            
            with gr.Column(scale=1):
                gr.Markdown("### 📋 使用说明")
                gr.Markdown("""
                1. 复制抖音视频链接
                2. 粘贴到输入框中
                3. 点击"开始下载"按钮
                4. 等待下载完成
                
                **支持的链接格式：**
                - `https://v.douyin.com/xxxxx/`
                - 包含链接的完整文本
                """)
        
        with gr.Row():
            result_text = gr.Textbox(
                label="处理结果",
                lines=6,
                interactive=False
            )
        
        with gr.Row():
            video_preview = gr.Video(
                label="视频预览",
                height=400,
                show_download_button=True,
                interactive=False
            )
            cover_image = gr.Image(
                label="封面图片",
                height=400,
                interactive=False,
                visible=False
            )
        
        # 添加下载信息显示
        download_info = gr.Textbox(
            label="下载信息",
            lines=2,
            interactive=False
        )
        
        # 绑定事件
        process_btn.click(
            fn=process_video,
            inputs=[input_text],
            outputs=[result_text, video_preview, download_info]
        )
        
        # 添加Gemini文案生成区域
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🤖 Gemini文案生成")
                gemini_api_key = gr.Textbox(
                    label="Gemini API密钥",
                    type="password",
                    placeholder="请输入您的Gemini API密钥..."
                )
                copywriting_prompt = gr.Textbox(
                    label="提示词",
                    value="请分析这个视频的内容，并生成一个吸引人的抖音文案，要求：1. 突出视频亮点 2. 使用热门话题标签 3. 语言生动有趣 4. 适合抖音平台传播",
                    lines=4,
                    placeholder="请输入您想要的文案风格和要求..."
                )
                generate_btn = gr.Button("🚀 生成文案", variant="primary")
            
            with gr.Column(scale=1):
                copywriting_result = gr.Textbox(
                    label="生成结果",
                    lines=8,
                    interactive=False
                )
                copywriting_output = gr.Textbox(
                    label="纯文案内容",
                    lines=4,
                    interactive=True
                )
        
        # 绑定文案生成事件
        generate_btn.click(
            fn=generate_copywriting_with_gemini,
            inputs=[video_preview, copywriting_prompt, gemini_api_key],
            outputs=[copywriting_result, copywriting_output],
            show_progress=True
        )
        
        # 添加文件浏览器
        with gr.Row():
            gr.Markdown("### 📁 下载的文件")
            file_browser = gr.File(
                label="选择视频文件",
                file_count="single",
                file_types=["video"]
            )
        
        # 文件选择事件
        def on_file_select(file):
            if file is None:
                return None
            return file.name
        
        file_browser.change(
            fn=on_file_select,
            inputs=[file_browser],
            outputs=[video_preview]
        )
        
        # 示例
        gr.Markdown("### 💡 示例输入")
        gr.Examples(
            examples=[
                ["5.10 复制打开扌斗🎵，看看【草莓啵啵的作品】适合宝宝磨耳朵的英文儿歌～# 英语启蒙 # 每日英... https://v.douyin.com/_UUPq33ezOI/ O@k.pq zTl:/ 12/14"]
            ],
            inputs=[input_text]
        )
        
        # 使用说明
        gr.Markdown("""
        ### 📖 使用说明
        
        1. **下载视频**：粘贴抖音链接，点击"开始下载"
        2. **配置API**：输入您的Gemini API密钥
        3. **自定义提示**：根据需要修改提示词
        4. **生成文案**：点击"生成文案"按钮
        5. **复制使用**：从"纯文案内容"区域复制生成的文案
        
        **获取Gemini API密钥**：访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
        """)
    
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
