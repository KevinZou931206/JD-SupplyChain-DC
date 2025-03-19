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
import json
import requests

from ui import MainWindow, VerificationDialog
from modules import BrowserAutomation, ApiClient, DataProcessor, DatabaseManager, CacheManager, AccountManager
from modules import UILogHandler, LogSignal, setup_logging, get_logger
from config import CONFIG, load_db_config

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

        # 从函数加载数据库配置
        db_config = load_db_config()
        
        # 如果数据库配置为空，提示用户
        if not db_config:
            logger.warning("数据库配置不存在或为空，请在数据库配置标签页中设置正确的连接信息")
            QMessageBox.warning(self.window, "数据库配置缺失", 
                              "数据库配置不存在或为空，请在「数据库配置」标签页中设置正确的连接信息")

        # 创建数据库管理器
        self.db_manager = DatabaseManager(
            server=db_config.get('server', ''),
            database=db_config.get('database', ''),
            username=db_config.get('username', ''),
            password=db_config.get('password', ''),
            batch_size=db_config.get('batch_size', '100'),
            timeout=db_config.get('timeout', '30')
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
        
        # 新增信号连接
        self.window.clear_orders_signal.connect(self.clear_orders_files)
        self.window.generate_service_signal.connect(self.generate_service_list)
        self.window.download_service_signal.connect(self.download_service_list)
        self.window.upload_service_signal.connect(self.upload_service_to_database)
        self.window.clear_service_signal.connect(self.clear_service_files)
        
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
        
        # 将下载路径修改为orders子文件夹
        orders_dir = CONFIG['paths']['orders_dir']
        if not os.path.exists(orders_dir):
            os.makedirs(orders_dir)
        
        result = self.api_client.download_order_list(orders_dir)
        
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("下载成功", result.get('message'))
        else:
            logger.error(result.get('message'))
            self.window.show_message("下载失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def upload_to_database(self):
        """上传订单数据到数据库"""
        logger.info("开始处理Excel文件并上传到数据库")
        
        # 测试数据库连接
        test_result = self.db_manager.test_connection()
        if not test_result.get('success'):
            error_msg = f"数据库连接失败: {test_result.get('message')}"
            logger.error(error_msg)
            self.window.show_message("数据库连接失败", error_msg, QMessageBox.Icon.Warning)
            return
        
        logger.info("数据库连接测试成功")
        
        # 处理Excel文件
        orders_dir = CONFIG['paths']['orders_dir']
        logger.info(f"从 {orders_dir} 目录读取订单Excel文件")
        
        try:
            data_result = self.data_processor.process_order_excel(orders_dir)
            if not data_result.get('success'):
                error_msg = f"Excel处理失败: {data_result.get('message')}"
                logger.error(error_msg)
                self.window.show_message("处理失败", error_msg, QMessageBox.Icon.Warning)
                return
                
            logger.info("Excel文件处理成功")
            
            # 上传数据到数据库
            upload_result = self.db_manager.upload_data(data_result)
            if upload_result.get('success'):
                success_msg = upload_result.get('message')
                logger.info(success_msg)
                self.window.show_message("上传成功", success_msg)
            else:
                error_msg = f"数据上传失败: {upload_result.get('message')}"
                logger.error(error_msg)
                self.window.show_message("上传失败", error_msg, QMessageBox.Icon.Warning)
                
        except Exception as e:
            error_msg = f"上传过程中发生错误: {str(e)}"
            logger.error(error_msg)
            self.window.show_message("上传错误", error_msg, QMessageBox.Icon.Critical)
    
    def clear_cache(self):
        """清除缓存"""
        logger.info("开始清除登录缓存")
        
        result = self.cache_manager.clear_cache()
        
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("清除成功", result.get('message'))
            self.window.enable_logged_in_features(False)  # 禁用需要登录的功能
        else:
            logger.error(result.get('message'))
            self.window.show_message("清除失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def clear_orders_files(self):
        """清空订单文件夹"""
        logger.info("开始清空订单文件")
        
        result = self.cache_manager.clear_orders_files()
        
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("清除成功", result.get('message'))
        else:
            logger.error(result.get('message'))
            self.window.show_message("清除失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def clear_service_files(self):
        """清空服务单文件夹"""
        logger.info("开始清空服务单文件")
        
        result = self.cache_manager.clear_service_files()
        
        if result.get('success'):
            logger.info(result.get('message'))
            self.window.show_message("清除成功", result.get('message'))
        else:
            logger.error(result.get('message'))
            self.window.show_message("清除失败", result.get('message'), QMessageBox.Icon.Warning)
    
    def generate_service_list(self, start_date, end_date):
        """生成服务单列表"""
        logger.info(f"开始生成服务单列表，时间范围: {start_date} 至 {end_date}")
        
        # 从cache/cookies.json获取cookies
        cookie_file = os.path.join(CONFIG['paths']['cache_dir'], 'cookies.json')
        if not os.path.exists(cookie_file):
            error_msg = "Cookie文件不存在，请先进行登录"
            logger.error(error_msg)
            self.window.show_message("生成失败", error_msg, QMessageBox.Icon.Warning)
            return
        
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            # 构建cookie字符串
            cookie_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_data])
            
            # 准备请求参数
            start_time = f"{start_date} 00:00:00"
            end_time = f"{end_date} 23:59:59"
            
            payload = {
                "startCreatedTime": start_time,
                "endCreatedTime": end_time
            }
            
            # 设置请求头
            headers = {
                'authority': 'gmall.jd.com',
                'method': 'POST',
                'path': '/api/afs/query/exportAfsService',
                'scheme': 'https',
                'accept': 'application/json, text/plain, */*',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'zh-CN,zh;q=0.9',
                'content-type': 'application/json',
                'cookie': cookie_str,
                'origin': 'https://gongxiao.jd.com',
                'referer': 'https://gongxiao.jd.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            }
            
            # 发送请求
            response = requests.post(
                'https://gmall.jd.com/api/afs/query/exportAfsService',
                json=payload,
                headers=headers
            )
            
            result = response.json()
            
            if result.get('success') == True and result.get('message') == "成功":
                logger.info(f"服务单生成请求成功: {result.get('message')}")
                self.window.show_message("生成成功", f"服务单生成请求成功，可以点击下载服务单按钮进行下载")
            else:
                logger.error(f"服务单生成请求失败: {result}")
                self.window.show_message("生成失败", f"服务单生成请求失败: {result.get('message', '未知错误')}", QMessageBox.Icon.Warning)
                
        except Exception as e:
            error_msg = f"生成服务单时发生错误: {str(e)}"
            logger.error(error_msg)
            self.window.show_message("生成失败", error_msg, QMessageBox.Icon.Critical)
    
    def download_service_list(self):
        """下载服务单列表"""
        logger.info("开始下载服务单列表")
        
        # 从cache/cookies.json获取cookies
        cookie_file = os.path.join(CONFIG['paths']['cache_dir'], 'cookies.json')
        if not os.path.exists(cookie_file):
            error_msg = "Cookie文件不存在，请先进行登录"
            logger.error(error_msg)
            self.window.show_message("下载失败", error_msg, QMessageBox.Icon.Warning)
            return
        
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            # 构建cookie字符串
            cookie_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_data])
            
            # 设置请求头
            headers = {
                'authority': 'gmall.jd.com',
                'method': 'POST',
                'path': '/api/afs/query/queryExportResult',
                'scheme': 'https',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'cookie': cookie_str,
                'origin': 'https://gongxiao.jd.com',
                'referer': 'https://gongxiao.jd.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            }
            
            # 发送请求
            response = requests.post(
                'https://gmall.jd.com/api/afs/query/queryExportResult',
                json={},
                headers=headers
            )
            
            result = response.json()
            
            if result.get('success') == True and result.get('message') == "成功" and result.get('data'):
                # 从响应中提取下载链接
                download_url = result.get('data')[0].get('url')
                if download_url:
                    # 下载文件
                    service_dir = CONFIG['paths']['service_dir']
                    if not os.path.exists(service_dir):
                        os.makedirs(service_dir)
                    
                    # 生成文件名：服务单_当前日期.xls
                    current_date = datetime.now().strftime('%Y%m%d%H%M%S')
                    filename = os.path.join(service_dir, f"服务单_{current_date}.xls")
                    
                    # 下载文件
                    file_response = requests.get(download_url)
                    with open(filename, 'wb') as f:
                        f.write(file_response.content)
                    
                    logger.info(f"服务单下载成功，已保存到: {filename}")
                    self.window.show_message("下载成功", f"服务单文件已保存到: {filename}")
                else:
                    logger.error("下载链接不存在")
                    self.window.show_message("下载失败", "下载链接不存在，请先生成服务单", QMessageBox.Icon.Warning)
            else:
                logger.error(f"服务单下载请求失败: {result}")
                self.window.show_message("下载失败", f"服务单下载请求失败: {result.get('message', '未知错误')}", QMessageBox.Icon.Warning)
                
        except Exception as e:
            error_msg = f"下载服务单时发生错误: {str(e)}"
            logger.error(error_msg)
            self.window.show_message("下载失败", error_msg, QMessageBox.Icon.Critical)
    
    def upload_service_to_database(self):
        """上传服务单数据到数据库"""
        logger.info("开始处理服务单Excel文件并上传到数据库")
        
        # 测试数据库连接
        test_result = self.db_manager.test_connection()
        if not test_result.get('success'):
            error_msg = f"数据库连接失败: {test_result.get('message')}"
            logger.error(error_msg)
            self.window.show_message("数据库连接失败", error_msg, QMessageBox.Icon.Warning)
            return
        
        logger.info("数据库连接测试成功")
        
        # 处理服务单Excel文件
        service_dir = CONFIG['paths']['service_dir']
        logger.info(f"从 {service_dir} 目录读取服务单Excel文件")
        
        try:
            # 创建服务单表
            service_table_sql = """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jx_service_orders' AND xtype='U')
                CREATE TABLE jx_service_orders (
                    service_no NVARCHAR(50) PRIMARY KEY,
                    purchase_order_no NVARCHAR(50),
                    customer_expectation NVARCHAR(255),
                    service_status NVARCHAR(50),
                    supplier_id NVARCHAR(50),
                    supplier_store_name NVARCHAR(100),
                    distributor_id NVARCHAR(50),
                    distributor_store_name NVARCHAR(100),
                    product_name NVARCHAR(255),
                    product_quantity INT,
                    purchase_amount DECIMAL(10, 2),
                    customer_name NVARCHAR(50),
                    contact_phone NVARCHAR(50),
                    shipping_address NVARCHAR(255),
                    customer_feedback NVARCHAR(255),
                    created_at DATETIME,
                    return_method NVARCHAR(50),
                    service_reason NVARCHAR(255),
                    return_tracking_no NVARCHAR(50),
                    order_id NVARCHAR(50),
                    sales_store_front NVARCHAR(100),
                    order_type NVARCHAR(50),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            
            # 连接数据库并创建表
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(service_table_sql)
            conn.commit()
            
            # 查找所有xls文件
            files_processed = 0
            total_records = 0
            
            for file in os.listdir(service_dir):
                if file.endswith('.xls') or file.endswith('.xlsx'):
                    file_path = os.path.join(service_dir, file)
                    logger.info(f"处理文件: {file_path}")
                    
                    # 使用pandas读取Excel文件
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    
                    # 字段映射
                    column_mapping = {
                        '采购单号': 'purchase_order_no',
                        '服务单号': 'service_no',
                        '用户期望': 'customer_expectation',
                        '服务单状态': 'service_status',
                        '供应商编号': 'supplier_id',
                        '供应商店铺名称': 'supplier_store_name',
                        '分销商编号': 'distributor_id',
                        '分销商店铺名称': 'distributor_store_name',
                        '产品名称': 'product_name',
                        '产品数量': 'product_quantity',
                        '采购金额': 'purchase_amount',
                        '顾客姓名': 'customer_name',
                        '联系方式': 'contact_phone',
                        '收货地址': 'shipping_address',
                        '用户意见': 'customer_feedback',
                        '服务单创建时间': 'created_at',
                        '返件方式': 'return_method',
                        '申请原因': 'service_reason',
                        '客户寄回物流单号': 'return_tracking_no',
                        '订单号': 'order_id',
                        '前台销售店铺': 'sales_store_front',
                        '订单类型': 'order_type'
                    }
                    
                    # 重命名列
                    for old_col, new_col in column_mapping.items():
                        if old_col in df.columns:
                            df.rename(columns={old_col: new_col}, inplace=True)
                    
                    # 确保服务单号列存在
                    if 'service_no' not in df.columns:
                        logger.error(f"文件 {file} 缺少服务单号列，跳过")
                        continue
                    
                    # 如果数据为空，跳过
                    if df.empty:
                        logger.warning(f"文件 {file} 中没有数据，跳过")
                        continue
                    
                    # 收集所有服务单号
                    service_nos = df['service_no'].unique().tolist()
                    
                    # 删除已有的相同服务单号记录
                    if service_nos:
                        placeholders = ','.join(['?' for _ in service_nos])
                        delete_sql = f"DELETE FROM jx_service_orders WHERE service_no IN ({placeholders})"
                        cursor.execute(delete_sql, service_nos)
                        rows_deleted = cursor.rowcount
                        logger.info(f"已删除 {rows_deleted} 条旧服务单记录")
                    
                    # 上传新数据
                    records_count = 0
                    
                    for _, row in df.iterrows():
                        # 准备列名和值
                        columns = [col for col in row.index if col in column_mapping.values() and pd.notna(row[col])]
                        values = [row[col] for col in columns]
                        
                        # 跳过没有服务单号的记录
                        if 'service_no' not in columns or not values[columns.index('service_no')]:
                            continue
                        
                        # 构建SQL
                        column_str = ', '.join(columns)
                        placeholders = ', '.join(['?' for _ in columns])
                        sql = f"INSERT INTO jx_service_orders ({column_str}) VALUES ({placeholders})"
                        
                        try:
                            cursor.execute(sql, values)
                            records_count += 1
                        except Exception as e:
                            logger.error(f"插入记录时出错: {str(e)}")
                    
                    # 提交事务
                    conn.commit()
                    logger.info(f"文件 {file} 处理完成，已上传 {records_count} 条记录")
                    total_records += records_count
                    files_processed += 1
            
            # 关闭连接
            conn.close()
            
            if files_processed > 0:
                success_msg = f"服务单上传完成，共处理 {files_processed} 个文件，上传 {total_records} 条记录"
                logger.info(success_msg)
                self.window.show_message("上传成功", success_msg)
            else:
                logger.warning("没有找到服务单文件")
                self.window.show_message("上传提示", "没有找到可上传的服务单文件", QMessageBox.Icon.Information)
                
        except Exception as e:
            error_msg = f"上传服务单时发生错误: {str(e)}"
            logger.error(error_msg)
            self.window.show_message("上传失败", error_msg, QMessageBox.Icon.Critical)
    
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
            # 从函数加载数据库配置
            db_config = load_db_config()
            
            # 检查配置是否为空
            if not db_config:
                logger.warning("数据库配置不存在或为空")
                return
            
            # 更新数据库管理器的连接参数
            self.db_manager = DatabaseManager(
                server=db_config.get('server', ''),
                database=db_config.get('database', ''),
                username=db_config.get('username', ''),
                password=db_config.get('password', ''),
                batch_size=db_config.get('batch_size', '100'),
                timeout=db_config.get('timeout', '30')
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