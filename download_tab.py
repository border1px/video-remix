import gradio as gr
import json
from douyin_core import DouyinDownloader

def create_download_tab(downloader):
    """创建视频下载标签页"""
    
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
            api_info = json.dumps(parse_result.get('raw_response', {}), ensure_ascii=False, indent=2)
            return None, f"❌ 解析失败: {parse_result['error']}", current_video_path, api_info
        
        # 获取视频信息
        title = parse_result['title']
        author = parse_result['author']
        video_url = parse_result['video_url']
        
        if not video_url:
            api_info = json.dumps(parse_result.get('raw_response', {}), ensure_ascii=False, indent=2)
            return None, "❌ 未获取到视频下载链接", current_video_path, api_info
        
        # 下载视频
        download_result = downloader.download_video(video_url, title)
        if not download_result['success']:
            api_info = json.dumps(parse_result.get('raw_response', {}), ensure_ascii=False, indent=2)
            return None, f"❌ 下载失败: {download_result['error']}", current_video_path, api_info
        
        # 更新状态
        new_video_path = download_result['filepath']
        
        # 返回成功信息
        success_msg = f"✅ 下载成功！\n\n📹 标题: {title}\n👤 作者: {author}\n📁 文件: {download_result['filename']}\n💾 路径: {download_result['filepath']}"
        
        # 格式化API返回信息
        api_info = json.dumps(parse_result.get('raw_response', {}), ensure_ascii=False, indent=2)
        
        return new_video_path, success_msg, new_video_path, api_info
    
    # 创建视频下载标签页界面
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
            inputs=[input_text, gr.State()],
            outputs=[video_preview, gr.Textbox(label="状态信息"), gr.State(), api_response]
        )
        
        # 返回输入框，供主程序使用示例
        return input_text
