import gradio as gr
from douyin_core import DouyinDownloader
from download_tab import create_download_tab
from copywriting_tab import create_copywriting_tab
from config_tab import create_config_tab

def create_interface():
    """创建主界面"""
    with gr.Blocks(title="作者工具", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🎵 作者工具")
        gr.Markdown("支持抖音视频下载、AI文案生成和配置管理")
        
        # 创建下载器实例
        downloader = DouyinDownloader()
        
        # 全局状态管理
        current_video_path = gr.State(value=None)
        gemini_api_key_state = gr.State(value="")
        
        # 创建三个标签页
        with gr.Tabs():
            # 视频下载标签页
            input_text = create_download_tab(downloader)
            
            # AI文案生成标签页
            create_copywriting_tab(downloader)
            
            # 配置标签页
            gemini_api_key = create_config_tab()
        
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
