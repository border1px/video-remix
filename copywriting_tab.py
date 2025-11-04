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
    
    def update_video_preview(file_obj):
        """更新视频预览"""
        if file_obj is not None:
            return file_obj  # 直接返回文件对象给Video组件
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
            yield "", "\n".join(status_log), "", ""
            
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
            yield "", "\n".join(status_log), "", ""
            
            # 上传视频到Gemini
            upload_result = downloader.upload_video_to_gemini(video_path)
            
            if not upload_result['success']:
                elapsed_time = time.time() - start_time
                status_log.append(format_log_entry(elapsed_time, f"❌ 上传失败: {upload_result['error']}"))
                error_msg = f"❌ 上传失败: {upload_result['error']}"
                yield error_msg, "\n".join(status_log), "", ""
                return
            
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, "✅ 视频上传成功"))
            yield "", "\n".join(status_log), "", ""
            
            # 第三步：生成文案
            elapsed = time.time() - start_time
            status_log.append(format_log_entry(elapsed, "🧠 正在生成文案..."))
            yield "", "\n".join(status_log), "", ""
            
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
            
            result_text = f"✅ **文案生成成功！**\n\n---\n\n{response.text}"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conversation_history = f"""## 🎯 AI生成结果 - {current_time}

{response.text}

---
*💡 提示：您可以在下方输入框中告诉AI如何修改这个文案*"""
            yield result_text, "\n".join(status_log), conversation_history, upload_result['file_uri']
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            status_log.append(format_log_entry(elapsed_time, f"❌ 处理失败: {str(e)}"))
            
            # 添加异常结束总结
            end_time_str = datetime.now().strftime("%H:%M:%S")
            status_log.append(f"💥 异常终止 - {end_time_str}")
            status_log.append(f"📊 总耗时: {elapsed_time:.1f}秒")
            
            error_msg = f"❌ 生成失败: {str(e)}"
            yield error_msg, "\n".join(status_log), "", ""
    
    def continue_conversation(user_message, conversation_history, file_uri):
        """继续对话，修改文案"""
        if not file_uri:
            raise gr.Error("❌ 请先生成初始文案")
        
        if not user_message.strip():
            raise gr.Error("❌ 请输入您的修改要求")
        
        try:
            # 构建对话历史的完整上下文
            full_prompt = f"""基于之前的分析结果，根据用户的新要求进行修改：

用户新要求：{user_message}

请保持分析的核心内容，但根据新要求进行调整。"""
            
            # 调用Gemini继续对话
            response = downloader.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part(file_data=types.FileData(file_uri=file_uri)),
                    types.Part(text=full_prompt)
                ]
            )
            
            # 更新对话历史（Markdown格式）
            current_time = datetime.now().strftime("%H:%M:%S")
            new_history = f"""{conversation_history}

---

### 🕐 {current_time}

**👤 用户说：**
{user_message}

**🤖 AI回复：**
{response.text}"""
            
            result_text = f"✅ 文案修改完成！\n\n{response.text}"
            
            return result_text, new_history, ""  # 清空输入框
            
        except Exception as e:
            error_msg = f"❌ 对话失败: {str(e)}"
            return error_msg, conversation_history, ""
    
    # 创建AI文案生成标签页界面
    with gr.Tab("AI文案生成"):
        with gr.Row(equal_height=False):
            # 左侧：更高的输入区域
            with gr.Column(scale=1, min_width=350):
                prompt_template = gr.Textbox(
                    label="📝 提示词模板",
                    value=
"""
    请分析短视频的结构和内容，结合我的账号定位，重新创作短视频脚本。以下是我的短视频账号定位：
    【人物角色】
    ● 香贝贝：两岁的小戏精女宝，擅长观察和吐槽
    ● 爸爸：幽默搞笑的懒爸爸
    ● 妈妈：不完美的成长型妈妈
    【创作要求】
    1. 宝宝的第一视角，风格是：“宝宝吐槽 + 育儿知识反差输出 + 家庭修罗场（三方视角冲突）”
    2. 文案时长控制在45s以内，开头吸睛（宝宝吐槽搞笑/讽刺）；中段带入家庭矛盾或共鸣点；结尾甩出一个轻量育儿干货/金句。
""",
                    lines=8,  # 增加行数
                    placeholder="请输入您想要的文案风格和要求...",
                    elem_classes="left-panel"
                )
                
                video_upload = gr.File(
                    label="🎥 视频上传",
                    file_count="single",
                    file_types=["video"],
                    elem_classes="video-upload"
                )
                
                # 视频预览组件
                video_preview = gr.Video(
                    label="📺 视频预览",
                    height=200,
                    elem_classes="video-preview"
                )
                
                generate_btn = gr.Button("🚀 开始生成", variant="primary", size="lg")
            
            # 右侧：markdown + 滚动对话
            with gr.Column(scale=2):
                # 顶部：当前文案结果（Markdown渲染）
                copywriting_result = gr.Markdown(
                    label="✨ 当前文案结果",
                    value="💡 等待AI生成文案...",
                    show_copy_button=True,
                    elem_classes="markdown-result"
                )
                
                # 中间：多轮对话区（滚动显示）
                with gr.Column():
                    user_input = gr.Textbox(
                        label="💬 继续对话（告诉AI如何修改文案）",
                        placeholder="💡 示例：请保持创意风格，但增加更多情感...\n         去掉话题标签，改用emoji\n         文字要更简短，突出重点",
                        lines=3
                    )
                    chat_btn = gr.Button("📤 修改", variant="primary")
                
                # 底部：对话历史（可折叠）
                with gr.Accordion("📚 对话历史", open=False):
                    conversation_display = gr.Markdown(
                        value="💬 **等待生成初始文案...**",
                        elem_classes="chat-history"
                    )
        
        # 累积状态日志显示
        progress_status = gr.Textbox(
            label="📊 处理日志 (按时间顺序)",
            value="⏸️ 等待开始...",
            interactive=False,
            lines=10
        )
        
        # 隐藏的状态变量，用于存储file_uri和对话历史
        file_uri_state = gr.State(value="")
        conversation_state = gr.State(value="")
        
        # 绑定事件
        generate_btn.click(
            fn=generate_copywriting_simple,
            inputs=[video_upload, prompt_template],
            outputs=[copywriting_result, progress_status, conversation_display, file_uri_state]
        ).then(
            lambda conv: conv,  # 更新conversation_state
            inputs=[conversation_display],
            outputs=[conversation_state]
        )
        
        # 视频上传预览事件
        video_upload.change(
            fn=update_video_preview,
            inputs=[video_upload],
            outputs=[video_preview]
        )
        
        # 对话事件
        chat_btn.click(
            fn=continue_conversation,
            inputs=[user_input, conversation_state, file_uri_state],
            outputs=[copywriting_result, conversation_display, user_input]
        ).then(
            lambda conv: conv,  # 更新conversation_state
            inputs=[conversation_display],
            outputs=[conversation_state]
        )
        
        # 返回video_upload控件、video_preview控件和generate_btn供主程序使用
        return video_upload, video_preview, generate_btn
