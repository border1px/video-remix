import gradio as gr
import os
import time
import re
from datetime import datetime
from core import DouyinDownloader, config_manager
from google.genai import types

def create_copywriting_tab(downloader):
    """创建AI文案生成标签页"""
    
    def format_start_time():
        """格式化开始时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def format_log_entry(elapsed_seconds, message):
        """格式化日志条目"""
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"[{current_time}] {message} (耗时: {elapsed_seconds:.1f}秒)"
    
    def get_video_path(video_input):
        """从video_input获取视频路径"""
        video_path = None
        if video_input is not None:
            if isinstance(video_input, str):
                video_path = video_input
            elif hasattr(video_input, 'name'):
                video_path = video_input.name
            else:
                video_path = video_input
        return video_path
    
    def get_filename_from_video(video_path):
        """根据视频文件名和日期生成markdown文件名
        格式：视频文件名_YYYYMMDD.md
        同一个视频多次保存会覆盖（文件名相同），不同视频保存新文件
        """
        if not video_path:
            return None
        
        # 获取视频文件名（不含扩展名）
        video_name = os.path.basename(video_path)
        video_name_without_ext = os.path.splitext(video_name)[0]
        
        # 清理文件名，移除特殊字符，保留中英文、数字、下划线和连字符
        clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', video_name_without_ext)
        clean_name = re.sub(r'\s+', '_', clean_name).strip('_')
        
        # 如果文件名太长，截取前50个字符
        if len(clean_name) > 50:
            clean_name = clean_name[:50]
        
        # 获取日期（年月日）
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 生成文件名：视频名_年月日.md
        filename = f"{clean_name}_{date_str}.md"
        
        return filename
    
    def save_copywriting(video_input, remake_script, current_log):
        """保存文案到markdown文件，返回更新后的日志"""
        if not remake_script or not remake_script.strip():
            log_entry = format_log_entry(0, "❌ 保存失败：没有可保存的文案内容")
            return (current_log + "\n" + log_entry) if current_log else log_entry
        
        try:
            # 获取视频路径
            video_path = get_video_path(video_input)
            if not video_path or not os.path.exists(video_path):
                log_entry = format_log_entry(0, "❌ 保存失败：无法确定视频路径，请重新上传视频")
                return (current_log + "\n" + log_entry) if current_log else log_entry
            
            # 生成文件名
            filename = get_filename_from_video(video_path)
            if not filename:
                log_entry = format_log_entry(0, "❌ 保存失败：无法生成文件名")
                return (current_log + "\n" + log_entry) if current_log else log_entry
            
            # 确保data目录存在
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 保存文件路径
            filepath = os.path.join(data_dir, filename)
            
            # 写入markdown文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(remake_script)
            
            elapsed = 0  # 保存操作很快，不需要记录耗时
            log_entry = format_log_entry(elapsed, f"✅ 文案已保存\n📁 文件名: {filename}\n💾 路径: {filepath}")
            return (current_log + "\n" + log_entry) if current_log else log_entry
        
        except Exception as e:
            elapsed = 0
            log_entry = format_log_entry(elapsed, f"❌ 保存失败: {str(e)}")
            return (current_log + "\n" + log_entry) if current_log else log_entry
    
    def generate_copywriting(video_input, account_positioning):
        """一次性生成三块内容：解析文案、分析特点、二创文案"""
        start_time = time.time()
        start_time_str = format_start_time()
        status_log = []
        status_log.append(f"🚀 开始执行 - {start_time_str}")
        
        # 获取视频路径
        video_path = None
        if video_input is not None:
            if isinstance(video_input, str):
                video_path = video_input
            elif hasattr(video_input, 'name'):
                video_path = video_input.name
            else:
                video_path = video_input
        
        if not video_path or not os.path.exists(video_path):
            raise gr.Error("❌ 请先下载视频或上传视频文件")
        
        # 读取API密钥
        api_key = config_manager.get("gemini_api_key", "")
        if not api_key:
            raise gr.Error("❌ 请先在配置页面输入Gemini API密钥")
        
        try:
            # 初始化
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🔄 正在初始化Gemini客户端..."))
            yield "", "", "", "\n".join(status_log), "", "", ""
            
            # 更新下载器的API密钥
            if downloader.gemini_api_key != api_key:
                downloader.gemini_api_key = api_key
                downloader.gemini_client = None
                if api_key:
                    from google import genai
                    downloader.gemini_client = genai.Client(api_key=api_key)
            
            # 上传视频
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "📤 正在上传视频到Gemini..."))
            yield "", "", "", "\n".join(status_log), "", "", ""
            
            upload_result = downloader.upload_video_to_gemini(video_path)
            if not upload_result['success']:
                elapsed_time = time.time() - start_time
                status_log.append(format_log_entry(elapsed_time, f"❌ 上传失败: {upload_result['error']}"))
                yield "", "", "", "\n".join(status_log), "", "", ""
                return
            
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频上传成功"))
            
            # 一次性生成三块内容
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🧠 正在一次性生成所有内容..."))
            yield "", "", "", "\n".join(status_log), "", "", ""
            
            # 第一步：解析上传视频的文案
            prompt1 = """请仔细分析这个视频，提取并复述视频中的文案内容（如果有的话）。如果没有明确的文案，请描述视频中的对话、旁白或文字内容。

要求：
1. 只提取纯文本内容，不要包含任何时间戳、时间信息
2. 按照视频中出现的顺序，完整呈现文案文本
3. 如果有字幕或文字，直接提取字幕内容
4. 如果是对话或旁白，用引号标注并说明是谁说的"""
            # 获取模型名称（从配置读取，默认使用gemini-2.5-flash）
            model_name = config_manager.get("gemini_model_name", "gemini-2.5-flash")
            response1 = downloader.generate_content_with_retry(
                model_name=model_name,
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt1)
                ]
            )
            original_copywriting = response1.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频文案解析完成"))
            
            # 在连续请求之间添加短暂延迟，避免触发速率限制
            time.sleep(1)
            
            # 第二步：分析视频的特点、风格、结构等信息
            prompt2 = """请详细分析这个视频的特点、风格和结构，包括但不限于：
1. 视频的拍摄风格（如：第一人称、第三人称、特写、全景等）
2. 视频的节奏和剪辑特点
3. 视频的内容主题和情感表达
4. 视频的语言风格（如：幽默、严肃、轻松、紧张等）
5. 视频的视觉元素（如：场景、道具、服装等）
6. 视频的目标受众和传播特点
请给出详细的分析报告。"""
            # 获取模型名称（从配置读取，默认使用gemini-2.5-flash）
            model_name = config_manager.get("gemini_model_name", "gemini-2.5-flash")
            response2 = downloader.generate_content_with_retry(
                model_name=model_name,
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt2)
                ]
            )
            video_analysis = response2.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频分析完成"))
            
            # 在连续请求之间添加短暂延迟，避免触发速率限制
            time.sleep(1)
            
            # 第三步：基于账号定位和视频，生成二创文案脚本
            prompt3 = f"""基于以下信息，创作一个新的短视频脚本：

【原视频分析】
{original_copywriting}

【视频特点分析】
{video_analysis}

【账号定位】
{account_positioning}

请结合你的账号定位，重新创作一个短视频脚本。要求：
1. 保持原视频的核心创意或主题，但要用你的账号风格来呈现
2. 脚本要符合你的账号定位和人物角色
3. 脚本要适合短视频平台，时长控制在45秒以内
4. 脚本要有清晰的开始、发展、高潮、结尾结构
5. 语言要生动有趣，符合你的账号风格"""
            
            # 获取模型名称（从配置读取，默认使用gemini-2.5-flash）
            model_name = config_manager.get("gemini_model_name", "gemini-2.5-flash")
            response3 = downloader.generate_content_with_retry(
                model_name=model_name,
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt3)
                ]
            )
            remake_script = response3.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 二创文案脚本生成完成"))
            
            # 完成
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"🏁 执行完成 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            
            yield original_copywriting, video_analysis, remake_script, "\n".join(status_log), upload_result['file_uri'], original_copywriting, video_analysis
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, f"❌ 处理失败: {str(e)}"))
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"💥 异常终止 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            yield "", "", "", "\n".join(status_log), "", "", ""
    
    def regenerate_copywriting(account_positioning, file_uri, original_copywriting, video_analysis):
        """只重新生成文案脚本（基于已上传的视频和前两块内容）"""
        start_time = time.time()
        start_time_str = format_start_time()
        status_log = []
        status_log.append(f"🚀 重新生成文案开始 - {start_time_str}")
        
        if not file_uri:
            raise gr.Error("❌ 请先使用'开始生成'按钮生成一次内容")
        
        if not original_copywriting or not video_analysis:
            raise gr.Error("❌ 缺少必要的分析信息，请重新使用'开始生成'按钮")
        
        # 读取API密钥
        api_key = config_manager.get("gemini_api_key", "")
        if not api_key:
            raise gr.Error("❌ 请先在配置页面输入Gemini API密钥")
        
        try:
            # 初始化
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
            
            # 重新生成：二创文案（使用已有的分析结果）
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "✍️ 正在重新生成二创文案脚本..."))
            yield "", "\n".join(status_log)
            
            prompt3 = f"""基于以下信息，创作一个新的短视频脚本：

【原视频分析】
{original_copywriting}

【视频特点分析】
{video_analysis}

【账号定位】
{account_positioning}

请结合你的账号定位，重新创作一个短视频脚本。要求：
1. 保持原视频的核心创意或主题，但要用你的账号风格来呈现
2. 脚本要符合你的账号定位和人物角色
3. 脚本要适合短视频平台，时长控制在45秒以内
4. 脚本要有清晰的开始、发展、高潮、结尾结构
5. 语言要生动有趣，符合你的账号风格"""
            
            # 获取模型名称（从配置读取，默认使用gemini-2.5-flash）
            model_name = config_manager.get("gemini_model_name", "gemini-2.5-flash")
            response3 = downloader.generate_content_with_retry(
                model_name=model_name,
                contents=[
                    types.Part(file_data=types.FileData(file_uri=file_uri)),
                    types.Part(text=prompt3)
                ]
            )
            remake_script = response3.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 二创文案脚本重新生成完成"))
            
            # 完成
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"🏁 执行完成 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            
            yield remake_script, "\n".join(status_log)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, f"❌ 处理失败: {str(e)}"))
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"💥 异常终止 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            yield "", "\n".join(status_log)
    
    # 创建AI文案生成标签页界面
    with gr.Tab("文案生成"):
        with gr.Row():
            # 左侧：输入区域
            with gr.Column(scale=1, min_width=350):
                # 1. 视频上传/预览
                video_input = gr.Video(
                    label="🎥 视频上传/预览",
                    height=300,
                    elem_classes="video-preview",
                    sources=["upload"]
                )
                
                # 2. 账号定位
                account_positioning = gr.Textbox(
                    label="📝 账号定位",
                    value=
"""
请分析短视频的结构和内容，结合我的账号定位，重新创作短视频脚本。以下是我的短视频账号定位：
【人物角色】
● 香贝贝：两岁的小戏精女宝，擅长观察和吐槽
● 爸爸：幽默搞笑的懒爸爸（配角，根据情况出现）
● 妈妈：不完美的成长型妈妈（配角，根据情况出现）
【创作要求】
1. 宝宝的第一视角，风格是："宝宝吐槽 + 育儿知识反差输出 + 家庭修罗场（三方视角冲突）"
2. 文案时长控制在45s以内，开头吸睛（宝宝吐槽搞笑/讽刺）；中段带入家庭矛盾或共鸣点
""",
                    lines=8,
                    placeholder="请输入您的账号定位...",
                    elem_classes="left-panel"
                )
                
                # 开始生成按钮（保持默认高度）
                generate_btn = gr.Button("🚀 开始生成", variant="primary")
                
                # 3. 处理日志
                progress_status = gr.Textbox(
                    label="📊 处理日志 (按时间顺序)",
                    value="⏸️ 等待开始...",
                    interactive=False,
                    lines=8
                )
            
            # 右侧：结果展示
            with gr.Column(scale=2):
                with gr.Accordion("🔍 原视频分析", open=False):
                    video_analysis_display = gr.Markdown(
                        value="💡 等待AI分析视频特点...",
                        elem_classes="markdown-result",
                        elem_id="video-analysis-markdown"
                    )
                
                # 使用Accordion折叠组件来节省空间
                with gr.Accordion("📝 原视频文案", open=False):
                    original_copywriting_display = gr.Markdown(
                        value="💡 等待AI解析视频文案...",
                        elem_classes="markdown-result",
                        elem_id="original-copywriting-markdown"
                    )
                
                with gr.Accordion("✍️ 二创文案", open=True):
                    remake_script_display = gr.Markdown(
                        value="💡 等待AI生成二创文案脚本...",
                        elem_classes="markdown-result",
                        elem_id="remake-script-markdown"
                    )
                
                # 重新生成和保存按钮（独立一行，正常高度）
                with gr.Row():
                    regenerate_btn = gr.Button("🔄 重新生成", variant="secondary", interactive=False)
                    save_btn = gr.Button("💾 保存文案", variant="secondary", interactive=False)
        
        # 状态变量
        file_uri_state = gr.State(value="")
        original_copywriting_state = gr.State(value="")
        video_analysis_state = gr.State(value="")
        current_video_path_state = gr.State(value="")
        
        # 绑定事件
        generate_btn.click(
            fn=generate_copywriting,
            inputs=[video_input, account_positioning],
            outputs=[
                original_copywriting_display,
                video_analysis_display,
                remake_script_display,
                progress_status,
                file_uri_state,
                original_copywriting_state,
                video_analysis_state
            ]
        ).then(
            lambda video: (gr.update(interactive=True), gr.update(interactive=True), get_video_path(video)),
            inputs=[video_input],
            outputs=[regenerate_btn, save_btn, current_video_path_state]
        )
        
        # 重新生成按钮事件（只更新文案脚本）
        regenerate_btn.click(
            fn=regenerate_copywriting,
            inputs=[account_positioning, file_uri_state, original_copywriting_state, video_analysis_state],
            outputs=[
                remake_script_display,
                progress_status
            ]
        )
        
        # 保存文案按钮事件
        save_btn.click(
            fn=save_copywriting,
            inputs=[video_input, remake_script_display, progress_status],
            outputs=[progress_status]
        )
        
        return video_input, generate_btn
