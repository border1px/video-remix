import gradio as gr  # type: ignore
import os
import subprocess
from datetime import datetime

# 剪映项目目录
JIANYING_PROJECTS_DIR = "/Users/rainbow/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/"

def get_project_folders():
    """获取剪映项目文件夹列表，按创建时间倒序排列"""
    if not os.path.exists(JIANYING_PROJECTS_DIR):
        return []
    
    folders = []
    try:
        for item in os.listdir(JIANYING_PROJECTS_DIR):
            # 过滤掉以.开头的隐藏文件夹
            if item.startswith('.'):
                continue
            
            item_path = os.path.join(JIANYING_PROJECTS_DIR, item)
            if os.path.isdir(item_path):
                # 获取创建时间
                stat = os.stat(item_path)
                # macOS 使用 st_birthtime 作为创建时间
                create_time = stat.st_birthtime
                folders.append({
                    'name': item,
                    'path': item_path,
                    'create_time': create_time
                })
        
        # 按创建时间倒序排列（最新的在前）
        folders.sort(key=lambda x: x['create_time'], reverse=True)
        return folders
    except Exception as e:
        print(f"读取文件夹列表失败: {e}")
        return []

def format_folder_summary(folders):
    """生成文件夹数量和最新项目的概览文本"""
    if not folders:
        return "📁 **未找到项目文件夹**\n\n请确认剪映项目目录是否存在。"
    
    latest_folder = folders[0]
    latest_time = datetime.fromtimestamp(latest_folder['create_time']).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"**共找到 {len(folders)} 个项目文件夹**（按创建时间倒序）\n\n"
        f"🆕 最新项目：`{latest_folder['name']}`，创建时间 `{latest_time}`"
    )

def format_folder_choices(folders):
    """将文件夹列表格式化为 Radio 的选项"""
    choices = []
    for folder in folders:
        create_time_str = datetime.fromtimestamp(folder['create_time']).strftime("%Y-%m-%d %H:%M:%S")
        display_text = f"{folder['name']}  ·  📅 {create_time_str}"
        choices.append(display_text)
    
    default_value = choices[0] if choices else None
    return choices, default_value

def extract_folder_name(choice_label):
    """从 Radio 的展示文本解析出真实文件夹名"""
    if not choice_label:
        return None
    return choice_label.split("  ·  ")[0].strip()

def open_folder_in_finder(folder_choice):
    """用访达打开指定文件夹下的 Resources/combination 目录"""
    folder_name = extract_folder_name(folder_choice)
    if not folder_name:
        return "❌ 请选择一个项目文件夹"
    
    folder_path = os.path.join(JIANYING_PROJECTS_DIR, folder_name)
    combination_path = os.path.join(folder_path, "Resources", "combination")
    
    if not os.path.exists(folder_path):
        return f"❌ 文件夹不存在: {folder_name}"
    
    try:
        # 优先打开 Resources/combination 目录，如果不存在则打开项目文件夹
        target_path = combination_path if os.path.exists(combination_path) else folder_path
        subprocess.run(['open', target_path], check=True)
        
        if os.path.exists(combination_path):
            return f"✅ 已用访达打开 Resources/combination 目录\n\n📁 {combination_path}"
        else:
            return f"⚠️ Resources/combination 目录不存在，已打开项目文件夹\n\n📁 {folder_path}"
    except subprocess.CalledProcessError as e:
        return f"❌ 打开失败: {str(e)}"
    except Exception as e:
        return f"❌ 发生错误: {str(e)}"

def refresh_folders():
    """刷新文件夹列表"""
    folders = get_project_folders()
    summary_text = format_folder_summary(folders)
    choices, default_value = format_folder_choices(folders)
    
    return summary_text, gr.update(choices=choices, value=default_value)

def create_jianying_tab():
    """创建剪映项目标签页"""
    
    # 初始加载文件夹列表
    initial_folders = get_project_folders()
    initial_choices, initial_value = format_folder_choices(initial_folders)
    
    with gr.Tab("剪映项目"):
        
        with gr.Row():
            with gr.Column(scale=2):
                folder_selector = gr.Radio(
                    label=f"📁 草稿列表（共 {len(initial_folders)} 个）",
                    choices=initial_choices,
                    value=initial_value,
                    interactive=True,
                    info=" "
                )
            
            with gr.Column(scale=1):
                # gr.Markdown("选择一个项目后，点击下方按钮即可用访达快速定位资源目录。")
                open_btn = gr.Button("📂 打开草稿", variant="primary", size="lg")
                refresh_btn = gr.Button("🔄 刷新列表", variant="secondary")

                status_info = gr.Textbox(
                    label="📊 状态信息",
                    lines=5,
                    interactive=False,
                    value="💡 选择一个项目文件夹，然后点击按钮打开"
                )
        
        # 绑定事件
        refresh_btn.click(
            fn=refresh_folders,
            inputs=[],
            outputs=[folder_selector]
        )
        
        open_btn.click(
            fn=open_folder_in_finder,
            inputs=[folder_selector],
            outputs=[status_info]
        )

