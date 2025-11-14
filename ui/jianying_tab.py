import gradio as gr
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

def format_folder_choices(folders):
    """格式化文件夹为选择列表，返回选项列表和对应的值"""
    if not folders:
        return [], None
    
    choices = []
    for folder in folders:
        create_time_str = datetime.fromtimestamp(folder['create_time']).strftime("%Y-%m-%d %H:%M:%S")
        # 格式：文件夹名 | 创建时间
        display_text = f"{folder['name']}  |  📅 {create_time_str}"
        choices.append((display_text, folder['name']))
    
    return choices, folders[0]['name'] if folders else None

def open_folder_in_finder(folder_name):
    """用访达打开指定文件夹下的 Resources/combination 目录"""
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
    choices, default_value = format_folder_choices(folders)
    
    count_text = f"**共找到 {len(folders)} 个项目文件夹**（按创建时间倒序排列）" if folders else "**未找到项目文件夹**"
    
    return (
        gr.update(choices=choices, value=default_value),
        count_text
    )

def create_jianying_tab():
    """创建剪映项目标签页"""
    
    # 初始加载文件夹列表
    initial_folders = get_project_folders()
    initial_choices, initial_value = format_folder_choices(initial_folders)
    # initial_count = f"**共找到 {len(initial_folders)} 个项目文件夹**（按创建时间倒序排列）" if initial_folders else "**未找到项目文件夹**"
    
    with gr.Tab("剪映草稿"):
        # gr.Markdown("### 📂 剪映项目文件夹管理")
        # gr.Markdown("选择项目文件夹，用访达打开其 `Resources/combination` 目录")
        
        # 统计信息
        # folder_count = gr.Markdown(value=initial_count)
        
        # 文件夹列表选择
        folder_selector = gr.Radio(
            label=f"📋 草稿列表（共 {len(initial_folders)} 个）",
            choices=initial_choices,
            value=initial_value,
            interactive=True,
            show_label=True,
            container=True,
            elem_classes="folder-list"
        )
        
        # 操作按钮区域
        with gr.Row():
            refresh_btn = gr.Button("🔄 刷新列表", variant="secondary", scale=1)
            open_btn = gr.Button("📂 打开复合片段目录", variant="primary", scale=2)
        
        # 状态信息
        status_info = gr.Textbox(
            label="📊 状态信息",
            lines=3,
            interactive=False,
            value="💡 从上方列表中选择一个草稿，打开该草稿的 Resources/combination 目录"
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

