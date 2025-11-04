# -*- coding: utf-8 -*-
import codecs

content = '''import gradio as gr
import os
import time
from datetime import datetime
from douyin_core import DouyinDownloader
from config_manager import config_manager
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
    
    def generate_copywriting(video_input, account_positioning):
        """生成三块内容：解析文案、分析特点、二创文案"""
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
            yield "", "", "", "\\n".join(status_log), ""
            
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
            yield "", "", "", "\\n".join(status_log), ""
            
            upload_result = downloader.upload_video_to_gemini(video_path)
            if not upload_result['success']:
                elapsed_time = time.time() - start_time
                status_log.append(format_log_entry(elapsed_time, f"❌ 上传失败: {upload_result['error']}"))
                yield "", "", "", "\\n".join(status_log), ""
                return
            
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频上传成功"))
            yield "", "", "", "\\n".join(status_log), ""
            
            # 第一步：解析上传视频的文案
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "📝 正在解析视频文案..."))
            yield "", "", "", "\\n".join(status_log), ""
            
            prompt1 = "请仔细分析这个视频，提取并复述视频中的文案内容（如果有的话）。如果没有明确的文案，请描述视频中的对话、旁白或文字内容。"
            response1 = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt1)
                ]
            )
            original_copywriting = response1.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频文案解析完成"))
            yield original_copywriting, "", "", "\\n".join(status_log), ""
            
            # 第二步：分析视频的特点、风格、结构等信息
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🔍 正在分析视频特点、风格、结构..."))
            yield original_copywriting, "", "", "\\n".join(status_log), ""
            
            prompt2 = """请详细分析这个视频的特点、风格和结构，包括但不限于：
1. 视频的拍摄风格（如：第一人称、第三人称、特写、全景等）
2. 视频的节奏和剪辑特点
3. 视频的内容主题和情感表达
4. 视频的语言风格（如：幽默、严肃、轻松、紧张等）
5. 视频的视觉元素（如：场景、道具、服装等）
6. 视频的目标受众和传播特点
请给出详细的分析报告。"""
            response2 = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt2)
                ]
            )
            video_analysis = response2.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频分析完成"))
            yield original_copywriting, video_analysis, "", "\\n".join(status_log), ""
            
            # 第三步：基于账号定位和视频，生成二创文案脚本
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "✍️ 正在生成二创文案脚本..."))
            yield original_copywriting, video_analysis, "", "\\n".join(status_log), ""
            
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
            
            response3 = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
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
            
            yield original_copywriting, video_analysis, remake_script, "\\n".join(status_log), upload_result['file_uri']
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, f"❌ 处理失败: {str(e)}"))
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"💥 异常终止 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            yield "", "", "", "\\n".join(status_log), ""
    
    def regenerate_copywriting(account_positioning, file_uri):
        """重新生成三块内容（基于已上传的视频）"""
        start_time = time.time()
        start_time_str = format_start_time()
        status_log = []
        status_log.append(f"🚀 重新生成开始 - {start_time_str}")
        
        if not file_uri:
            raise gr.Error("❌ 请先使用'开始生成'按钮生成一次内容")
        
        # 读取API密钥
        api_key = config_manager.get("gemini_api_key", "")
        if not api_key:
            raise gr.Error("❌ 请先在配置页面输入Gemini API密钥")
        
        try:
            # 初始化
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🔄 正在初始化Gemini客户端..."))
            yield "", "", "", "\\n".join(status_log)
            
            # 更新下载器的API密钥
            if downloader.gemini_api_key != api_key:
                downloader.gemini_api_key = api_key
                downloader.gemini_client = None
                if api_key:
                    from google import genai
                    downloader.gemini_client = genai.Client(api_key=api_key)
            
            # 重新生成：解析文案
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "📝 正在重新解析视频文案..."))
            yield "", "", "", "\\n".join(status_log)
            
            prompt1 = "请仔细分析这个视频，提取并复述视频中的文案内容（如果有的话）。如果没有明确的文案，请描述视频中的对话、旁白或文字内容。"
            response1 = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=file_uri)),
                    types.Part(text=prompt1)
                ]
            )
            original_copywriting = response1.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频文案解析完成"))
            yield original_copywriting, "", "", "\\n".join(status_log)
            
            # 重新生成：分析特点
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🔍 正在重新分析视频特点、风格、结构..."))
            yield original_copywriting, "", "", "\\n".join(status_log)
            
            prompt2 = """请详细分析这个视频的特点、风格和结构，包括但不限于：
1. 视频的拍摄风格（如：第一人称、第三人称、特写、全景等）
2. 视频的节奏和剪辑特点
3. 视频的内容主题和情感表达
4. 视频的语言风格（如：幽默、严肃、轻松、紧张等）
5. 视频的视觉元素（如：场景、道具、服装等）
6. 视频的目标受众和传播特点
请给出详细的分析报告。"""
            response2 = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=file_uri)),
                    types.Part(text=prompt2)
                ]
            )
            video_analysis = response2.text
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频分析完成"))
            yield original_copywriting, video_analysis, "", "\\n".join(status_log)
            
            # 重新生成：二创文案
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "✍️ 正在重新生成二创文案脚本..."))
            yield original_copywriting, video_analysis, "", "\\n".join(status_log)
            
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
            
            response3 = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=file_uri)),
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
            
            yield original_copywriting, video_analysis, remake_script, "\\n".join(status_log)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, f"❌ 处理失败: {str(e)}"))
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"💥 异常终止 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            yield "", "", "", "\\n".join(status_log)
    
    # 创建AI文案生成标签页界面
    with gr.Tab("文案生成"):
        with gr.Row(equal_height=True):
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
● 爸爸：幽默搞笑的懒爸爸
● 妈妈：不完美的成长型妈妈
【创作要求】
1. 宝宝的第一视角，风格是："宝宝吐槽 + 育儿知识反差输出 + 家庭修罗场（三方视角冲突）"
2. 文案时长控制在45s以内，开头吸睛（宝宝吐槽搞笑/讽刺）；中段带入家庭矛盾或共鸣点；结尾甩出一个轻量育儿干货/金句。
""",
                    lines=8,
                    placeholder="请输入您的账号定位...",
                    elem_classes="left-panel"
                )
                
                # 开始生成按钮
                generate_btn = gr.Button("🚀 开始生成", variant="primary", size="lg")
                
                # 3. 处理日志
                progress_status = gr.Textbox(
                    label="📊 处理日志 (按时间顺序)",
                    value="⏸️ 等待开始...",
                    interactive=False,
                    lines=10
                )
            
            # 右侧：结果展示
            with gr.Column(scale=2):
                # 第一个文本框：解析上传视频的文案
                original_copywriting_display = gr.Textbox(
                    label="📝 解析上传视频的文案",
                    value="💡 等待AI解析视频文案...",
                    lines=8,
                    interactive=False,
                    show_copy_button=True,
                    elem_classes="result-textbox"
                )
                
                # 第二个文本框：分析视频特点、风格、结构
                video_analysis_display = gr.Textbox(
                    label="🔍 视频特点、风格、结构分析",
                    value="💡 等待AI分析视频特点...",
                    lines=10,
                    interactive=False,
                    show_copy_button=True,
                    elem_classes="result-textbox"
                )
                
                # 第三个文本框：二创文案脚本
                remake_script_display = gr.Textbox(
                    label="✍️ 基于账号定位的二创文案脚本",
                    value="💡 等待AI生成二创文案脚本...",
                    lines=12,
                    interactive=False,
                    show_copy_button=True,
                    elem_classes="result-textbox"
                )
                
                # 重新生成按钮
                regenerate_btn = gr.Button("🔄 重新生成", variant="secondary", size="lg", interactive=False)
        
        # 状态变量
        file_uri_state = gr.State(value="")
        
        # 绑定事件
        generate_btn.click(
            fn=generate_copywriting,
            inputs=[video_input, account_positioning],
            outputs=[
                original_copywriting_display,
                video_analysis_display,
                remake_script_display,
                progress_status,
                file_uri_state
            ]
        ).then(
            lambda: gr.update(interactive=True),
            outputs=[regenerate_btn]
        )
        
        # 重新生成按钮事件
        regenerate_btn.click(
            fn=regenerate_copywriting,
            inputs=[account_positioning, file_uri_state],
            outputs=[
                original_copywriting_display,
                video_analysis_display,
                remake_script_display,
                progress_status
            ]
        )
        
        return video_input, generate_btn
'''

with codecs.open('copywriting_tab.py', 'w', 'utf-8') as f:
    f.write(content)
print('File rewritten successfully!')
'''
