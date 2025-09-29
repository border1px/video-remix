import gradio as gr
from douyin_core import DouyinDownloader

def create_copywriting_tab(downloader):
    """创建AI文案生成标签页"""
    
    def generate_copywriting_with_state(video_upload, prompt, api_key, current_video_path):
        """使用Gemini生成文案的界面函数（带状态管理）"""
        # 确定使用的视频文件
        video_path = None
        if video_upload is not None:
            video_path = video_upload.name
        elif current_video_path is not None:
            video_path = current_video_path
        
        if not video_path:
            return "❌ 请先下载视频或上传视频文件"
        
        if not api_key.strip():
            return "❌ 请先在配置页面输入Gemini API密钥"
        
        # 更新下载器的API密钥
        if downloader.gemini_api_key != api_key:
            downloader.gemini_api_key = api_key
            downloader.gemini_client = None
            if api_key:
                from google import genai
                downloader.gemini_client = genai.Client(api_key=api_key)
        
        # 生成文案
        result = downloader.generate_copywriting(video_path, prompt)
        
        if result['success']:
            return f"✅ 文案生成成功！\n\n{result['copywriting']}"
        else:
            return f"❌ 生成失败: {result['error']}"
    
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
        
        # 绑定事件
        generate_btn.click(
            fn=generate_copywriting_with_state,
            inputs=[video_upload, prompt_template, gr.State(), gr.State()],
            outputs=[copywriting_result]
        )
