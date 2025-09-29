# dev.py
from watchfiles import run_process
import sys

def start_gradio_app():
    # 导入你的主文件（假设是 main.py）
    import main
    # 启动应用（确保 main.py 中有 demo = create_interface()）
    main.demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )

if __name__ == "__main__":
    print("🚀 开发模式启动中... 修改代码后自动重启")
    run_process(
        '.',  # 监控当前目录
        target=start_gradio_app,
        watch_filter=lambda changes, path: path.endswith('.py')  # 只监控 .py 文件
    )