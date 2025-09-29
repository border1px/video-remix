import gradio as gr
from config_manager import config_manager

def create_config_tab():
    """创建配置标签页"""
    
    def save_gemini_config(api_key):
        """保存Gemini API配置"""
        if not api_key.strip():
            return "❌ 请输入有效的API密钥"
        
        # 验证API密钥格式（简单验证）
        if len(api_key) < 20:
            return "❌ API密钥格式不正确"
        
        # 使用配置管理器保存
        config_manager.set("gemini_api_key", api_key)
        return "✅ 配置保存成功"
    
    def load_config():
        """加载当前的配置"""
        api_key = config_manager.get("gemini_api_key", "")
        status = "已配置" if api_key else "未配置"
        return api_key, status
    
    # 创建配置标签页界面
    with gr.Tab("配置"):
        with gr.Row():
            with gr.Column(scale=1):
                gemini_api_key = gr.Textbox(
                    label="Gemini API密钥",
                    type="password",
                    placeholder="请输入您的Gemini API密钥..."
                )
                
                save_config_btn = gr.Button("保存配置", variant="primary")
                load_config_btn = gr.Button("加载已有配置", variant="secondary")
                
                config_status = gr.Textbox(
                    label="配置状态",
                    lines=2,
                    interactive=False,
                    value="未配置"
                )
        
        # 绑定事件
        save_config_btn.click(
            fn=save_gemini_config,
            inputs=[gemini_api_key],
            outputs=[config_status]
        )
        
        load_config_btn.click(
            fn=load_config,
            inputs=[],
            outputs=[gemini_api_key, config_status]
        )