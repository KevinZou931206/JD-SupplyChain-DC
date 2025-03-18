import logging
import os
import time
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from PyQt6.QtCore import QObject, pyqtSignal

class UILogHandler(logging.Handler):
    """
    自定义日志处理器，将日志同时显示在UI界面和终端
    """
    def __init__(self, signal_target=None):
        super().__init__()
        self.signal_target = signal_target
        
        # 设置格式化器
        formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s')
        self.setFormatter(formatter)
    
    def emit(self, record):
        """
        发出日志记录，如果有信号目标则发送到UI界面
        """
        try:
            msg = self.format(record)
            if self.signal_target is not None:
                # 通过信号发送日志消息到UI
                self.signal_target.log_signal.emit(msg)
                
            # 确保信号被处理，调用立即刷新
            QApplication = None
            try:
                from PyQt6.QtWidgets import QApplication
            except ImportError:
                pass
            
            if QApplication is not None and QApplication.instance() is not None:
                QApplication.instance().processEvents()
        except Exception:
            self.handleError(record)

class LogSignal(QObject):
    """
    用于传递日志消息的信号类
    """
    log_signal = pyqtSignal(str)

def ensure_log_dir():
    """
    确保日志目录存在
    """
    log_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

def setup_logging(ui_handler=None, log_level=logging.INFO):
    """
    设置全局日志配置
    
    参数:
        ui_handler: UI日志处理器
        log_level: 日志级别，默认为INFO
    """
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建标准格式化器
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s')
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 确保日志目录存在
    log_dir = ensure_log_dir()
    
    # 添加按大小轮转的文件处理器 (10MB, 最多保留5个备份)
    log_file = os.path.join(log_dir, 'app.log')
    size_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    size_handler.setLevel(log_level)
    size_handler.setFormatter(formatter)
    root_logger.addHandler(size_handler)
    
    # 添加按时间轮转的文件处理器 (每天轮转一次，保留30天)
    daily_log_file = os.path.join(log_dir, 'daily.log')
    time_handler = TimedRotatingFileHandler(
        daily_log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    time_handler.setLevel(log_level)
    time_handler.setFormatter(formatter)
    time_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(time_handler)
    
    # 添加错误日志专用处理器
    error_log_file = os.path.join(log_dir, 'error.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # 如果提供了UI处理器，则添加
    if ui_handler:
        ui_handler.setLevel(log_level)
        root_logger.addHandler(ui_handler)
    
    # 记录启动信息
    root_logger.info("========== 程序启动 ==========")
    root_logger.info(f"日志保存路径: {log_dir}")
    
    return root_logger

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    参数:
        name: 日志记录器名称
    
    返回:
        Logger: 日志记录器实例
    """
    return logging.getLogger(name) 