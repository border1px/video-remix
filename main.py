import gradio as gr
import os
from core import DouyinDownloader
from ui import create_download_tab, create_copywriting_tab, create_config_tab, create_jianying_tab

# 读取外部 CSS 文件
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
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
            video_input, generate_btn = create_copywriting_tab(downloader)
            create_jianying_tab()
            create_config_tab()
        
        def sync_video_to_copywriting(video_path):
            """同步视频到文案生成tab"""
            if video_path and os.path.exists(video_path):
                return video_path  # 更新video_input组件
            return None
        
        global_copywriting_video_path.change(
            fn=sync_video_to_copywriting,
            inputs=[global_copywriting_video_path],
            outputs=[video_input]
        )
    
    return interface

# ✅ 关键：在模块顶层暴露一个名为 `demo` 的变量（Gradio CLI 会自动识别）
demo = create_interface()

if __name__ == "__main__":
    demo.launch()