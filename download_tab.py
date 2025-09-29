import gradio as gr
import json
import os
import glob
from douyin_core import DouyinDownloader

def get_latest_video_path():
    """获取downloads目录中最新的一视频文件路径"""
    downloads_dir = "downloads"
    if not os.path.exists(downloads_dir):
        return None
    
    # 查找所有MP4文件
    video_files = glob.glob(os.path.join(downloads_dir, "*.mp4"))
    if not video_files:
        return None
    
    # 按修改时间排序，取最新的
    latest_file = max(video_files, key=os.path.getmtime)
    return latest_file

def create_download_tab(downloader):
    """创建视频下载标签页"""
    
    def sync_to_copywriting():
        """同步最新视频到AI文案创作tab"""
        latest_video = get_latest_video_path()
        if latest_video:
            return latest_video
        return None
    
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
                    lines=15
                )
                
                with gr.Row():
                    process_btn = gr.Button("开始下载", variant="primary", size="lg")
                    reference_btn = gr.Button("参考创作", variant="secondary", size="lg", interactive=False)
            
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
        
        def process_video_with_button_state(input_text, current_video_path):
            """处理视频下载并更新按钮状态"""
            result = process_video_with_state(input_text, current_video_path)
            if len(result) == 4:
                video_path, msg, new_path, api_info = result
                # 如果下载成功，启用参考创作按钮
                button_enabled = video_path is not None
                return video_path, msg, new_path, api_info, gr.update(interactive=button_enabled)
            else:
                return result[0], result[1], result[2], result[3], gr.update(interactive=False)
        
        # 绑定事件
        download_outputs = [video_preview, gr.Textbox(label="状态信息"), gr.State(), api_response, reference_btn]
        process_btn.click(
            fn=process_video_with_button_state,
            inputs=[input_text, gr.State()],
            outputs=download_outputs
        )
        
        # 绑定参考创作按钮事件 - 需要创建全局状态来传递视频路径
        global_copywriting_video_path = gr.State()
        
        reference_btn.click(
            fn=sync_to_copywriting,
            inputs=[],
            outputs=[global_copywriting_video_path]
        )
        
        with gr.Column():      
            # 示例
            gr.Markdown("### 💡 示例输入")
            gr.Examples(
                examples=[
                    ["5.10 复制打开扌斗🎵，看看【草莓啵啵的作品】适合宝宝磨耳朵的英文儿歌～# 英语启蒙 # 每日英... https://v.douyin.com/_UUPq33ezOI/ O@k.pq zTl:/ 12/14"]
                ],
                inputs=[input_text]
            )
        
        # 返回输入框和按钮，供主程序使用
        return input_text, reference_btn, global_copywriting_video_path
