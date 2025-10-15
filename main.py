import gradio as gr
import os
from douyin_core import DouyinDownloader
from download_tab import create_download_tab
from copywriting_tab import create_copywriting_tab
from config_tab import create_config_tab

# 读取外部 CSS 文件
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def create_interface():
    """创建主界面"""
    with gr.Blocks(
        title="创作者工具", 
        theme=gr.themes.Soft(),
        css=load_css()
    ) as interface:
        gr.Markdown("# 🎵 创作者工具")
        
        downloader = DouyinDownloader()
        current_video_path = gr.State(value=None)
        
        with gr.Tabs():
            input_text, reference_btn, global_copywriting_video_path = create_download_tab(downloader)
            video_upload, video_preview, generate_btn = create_copywriting_tab(downloader)
            create_config_tab()
        
        def sync_video_to_copywriting(video_path):
            """同步视频到文案生成tab"""
            if video_path and os.path.exists(video_path):
                return video_path, video_path  # 同时更新上传控件和预览控件
            return None, None
        
        global_copywriting_video_path.change(
            fn=sync_video_to_copywriting,
            inputs=[global_copywriting_video_path],
            outputs=[video_upload, video_preview]
        )
    
    return interface

# ✅ 关键：在模块顶层暴露一个名为 `demo` 的变量（Gradio CLI 会自动识别）
demo = create_interface()

if __name__ == "__main__":
    # 保持原有启动逻辑（兼容直接运行）
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )