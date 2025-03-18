import os
import glob
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CacheManager')

class CacheManager:
    def __init__(self, cache_dir='./cache', download_dir='./Downloads'):
        self.cache_dir = cache_dir
        self.download_dir = download_dir
        
        # 确保目录存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
    def clear_cache(self):
        """清除缓存和下载文件"""
        try:
            # 清除缓存文件
            if os.path.exists(self.cache_dir):
                logger.info(f"开始清除缓存目录: {self.cache_dir}")
                cookie_file = os.path.join(self.cache_dir, 'cookies.json')
                if os.path.exists(cookie_file):
                    os.remove(cookie_file)
                    logger.info(f"已删除Cookies文件: {cookie_file}")
                
                # 清除其他临时文件
                for file in glob.glob(os.path.join(self.cache_dir, '*.*')):
                    os.remove(file)
                    logger.info(f"已删除缓存文件: {file}")
            
            # 清除下载文件夹中的所有文件
            if os.path.exists(self.download_dir):
                logger.info(f"开始清除下载目录: {self.download_dir}")
                for file in glob.glob(os.path.join(self.download_dir, '*.*')):
                    os.remove(file)
                    logger.info(f"已删除下载文件: {file}")
                    
            return {"success": True, "message": "缓存清除成功"}
            
        except Exception as e:
            logger.error(f"缓存清除失败: {str(e)}")
            return {"success": False, "message": f"缓存清除失败: {str(e)}"}
            
    def check_cookie_exists(self):
        """检查Cookie文件是否存在"""
        cookie_file = os.path.join(self.cache_dir, 'cookies.json')
        exists = os.path.exists(cookie_file)
        logger.info(f"检查Cookie文件是否存在: {exists}")
        return exists 