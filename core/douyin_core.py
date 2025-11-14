import requests
import re
import os
import time
from google import genai
from google.genai import types
import hashlib
import shutil
import tempfile
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
        """上传视频到Gemini（增强：对含非 ASCII 的路径做临时拷贝并上传）"""
        # 内部帮助函数：生成 ASCII-safe 的临时拷贝（如不需要则返回原 path, False）
        def _make_ascii_safe_copy(src_path):
            if not src_path:
                return src_path, False
            try:
                basename = os.path.basename(src_path)
            except Exception:
                basename = "video"
            # 如果文件名全部是 ASCII，则直接返回原路径（不拷贝）
            if all(ord(ch) < 128 for ch in basename):
                return src_path, False
            # 生成唯一短 id，构造安全文件名
            sha1 = hashlib.sha1()
            sha1.update(src_path.encode('utf-8', errors='ignore'))
            digest = sha1.hexdigest()[:12]
            _, ext = os.path.splitext(basename)
            if not ext:
                ext = '.mp4'
            safe_name = f"video_{digest}{ext}"
            tmp_dir = tempfile.gettempdir()
            dst_path = os.path.join(tmp_dir, safe_name)
            try:
                # 若目标已存在且大小一致，直接复用
                if os.path.exists(dst_path) and os.path.getsize(dst_path) == os.path.getsize(src_path):
                    return dst_path, True
            except Exception:
                pass
            # 拷贝并保留元数据
            shutil.copy2(src_path, dst_path)
            return dst_path, True

        if not self.gemini_client:
            return {
                'success': False,
                'error': 'Gemini API密钥未配置'
            }

        safe_path = video_path
        created_temp = False
        result = None

        try:
            # 1) 如果文件名包含非 ASCII，先创建一个 ASCII-safe 的临时拷贝并上传该拷贝
            safe_path, created_temp = _make_ascii_safe_copy(video_path)

            # 2) 上传视频文件（使用 SDK 的 upload 接口）
            #    这里直接传路径（与原代码保持一致）。
            uploaded_file = self.gemini_client.files.upload(file=safe_path)

            # 3) 等待上传并轮询文件状态
            max_wait_time = 300  # 最多等待5分钟
            wait_interval = 2    # 每2秒检查一次
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                try:
                    # 有些 SDK 返回的 uploaded_file 可能包含 name 属性，也可能需要用上面返回的 name
                    file_name_for_query = getattr(uploaded_file, "name", None) or os.path.basename(safe_path)
                    file_info = self.gemini_client.files.get(name=file_name_for_query)

                    if getattr(file_info, "state", None) == "ACTIVE":
                        result = {
                            'success': True,
                            'file_uri': getattr(uploaded_file, "uri", None),
                            'file_name': getattr(uploaded_file, "name", file_name_for_query)
                        }
                        break
                    elif getattr(file_info, "state", None) == "FAILED":
                        result = {
                            'success': False,
                            'error': '文件处理失败'
                        }
                        break
                    # 如果仍在 PROCESSING/PENDING，继续等待
                except Exception as e:
                    # 兼容性判断：部分 SDK 在文件未最终化时会抛出 not found / not finalized 类似错误
                    lower = str(e).lower()
                    if "not found" in lower or "not finalized" in lower:
                        # 文件还在上传/处理，继续等待
                        pass
                    else:
                        result = {
                            'success': False,
                            'error': f'检查文件状态失败: {str(e)}'
                        }
                        break

                time.sleep(wait_interval)
                elapsed_time += wait_interval

            if result is None:
                # 如果循环结束还没有结果，则超时
                result = {
                    'success': False,
                    'error': '文件处理超时'
                }

            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'上传失败: {str(e)}'
            }
        finally:
            # 清理临时拷贝（如果创建过）
            try:
                if created_temp and safe_path and os.path.exists(safe_path):
                    try:
                        os.remove(safe_path)
                    except Exception:
                        # 无需中断主流程，如果删除失败就忽略
                        pass
            except Exception:
                pass


    def generate_content_with_retry(self, model_name, contents, max_retries=5, base_delay=2):
        """
        带重试机制的 Gemini API 调用
        使用指数退避策略处理 503 等临时错误
        
        Args:
            model_name: 模型名称
            contents: 请求内容
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒），每次重试会指数增长
        
        Returns:
            response 对象或抛出异常
        """
        if not self.gemini_client:
            raise Exception('Gemini API密钥未配置')
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                return response
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # 检查是否是 503 或其他可重试的错误
                is_retryable = (
                    '503' in error_str or 
                    'unavailable' in error_str or
                    'overloaded' in error_str or
                    'rate limit' in error_str or
                    '429' in error_str
                )
                
                # 如果不是可重试的错误，或者已经达到最大重试次数，直接抛出异常
                if not is_retryable or attempt == max_retries - 1:
                    raise
                
                # 计算延迟时间（指数退避：2s, 4s, 8s, 16s, 32s）
                delay = base_delay * (2 ** attempt)
                print(f"⚠️ API调用失败（尝试 {attempt + 1}/{max_retries}），{delay}秒后重试...")
                time.sleep(delay)
        
        # 如果所有重试都失败了，抛出最后一个异常
        raise last_exception

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
            # 调用Gemini生成文案（使用重试机制）
            response = self.generate_content_with_retry(
                model_name=model_name,
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
