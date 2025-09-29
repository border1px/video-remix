import gradio as gr
import os
import time
from datetime import datetime
from douyin_core import DouyinDownloader
from config_manager import config_manager
from google.genai import types

def create_copywriting_tab(downloader):
    """创建AI文案生成标签页"""
    
    def sync_video_from_download(video_path):
        """接收来自下载tab的视频文件"""
        if video_path and os.path.exists(video_path):
            return video_path
        return None
    
    def format_start_time():
        """格式化开始时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def format_log_entry(elapsed_seconds, message):
        """格式化日志条目"""
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"[{current_time}] {message} (耗时: {elapsed_seconds:.1f}秒)"
    
    def generate_copywriting_simple(video_upload, prompt):
        """使用Gemini生成文案（带累积状态日志）"""
        start_time = time.time()
        start_time_str = format_start_time()
        status_log = []  # 用于累积状态记录
        
        # 添加开始时间
        status_log.append(f"🚀 开始执行 - {start_time_str}")
        
        # 确定使用的视频文件
        video_path = None
        if video_upload is not None:
            video_path = video_upload.name
        
        if not video_path:
            raise gr.Error("❌ 请先下载视频或上传视频文件")
        
        # 从配置文件读取API密钥
        api_key = config_manager.get("gemini_api_key", "")
        if not api_key:
            raise gr.Error("❌ 请先在配置页面输入Gemini API密钥")
        
        try:
            # 第一步：初始化
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🔄 正在初始化Gemini客户端..."))
            yield "", "\n".join(status_log)
            
            # 更新下载器的API密钥
            if downloader.gemini_api_key != api_key:
                downloader.gemini_api_key = api_key
                downloader.gemini_client = None
                if api_key:
                    from google import genai
                    downloader.gemini_client = genai.Client(api_key=api_key)
            
            # 第二步：开始上传
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "📤 正在上传视频到Gemini..."))
            yield "", "\n".join(status_log)
            
            # 上传视频到Gemini
            upload_result = downloader.upload_video_to_gemini(video_path)
            
            if not upload_result['success']:
                elapsed_time = time.time() - start_time
                status_log.append(format_log_entry(elapsed_time, f"❌ 上传失败: {upload_result['error']}"))
                error_msg = f"❌ 上传失败: {upload_result['error']}"
                yield error_msg, "\n".join(status_log)
                return
            
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频上传成功"))
            yield "", "\n".join(status_log)
            
            # 第三步：生成文案
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🧠 正在生成文案..."))
            yield "", "\n".join(status_log)
            
            # 调用Gemini生成文案
            response = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt)
                ]
            )
            
            # 第四步：完成
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 文案生成完成！"))
            
            # 添加总耗时总结
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"🏁 执行完成 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            
            result_text = f"✅ 文案生成成功！\n\n{response.text}"
            yield result_text, "\n".join(status_log)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, f"❌ 处理失败: {str(e)}"))
            
            # 添加异常结束总结
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"💥 异常终止 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            
            error_msg = f"❌ 生成失败: {str(e)}"
            yield error_msg, "\n".join(status_log)
    
    # 创建AI文案生成标签页界面
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
        
        # 累积状态日志显示
        progress_status = gr.Textbox(
            label="📊 处理日志 (按时间顺序)",
            value="⏸️ 等待开始...",
            interactive=False,
            lines=10
        )
        
        # 绑定事件
        generate_btn.click(
            fn=generate_copywriting_simple,
            inputs=[video_upload, prompt_template],
            outputs=[copywriting_result, progress_status]
        )
        
        # 返回video_upload控件和generate_btn供主程序使用
        return video_upload, generate_btn
