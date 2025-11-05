import json
import os

class ConfigManager:
    def __init__(self, config_file=None):
        if config_file is None:
            # 默认配置文件路径：项目根目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(base_dir, "config.json")
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"配置文件加载失败: {e}")
                return {}
        return {}
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"配置文件保存失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value
        return self.save_config()
    
    def remove(self, key):
        """删除配置项"""
        if key in self.config:
            del self.config[key]
            return self.save_config()
        return True

# 全局配置管理器实例
config_manager = ConfigManager()
