import gradio as gr
import os
from douyin_core import DouyinDownloader
from download_tab import create_download_tab
from copywriting_tab import create_copywriting_tab
from config_tab import create_config_tab

def create_interface():
    """创建主界面"""
    with gr.Blocks(title="创作者工具", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🎵 创作者工具")
        
        downloader = DouyinDownloader()
        current_video_path = gr.State(value=None)
        
        with gr.Tabs():
            input_text, reference_btn, global_copywriting_video_path = create_download_tab(downloader)
            video_upload, generate_btn = create_copywriting_tab(downloader)
            create_config_tab()
        
        def sync_video_to_copywriting(video_path):
            if video_path and os.path.exists(video_path):
                return video_path
            return None
        
        global_copywriting_video_path.change(
            fn=sync_video_to_copywriting,
            inputs=[global_copywriting_video_path],
            outputs=[video_upload]
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