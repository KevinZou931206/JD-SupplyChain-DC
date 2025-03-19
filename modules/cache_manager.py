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
        self.orders_dir = os.path.join(download_dir, 'orders')
        self.service_dir = os.path.join(download_dir, 'service')
        
        # 确保目录存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        if not os.path.exists(self.orders_dir):
            os.makedirs(self.orders_dir)
        if not os.path.exists(self.service_dir):
            os.makedirs(self.service_dir)
            
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
    
    def clear_orders_files(self):
        """清空订单文件夹"""
        try:
            if os.path.exists(self.orders_dir):
                logger.info(f"开始清空订单文件夹: {self.orders_dir}")
                
                # 清除所有文件
                files_count = 0
                for file in glob.glob(os.path.join(self.orders_dir, '*.*')):
                    os.remove(file)
                    files_count += 1
                    logger.info(f"已删除订单文件: {file}")
                
                return {"success": True, "message": f"订单文件清空成功，共删除 {files_count} 个文件"}
            else:
                logger.info(f"订单文件夹不存在: {self.orders_dir}，已创建")
                os.makedirs(self.orders_dir)
                return {"success": True, "message": "订单文件夹不存在，已创建新的空文件夹"}
                
        except Exception as e:
            logger.error(f"清空订单文件失败: {str(e)}")
            return {"success": False, "message": f"清空订单文件失败: {str(e)}"}
    
    def clear_service_files(self):
        """清空服务单文件夹"""
        try:
            if os.path.exists(self.service_dir):
                logger.info(f"开始清空服务单文件夹: {self.service_dir}")
                
                # 清除所有文件
                files_count = 0
                for file in glob.glob(os.path.join(self.service_dir, '*.*')):
                    os.remove(file)
                    files_count += 1
                    logger.info(f"已删除服务单文件: {file}")
                
                return {"success": True, "message": f"服务单文件清空成功，共删除 {files_count} 个文件"}
            else:
                logger.info(f"服务单文件夹不存在: {self.service_dir}，已创建")
                os.makedirs(self.service_dir)
                return {"success": True, "message": "服务单文件夹不存在，已创建新的空文件夹"}
                
        except Exception as e:
            logger.error(f"清空服务单文件失败: {str(e)}")
            return {"success": False, "message": f"清空服务单文件失败: {str(e)}"}
            
    def check_cookie_exists(self):
        """检查Cookie文件是否存在"""
        cookie_file = os.path.join(self.cache_dir, 'cookies.json')
        exists = os.path.exists(cookie_file)
        logger.info(f"检查Cookie文件是否存在: {exists}")
        return exists 