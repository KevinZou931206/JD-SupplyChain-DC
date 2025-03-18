#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
京东供销平台数据采集与处理系统
"""

import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QDate, Qt, QObject, QThread, pyqtSignal, pyqtSlot
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ui import MainWindow, VerificationDialog
from modules import BrowserAutomation, ApiClient, DataProcessor, DatabaseManager, CacheManager, AccountManager
from modules import UILogHandler, LogSignal, setup_logging, get_logger
from config import CONFIG

# 创建日志信号对象
log_signal = LogSignal()

class WorkerSignals(QObject):
    # 定义信号
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(str)

class Worker(QThread):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            logger.exception(f"Worker执行过程中发生错误: {str(e)}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

class MainApp(QObject):
    def __init__(self):
        super().__init__()
        # 设置日志系统
        self.ui_handler = UILogHandler(log_signal)
        setup_logging(self.ui_handler)
        
        # 获取模块专用日志记录器
        global logger
        logger = get_logger('MainApp')
        
        # 创建应用和主窗口
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        
        # 日志信号连接到窗口状态更新
        log_signal.log_signal.connect(self.window.set_status)
        
        # 初始化各个模块
        self.account_manager = AccountManager()
        self.browser = None  # 延迟初始化，等用户选择账号后再创建
        self.api_client = ApiClient(
            cache_dir=CONFIG['paths']['cache_dir'],
            download_dir=CONFIG['paths']['download_dir']
        )
        self.data_processor = DataProcessor(
            download_dir=CONFIG['paths']['download_dir']
        )
        self.db_manager = DatabaseManager(
            server=CONFIG['db']['server'],
            database=CONFIG['db']['database'],
            username=CONFIG['db']['username'],
            password=CONFIG['db']['password']
        )
        self.cache_manager = CacheManager(
            cache_dir=CONFIG['paths']['cache_dir'],
            download_dir=CONFIG['paths']['download_dir']
        )
        
        # 连接信号
        self.connect_signals()
        
        # 加载账号配置
        self.load_accounts()
        
        # 检查是否已有cookie，如果有则启用相应功能
        self.check_login_status()
        
        # 显示主窗口
        self.window.show()
        
        logger.info("应用程序初始化完成")

    def connect_signals(self):
        """连接UI信号到对应的功能方法"""
        # 常规操作信号
        self.window.login_signal.connect(self.login)
        self.window.generate_signal.connect(self.generate_order_list)
        self.window.download_signal.connect(self.download_order_list)
        self.window.upload_signal.connect(self.upload_to_database)
        self.window.clear_cache_signal.connect(self.clear_cache)
        
        # 账号配置信号
        self.window.save_config_signal.connect(self.save_account_config)
        self.window.delete_config_signal.connect(self.delete_account_config)
        
        # 数据库配置信号
        self.window.update_db_config_signal.connect(self.update_db_config)
        
        # 注册应用退出事件
        self.app.aboutToQuit.connect(self.on_quit)
    
    def login(self, account_name):
        """登录处理方法，连接到UI的信号"""
        self.login_jd(account_name)
    
    def load_accounts(self):
        """加载账号配置"""
        accounts_result = self.account_manager.get_all_accounts()
        if accounts_result.get('success'):
            # 将账号添加到UI的下拉框中
            account_names = accounts_result.get('data', [])
            for account_name in account_names:
                self.window.add_account_to_combos(account_name)
            logger.info(f"成功加载 {len(account_names)} 个账号配置")
        else:
            logger.warning("加载账号配置失败")
    
    def check_login_status(self):
        """检查登录状态"""
        has_cookie = self.cache_manager.check_cookie_exists()
        if has_cookie:
            self.window.enable_logged_in_features(True)
            logger.info("已检测到登录状态，可以使用所有功能")
        else:
            logger.info("未检测到登录状态，请先登录")
    
    def login_jd(self, account_name):
        """登录京东"""
        logger.info(f"开始为账号 {account_name} 生成登录缓存")
        
        # 获取账号信息
        account_result = self.account_manager.get_account_info(account_name)
        if not account_result.get('success'):
            error_msg = f"获取账号信息失败: {account_result.get('message')}"
            logger.error(error_msg)
            self.window.show_message("错误", account_result.get('message'), QMessageBox.Icon.Warning)
            return
        
        account_info = account_result.get('data')
        username = account_info.get('username', '')
        password = account_info.get('password', '')
        
        # 检查账号密码是否为空
        if not username or not password:
            error_msg = "账号或密码为空，请先在配置信息页面完善账号信息"
            logger.error(error_msg)
            self.window.show_message("错误", error_msg, QMessageBox.Icon.Warning)
            return
        
        # 创建浏览器实例
        self.browser = BrowserAutomation(
            cache_dir=CONFIG['paths']['cache_dir'],
            jd_username=username,
            jd_password=password
        )
        
        logger.info("正在打开浏览器并尝试登录...")
        result = self.browser.login()
        
        if result == "需要手动验证":
            # 显示验证对话框
            logger.info("需要手动完成验证，请在浏览器中操作")
            dialog = VerificationDialog(self.window)
            dialog.exec()
            # 用户完成验证后继续
            logger.info("验证完成，等待进入主页面...")
            
            # 等待登录成功进入主页面
            try:
                WebDriverWait(self.browser.driver, 30).until(
                    EC.url_contains('gongxiao.jd.com/vender/home')
                )
                # 手动保存cookies
                self.browser.save_cookies()
                logger.info("已保存登录缓存")
                self.window.enable_logged_in_features(True)
            except Exception as e:
                logger.error(f"等待登录完成失败: {str(e)}")
                self.window.show_message("登录失败", f"等待登录完成失败: {str(e)}", QMessageBox.Icon.Warning)
                
        elif "登录成功" in result:
            logger.info("登录成功")
            self.window.enable_logged_in_features(True)
        else:
            logger.error(f"登录失败: {result}")
            self.window.show_message("登录失败", result, QMessageBox.Icon.Warning)
        
        # 关闭浏览器
        if self.browser:
            logger.info("关闭浏览器")
            self.browser.close()
    
    def generate_order_list(self, start_date, end_date, account_name):
        """生成订单列表"""
        logger.info(f"开始为账号 {account_name} 生成订单列表")
        logger.info(f"时间范围: {start_date} 至 {end_date}")
        
        start_time = f"{start_date} 00:00:00"
        end_time = f"{end_date} 23:59:59"
        
        result = self.api_client.generate_order_list(start_time, end_time)
        
        if result.get('success', False) or "message" in result:
            if "message" in result and result["message"] == "成功":
                total_num = result.get('data', {}).get('totalNum', 0)
                status_message = f"生成订单列表成功，共 {total_num} 条数据"
                logger.info(status_message)
                self.window.show_message("成功", status_message)
            else:
                status_message = f"生成订单列表成功: {result.get('message', '未知状态')}"
                logger.info(status_message)
                self.window.show_message("成功", status_message)
        else:
            status_message = f"生成订单列表失败: {result.get('message', '未知错误')}"
            logger.error(status_message)
            self.window.show_message("失败", status_message, QMessageBox.Icon.Warning)
    
    def download_order_list(self, account_name):
        """下载订单列表"""
        logger.info(f"开始为账号 {account_name} 下载订单列表")
        
        result = self.api_client.download_order_list()
        
        if result.get('success'):
            status_message = f"下载订单列表成功，文件保存在: {result.get('file_path')}"
            logger.info(status_message)
            self.window.show_message("成功", status_message)
        else:
            status_message = f"下载订单列表失败: {result.get('message')}"
            logger.error(status_message)
            self.window.show_message("失败", status_message, QMessageBox.Icon.Warning)
    
    def upload_to_database(self):
        """数据处理与上传"""
        logger.info("开始处理数据并上传到数据库")
        
        # 测试数据库连接
        logger.info("测试数据库连接...")
        db_test = self.db_manager.test_connection()
        if not db_test.get('success'):
            error_msg = f"数据库连接失败: {db_test.get('message')}"
            logger.error(error_msg)
            self.window.show_message("数据库连接失败", db_test.get('message'), QMessageBox.Icon.Critical)
            return
        
        # 处理Excel文件
        logger.info("正在处理Excel文件...")
        process_result = self.data_processor.process_excel_files()
        
        if process_result.get('success'):
            master_count = len(process_result.get('master_data', []))
            detail_count = len(process_result.get('detail_data', []))
            logger.info(f"数据处理成功，主表 {master_count} 条记录，明细表 {detail_count} 条记录")
            logger.info("开始上传数据到数据库...")
            
            # 上传数据
            upload_result = self.db_manager.upload_data(process_result)
            
            if upload_result.get('success'):
                # 获取主表和明细表的上传数量
                master_uploaded = upload_result.get('master_count', 0)
                detail_uploaded = upload_result.get('detail_count', 0)
                
                success_msg = f"数据上传成功，主表：{master_uploaded}条记录，明细表：{detail_uploaded}条记录"
                logger.info(success_msg)
                self.window.show_message("上传成功", success_msg)
            else:
                logger.error(upload_result.get('message'))
                self.window.show_message("上传失败", upload_result.get('message'), QMessageBox.Icon.Warning)
        else:
            status_message = f"数据处理失败: {process_result.get('message')}"
            logger.error(status_message)
            self.window.show_message("失败", status_message, QMessageBox.Icon.Warning)
    
    def clear_cache(self):
        """清除缓存"""
        logger.info("开始清除缓存")
        
        result = self.cache_manager.clear_cache()
        
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("清除成功", result.get('message'))
            self.window.enable_logged_in_features(False)  # 禁用需要登录的功能
        else:
            logger.error(result.get('message'))
            self.window.show_message("清除失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def save_account_config(self, config):
        """保存账号配置"""
        logger.info(f"开始保存账号 {config.get('account_name')} 的配置")
        
        result = self.account_manager.save_account(config)
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("保存成功", result.get('message'))
            
            # 更新UI中的账号列表
            self.window.add_account_to_combos(config.get('account_name'))
        else:
            logger.error(result.get('message'))
            self.window.show_message("保存失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def delete_account_config(self, account_name):
        """删除账号配置"""
        logger.info(f"开始删除账号 {account_name} 的配置")
        
        result = self.account_manager.delete_account(account_name)
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("删除成功", result.get('message'))
            
            # 从UI中移除账号
            self.window.remove_account_from_combos(account_name)
        else:
            logger.error(result.get('message'))
            self.window.show_message("删除失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def update_db_config(self):
        """更新数据库配置"""
        try:
            # 重新加载配置文件
            import importlib
            import config
            importlib.reload(config)
            
            # 更新数据库管理器的连接参数
            self.db_manager = DatabaseManager(
                server=config.CONFIG['db']['server'],
                database=config.CONFIG['db']['database'],
                username=config.CONFIG['db']['username'],
                password=config.CONFIG['db']['password']
            )
            logger.info("数据库配置已更新")
        except Exception as e:
            logger.error(f"更新数据库配置失败: {str(e)}")
    
    def on_quit(self):
        """应用程序退出前的清理工作"""
        logger.info("应用程序正在退出，执行清理操作...")
        
        # 关闭可能存在的浏览器实例
        if hasattr(self, 'browser') and self.browser is not None:
            try:
                self.browser.close()
                logger.info("已关闭浏览器实例")
            except Exception as e:
                logger.error(f"关闭浏览器实例时出错: {str(e)}")
        
        logger.info("应用程序清理完成，准备退出")
    
    def run(self):
        """运行应用程序"""
        self.window.show()
        return self.app.exec()

if __name__ == "__main__":
    app = MainApp()
    sys.exit(app.run()) 