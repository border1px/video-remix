import requests
import re
import os
import time
from google import genai
from google.genai import types
from .config_manager import config_manager

class DouyinDownloader:
    def __init__(self, gemini_api_key=None):
        self.api_url = "https://api.suxun.site/api/douyin"
        # 下载目录路径：项目根目录的downloads文件夹
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.downloads_dir = os.path.join(base_dir, "downloads")
        self.gemini_api_key = gemini_api_key
        self.gemini_client = None
        
        # 确保下载目录存在
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)
        
        # 初始化Gemini客户端
        if self.gemini_api_key:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
    
    def extract_douyin_url(self, text):
        """从文本中提取抖音链接"""
        # 匹配抖音链接的正则表达式
        douyin_pattern = r'https://v\.douyin\.com/[A-Za-z0-9_/]+'
        match = re.search(douyin_pattern, text)
        if match:
            return match.group(0)
        return None
    
    def parse_video(self, url):
        """解析抖音视频获取下载链接"""
        try:
            # 调用解析API
            response = requests.get(self.api_url, params={'url': url}, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') == 200:
                video_info = data.get('data', {})
                return {
                    'success': True,
                    'title': video_info.get('title', '未知标题'),
                    'author': video_info.get('author', '未知作者'),
                    'video_url': video_info.get('url', ''),
                    'cover_url': video_info.get('cover', ''),
                    'duration': video_info.get('duration', 0),
                    'raw_response': data
                }
            else:
                return {
                    'success': False,
                'error': data.get('msg', '解析失败'),
                    'raw_response': data
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def download_video(self, video_url, title):
        """下载视频文件"""
        try:
            # 清理文件名，移除话题标签和特殊符号
            # 移除话题标签（#开头的内容）
            clean_title = re.sub(r'#\w+', '', title)
            # 移除其他特殊符号，只保留中英文、数字和空格
            clean_title = re.sub(r'[^\u4e00-\u9fff\w\s]', '', clean_title)
            # 移除多余空格
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            # 限制文件名长度
            if len(clean_title) > 30:
                clean_title = clean_title[:30]
            
            # 生成时间戳（年月日时分秒）
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{clean_title}_{timestamp}.mp4"
            filepath = os.path.join(self.downloads_dir, filename)
            
            # 下载视频
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': filename
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'下载失败: {str(e)}'
            }
    
    def upload_video_to_gemini(self, video_path):
        """上传视频到Gemini"""
        try:
            if not self.gemini_client:
                return {
                    'success': False,
                    'error': 'Gemini API密钥未配置'
                }
            
            # 上传视频文件
            uploaded_file = self.gemini_client.files.upload(file=video_path)
            
            # 等待上传完成
            max_wait_time = 300  # 最多等待5分钟
            wait_interval = 2    # 每2秒检查一次
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    # 检查文件状态
                    file_info = self.gemini_client.files.get(name=uploaded_file.name)
                    
                    if file_info.state == "ACTIVE":
                        return {
                            'success': True,
                            'file_uri': uploaded_file.uri,
                            'file_name': uploaded_file.name
                        }
                    elif file_info.state == "FAILED":
                        return {
                            'success': False,
                            'error': '文件处理失败'
                        }
                    elif file_info.state in ["PROCESSING", "PENDING"]:
                        # 文件还在处理中，继续等待
                        pass
                    else:
                        # 其他状态，继续等待
                        pass
                    
                except Exception as e:
                    # 如果获取文件信息失败，可能是文件还在上传中
                    if "not found" in str(e).lower() or "not finalized" in str(e).lower():
                        # 文件还在上传中，继续等待
                        pass
                    else:
                        # 其他错误，返回错误信息
                        return {
                            'success': False,
                            'error': f'检查文件状态失败: {str(e)}'
                        }
                
                # 等待后继续检查
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            return {
                'success': False,
                'error': '文件处理超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'上传失败: {str(e)}'
            }
    
    def generate_copywriting(self, video_path, prompt="请分析这个视频的内容，并生成一个吸引人的抖音文案，要求：1. 突出视频亮点 2. 使用热门话题标签 3. 语言生动有趣 4. 适合抖音平台传播"):
        """使用Gemini生成文案"""
        try:
            if not self.gemini_client:
                return {
                    'success': False,
                    'error': 'Gemini API密钥未配置'
                }
            
            # 上传视频
            upload_result = self.upload_video_to_gemini(video_path)
            if not upload_result['success']:
                return upload_result
            
            # 获取模型名称（从配置读取，默认使用gemini-2.5-flash）
            model_name = config_manager.get("gemini_model_name", "gemini-2.5-flash")
            # 调用Gemini生成文案
            response = self.gemini_client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part(file_data=types.FileData(file_uri=upload_result['file_uri'])),
                    types.Part(text=prompt)
                ]
            )
            
            return {
                'success': True,
                'copywriting': response.text,
                'file_uri': upload_result['file_uri']
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'生成文案失败: {str(e)}'
            }
