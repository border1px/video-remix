import gradio as gr

def create_config_tab():
    """创建配置标签页"""
    
    def save_gemini_config(api_key):
        """保存Gemini API配置"""
        if not api_key.strip():
            return "", "❌ 请输入有效的API密钥"
        
        # 验证API密钥格式（简单验证）
        if len(api_key) < 20:
            return "", "❌ API密钥格式不正确"
        
        return api_key, "✅ 配置保存成功"
    
    # 创建配置标签页界面
    with gr.Tab("配置"):
        with gr.Row():
            with gr.Column(scale=1):
                gemini_api_key = gr.Textbox(
                    label="gemini key配置",
                    type="password",
                    placeholder="请输入您的Gemini API密钥..."
                )
                
                save_config_btn = gr.Button("保存配置", variant="primary")
                
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
            outputs=[gr.State(), config_status]
        )
        
        # 返回API密钥输入框，供主程序引用
        return gemini_api_key
