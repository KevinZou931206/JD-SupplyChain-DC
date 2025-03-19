from PyQt6.QtWidgets import (QMainWindow, QDateEdit, QPushButton, QLabel, QMessageBox, 
                           QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QComboBox, 
                           QLineEdit, QTextEdit, QGridLayout, QFormLayout, QScrollArea,
                           QGroupBox, QSplitter, QFrame)
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QPalette
import os
import json
import logging

logger = logging.getLogger('UI.MainWindow')

class MainWindow(QMainWindow):
    # 定义信号
    login_signal = pyqtSignal(str)  # 传递选中的账号名称
    generate_signal = pyqtSignal(str, str, str)  # 开始日期、结束日期、账号名称
    download_signal = pyqtSignal(str)  # 账号名称
    upload_signal = pyqtSignal()
    clear_cache_signal = pyqtSignal()
    save_config_signal = pyqtSignal(dict)  # 配置信息
    delete_config_signal = pyqtSignal(str)  # 账号名称
    update_db_config_signal = pyqtSignal()  # 数据库配置更新信号
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_accounts()
        
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('京东供销平台数据采集工具')
        self.setGeometry(300, 300, 800, 600)
        
        # 创建标签页控件
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 创建三个标签页
        self.main_tab = QWidget()
        self.config_tab = QWidget()
        self.about_tab = QWidget()
        self.db_config_tab = QWidget()
        
        # 添加标签页到标签页控件
        self.tabs.addTab(self.main_tab, "主程序")
        self.tabs.addTab(self.config_tab, "配置信息")
        self.tabs.addTab(self.db_config_tab, "数据库配置")
        self.tabs.addTab(self.about_tab, "关于")
        
        # 初始化各个标签页的内容
        self.init_main_tab()
        self.init_config_tab()
        self.init_db_config_tab()
        self.init_about_tab()
    
    def init_main_tab(self):
        # 主页面布局
        main_layout = QVBoxLayout(self.main_tab)
        
        # 1. 账号信息部分
        account_group = QGroupBox("账号信息")
        account_layout = QGridLayout()
        
        # 账号选择控件
        self.account_label = QLabel("选择账号:")
        self.account_combo = QComboBox()
        self.account_combo.currentTextChanged.connect(self.on_account_changed)
        
        # 账号信息显示区域
        self.account_info_label = QLabel("账号名称:")
        self.account_name_value = QLabel("")
        self.merchant_id_label = QLabel("商家ID:")
        self.merchant_id_value = QLabel("")
        self.store_name_label = QLabel("店铺名称:")
        self.store_name_value = QLabel("")
        
        # 生成登录缓存按钮
        self.login_button = QPushButton("生成登录缓存")
        self.login_button.clicked.connect(self.on_login_clicked)
        
        # 添加控件到布局
        account_layout.addWidget(self.account_label, 0, 0)
        account_layout.addWidget(self.account_combo, 0, 1, 1, 3)
        account_layout.addWidget(self.account_info_label, 1, 0)
        account_layout.addWidget(self.account_name_value, 1, 1)
        account_layout.addWidget(self.merchant_id_label, 1, 2)
        account_layout.addWidget(self.merchant_id_value, 1, 3)
        account_layout.addWidget(self.store_name_label, 2, 0)
        account_layout.addWidget(self.store_name_value, 2, 1)
        account_layout.addWidget(self.login_button, 3, 0, 1, 4)
        
        account_group.setLayout(account_layout)
        main_layout.addWidget(account_group)
        
        # 2. 功能模块部分
        function_group = QGroupBox("功能模块")
        function_layout = QGridLayout()
        
        # 日期选择控件
        self.start_date_label = QLabel("开始日期:")
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-7))  # 默认为7天前
        self.start_date.setCalendarPopup(True)
        
        self.end_date_label = QLabel("结束日期:")
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        # 功能按钮
        self.generate_button = QPushButton("生成订单列表")
        self.generate_button.clicked.connect(self.on_generate_clicked)
        
        self.download_button = QPushButton("下载订单列表")
        self.download_button.clicked.connect(self.on_download_clicked)
        
        self.upload_button = QPushButton("上传到数据库")
        self.upload_button.clicked.connect(self.on_upload_clicked)
        
        self.clear_button = QPushButton("清理缓存")
        self.clear_button.clicked.connect(self.on_clear_cache_clicked)
        
        # 初始禁用需要登录才能使用的按钮
        self.generate_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.upload_button.setEnabled(False)
        
        # 添加控件到布局
        function_layout.addWidget(self.start_date_label, 0, 0)
        function_layout.addWidget(self.start_date, 0, 1)
        function_layout.addWidget(self.end_date_label, 0, 2)
        function_layout.addWidget(self.end_date, 0, 3)
        function_layout.addWidget(self.generate_button, 1, 0, 1, 2)
        function_layout.addWidget(self.download_button, 1, 2, 1, 2)
        function_layout.addWidget(self.upload_button, 2, 0, 1, 2)
        function_layout.addWidget(self.clear_button, 2, 2, 1, 2)
        
        function_group.setLayout(function_layout)
        main_layout.addWidget(function_group)
        
        # 3. 运行日志部分
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # 设置各组件的比例
        main_layout.setStretch(0, 2)  # 账号信息
        main_layout.setStretch(1, 2)  # 功能模块
        main_layout.setStretch(2, 5)  # 运行日志
    
    def init_config_tab(self):
        # 配置页面布局
        config_layout = QVBoxLayout(self.config_tab)
        
        # 1. 账号选择区域
        select_group = QGroupBox("选择/新建账号")
        select_layout = QHBoxLayout()
        
        self.config_account_label = QLabel("账号:")
        self.config_account_combo = QComboBox()
        self.config_account_combo.setEditable(True)
        self.config_account_combo.currentTextChanged.connect(self.on_config_account_changed)
        
        select_layout.addWidget(self.config_account_label)
        select_layout.addWidget(self.config_account_combo)
        
        select_group.setLayout(select_layout)
        config_layout.addWidget(select_group)
        
        # 2. 信息录入/修改区域
        info_group = QGroupBox("信息录入/修改")
        info_layout = QFormLayout()
        
        self.account_name_edit = QLineEdit()
        self.account_password_edit = QLineEdit()
        self.account_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.merchant_id_edit = QLineEdit()
        self.store_name_edit = QLineEdit()
        
        info_layout.addRow("账号名称:", self.account_name_edit)
        info_layout.addRow("账号密码:", self.account_password_edit)
        info_layout.addRow("商家ID:", self.merchant_id_edit)
        info_layout.addRow("店铺名称:", self.store_name_edit)
        
        info_group.setLayout(info_layout)
        config_layout.addWidget(info_group)
        
        # 3. 操作按钮
        button_layout = QHBoxLayout()
        
        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.clicked.connect(self.on_save_config_clicked)
        
        self.delete_config_button = QPushButton("删除配置")
        self.delete_config_button.clicked.connect(self.on_delete_config_clicked)
        
        button_layout.addWidget(self.save_config_button)
        button_layout.addWidget(self.delete_config_button)
        
        config_layout.addLayout(button_layout)
        
        # 设置各组件的比例
        config_layout.setStretch(0, 1)  # 账号选择
        config_layout.setStretch(1, 4)  # 信息录入
        config_layout.setStretch(2, 1)  # 操作按钮
    
    def init_db_config_tab(self):
        """初始化数据库配置标签页"""
        # 数据库配置页面布局
        db_config_layout = QFormLayout(self.db_config_tab)
        
        # 添加说明标签
        db_intro_label = QLabel("请配置数据库连接信息，所有数据将上传至此数据库", self.db_config_tab)
        db_intro_label.setWordWrap(True)
        db_config_layout.addRow(db_intro_label)
        
        # 安全提示
        security_label = QLabel("⚠️ 安全提示：数据库配置信息将保存在单独的JSON文件中，请确保文件安全", self.db_config_tab)
        security_label.setWordWrap(True)
        security_label.setStyleSheet("color: red;")
        db_config_layout.addRow(security_label)
        
        # 添加分隔线
        line = QFrame(self.db_config_tab)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        db_config_layout.addRow(line)
        
        # 创建表单字段
        self.db_server_edit = QLineEdit(self.db_config_tab)
        self.db_name_edit = QLineEdit(self.db_config_tab)
        self.db_user_edit = QLineEdit(self.db_config_tab)
        self.db_password_edit = QLineEdit(self.db_config_tab)
        self.db_password_edit.setEchoMode(QLineEdit.EchoMode.Password)  # 密码模式
        self.db_batch_size_edit = QLineEdit(self.db_config_tab)
        self.db_batch_size_edit.setText("100")  # 默认值
        self.db_timeout_edit = QLineEdit(self.db_config_tab)
        self.db_timeout_edit.setText("30")  # 默认值
        
        # 添加到表单
        db_config_layout.addRow("服务器地址:", self.db_server_edit)
        db_config_layout.addRow("数据库名称:", self.db_name_edit)
        db_config_layout.addRow("用户名:", self.db_user_edit)
        db_config_layout.addRow("密码:", self.db_password_edit)
        db_config_layout.addRow("批处理大小:", self.db_batch_size_edit)
        db_config_layout.addRow("超时时间(秒):", self.db_timeout_edit)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        # 保存按钮
        self.save_db_config_button = QPushButton("保存配置", self.db_config_tab)
        self.save_db_config_button.clicked.connect(self.on_save_db_config_clicked)
        
        # 测试连接按钮
        self.test_db_connection_button = QPushButton("测试连接", self.db_config_tab)
        self.test_db_connection_button.clicked.connect(self.on_test_db_connection_clicked)
        
        # 查看数据结构按钮
        self.view_db_schema_button = QPushButton("查看表结构", self.db_config_tab)
        self.view_db_schema_button.clicked.connect(self.on_view_db_schema_clicked)
        
        # 添加按钮到布局
        buttons_layout.addWidget(self.save_db_config_button)
        buttons_layout.addWidget(self.test_db_connection_button)
        buttons_layout.addWidget(self.view_db_schema_button)
        
        db_config_layout.addRow(buttons_layout)
        
        # 添加表结构显示区域
        schema_group = QGroupBox("数据库表结构", self.db_config_tab)
        schema_layout = QVBoxLayout(schema_group)
        
        self.schema_text = QTextEdit(schema_group)
        self.schema_text.setReadOnly(True)
        self.schema_text.setMinimumHeight(200)
        self.schema_text.setPlaceholderText("点击「查看表结构」按钮查看数据库表结构...")
        schema_layout.addWidget(self.schema_text)
        
        db_config_layout.addRow(schema_group)
        
        # 尝试加载现有配置
        self.load_db_config()
    
    def load_accounts(self):
        """加载所有配置的账号"""
        try:
            config_file = 'accounts.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
                
                # 清空现有账号
                self.account_combo.clear()
                self.config_account_combo.clear()
                
                # 添加账号到选择框
                for account_name in accounts.keys():
                    self.account_combo.addItem(account_name)
                    self.config_account_combo.addItem(account_name)
                
                logger.info(f"已加载 {len(accounts)} 个账号配置")
        except Exception as e:
            logger.error(f"加载账号配置失败: {str(e)}")
            self.show_message("错误", f"加载账号配置失败: {str(e)}", QMessageBox.Icon.Critical)
    
    def on_account_changed(self, account_name):
        """当主程序标签页的账号选择改变时调用"""
        if not account_name:
            return
            
        try:
            config_file = 'accounts.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
                
                if account_name in accounts:
                    account_info = accounts[account_name]
                    self.account_name_value.setText(account_name)
                    self.merchant_id_value.setText(account_info.get('merchant_id', ''))
                    self.store_name_value.setText(account_info.get('store_name', ''))
                    logger.info(f"已加载账号 {account_name} 的信息")
        except Exception as e:
            logger.error(f"加载账号 {account_name} 信息失败: {str(e)}")
    
    def on_config_account_changed(self, account_name):
        """当配置标签页的账号选择改变时调用"""
        if not account_name:
            return
            
        try:
            config_file = 'accounts.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
                
                # 如果是已存在的账号，加载信息
                if account_name in accounts:
                    account_info = accounts[account_name]
                    self.account_name_edit.setText(account_name)
                    self.account_password_edit.setText(account_info.get('password', ''))
                    self.merchant_id_edit.setText(account_info.get('merchant_id', ''))
                    self.store_name_edit.setText(account_info.get('store_name', ''))
                    logger.info(f"已加载账号 {account_name} 的配置信息")
                else:
                    # 新账号，清空输入框
                    self.account_name_edit.setText(account_name)
                    self.account_password_edit.setText('')
                    self.merchant_id_edit.setText('')
                    self.store_name_edit.setText('')
                    logger.info(f"准备创建新账号 {account_name}")
        except Exception as e:
            logger.error(f"加载账号 {account_name} 配置信息失败: {str(e)}")
    
    def on_login_clicked(self):
        """登录按钮点击事件"""
        account_name = self.account_combo.currentText()
        if not account_name:
            self.show_message("错误", "请先选择一个账号", QMessageBox.Icon.Warning)
            return
            
        self.login_signal.emit(account_name)
    
    def on_generate_clicked(self):
        """生成订单列表按钮点击事件"""
        account_name = self.account_combo.currentText()
        if not account_name:
            self.show_message("错误", "请先选择一个账号", QMessageBox.Icon.Warning)
            return
            
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        self.generate_signal.emit(start_date, end_date, account_name)
    
    def on_download_clicked(self):
        """下载订单列表按钮点击事件"""
        account_name = self.account_combo.currentText()
        if not account_name:
            self.show_message("错误", "请先选择一个账号", QMessageBox.Icon.Warning)
            return
            
        self.download_signal.emit(account_name)
    
    def on_upload_clicked(self):
        """上传到数据库按钮点击事件"""
        self.upload_signal.emit()
    
    def on_clear_cache_clicked(self):
        """清理缓存按钮点击事件"""
        self.clear_cache_signal.emit()
    
    def on_save_config_clicked(self):
        """保存配置按钮点击事件"""
        account_name = self.account_name_edit.text().strip()
        if not account_name:
            self.show_message("错误", "账号名称不能为空", QMessageBox.Icon.Warning)
            return
            
        password = self.account_password_edit.text()
        merchant_id = self.merchant_id_edit.text()
        store_name = self.store_name_edit.text()
        
        config = {
            'account_name': account_name,
            'password': password,
            'merchant_id': merchant_id,
            'store_name': store_name
        }
        
        self.save_config_signal.emit(config)
    
    def on_delete_config_clicked(self):
        """删除配置按钮点击事件"""
        account_name = self.config_account_combo.currentText()
        if not account_name:
            self.show_message("错误", "请先选择一个账号", QMessageBox.Icon.Warning)
            return
            
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除账号 {account_name} 的配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_config_signal.emit(account_name)
    
    def set_status(self, message):
        """设置状态显示信息"""
        self.log_text.append(message)
        # 滚动到最新内容
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        # 确保更新立即显示
        self.log_text.repaint()
    
    def show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """显示消息对话框"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
        
    def enable_logged_in_features(self, enabled=True):
        """启用/禁用需要登录才能使用的功能"""
        self.generate_button.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
        self.upload_button.setEnabled(enabled)
    
    def add_account_to_combos(self, account_name):
        """向选择框中添加新账号"""
        # 先检查是否已存在
        if self.account_combo.findText(account_name) == -1:
            self.account_combo.addItem(account_name)
        
        if self.config_account_combo.findText(account_name) == -1:
            self.config_account_combo.addItem(account_name)
    
    def remove_account_from_combos(self, account_name):
        """从选择框中移除账号"""
        index = self.account_combo.findText(account_name)
        if index != -1:
            self.account_combo.removeItem(index)
        
        index = self.config_account_combo.findText(account_name)
        if index != -1:
            self.config_account_combo.removeItem(index)
    
    def load_db_config(self):
        """加载现有的数据库配置"""
        try:
            import os
            import json
            from config import load_db_config
            
            # 使用配置加载函数
            db_config = load_db_config()
            
            if db_config:
                # 填充表单
                self.db_server_edit.setText(db_config.get('server', ''))
                self.db_name_edit.setText(db_config.get('database', ''))
                self.db_user_edit.setText(db_config.get('username', ''))
                self.db_password_edit.setText(db_config.get('password', ''))
                self.db_batch_size_edit.setText(db_config.get('batch_size', '100'))
                self.db_timeout_edit.setText(db_config.get('timeout', '30'))
                
                logger.info("已加载数据库配置")
        except Exception as e:
            logger.error(f"加载数据库配置失败: {str(e)}")
    
    def on_test_db_connection_clicked(self):
        """测试数据库连接"""
        db_config = self.get_db_config()
        
        try:
            # 创建临时的数据库管理器
            from modules.database_manager import DatabaseManager
            db_manager = DatabaseManager(
                server=db_config['server'],
                database=db_config['database'],
                username=db_config['username'],
                password=db_config['password']
            )
            
            # 测试连接
            test_result = db_manager.test_connection()
            if test_result.get('success'):
                self.show_message("连接成功", "数据库连接测试成功", QMessageBox.Icon.Information)
            else:
                self.show_message("连接失败", test_result.get('message'), QMessageBox.Icon.Warning)
        except Exception as e:
            logger.error(f"测试数据库连接失败: {str(e)}")
            self.show_message("连接失败", f"数据库连接测试失败: {str(e)}", QMessageBox.Icon.Critical)
    
    def on_view_db_schema_clicked(self):
        """查看数据库表结构"""
        db_config = self.get_db_config()
        
        for key, value in db_config.items():
            if key in ['server', 'database', 'username', 'password'] and not value:
                self.show_message("配置不完整", f"请填写 {key} 字段", QMessageBox.Icon.Warning)
                return
        
        try:
            # 创建临时的数据库管理器
            from modules.database_manager import DatabaseManager
            db_manager = DatabaseManager(
                server=db_config['server'],
                database=db_config['database'],
                username=db_config['username'],
                password=db_config['password']
            )
            
            # 测试连接
            test_result = db_manager.test_connection()
            if not test_result.get('success'):
                self.show_message("连接失败", test_result.get('message'), QMessageBox.Icon.Warning)
                return
            
            # 连接数据库并获取表结构
            import pyodbc
            conn = pyodbc.connect(db_manager.connection_string)
            cursor = conn.cursor()
            
            # 获取主表结构
            schema_text = "=== 订单主表 (jx_orders_master) ===\n\n"
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'jx_orders_master' ORDER BY ORDINAL_POSITION")
            
            for row in cursor.fetchall():
                col_name = row.COLUMN_NAME
                data_type = row.DATA_TYPE
                length = row.CHARACTER_MAXIMUM_LENGTH
                
                if length:
                    schema_text += f"{col_name}: {data_type}({length})\n"
                else:
                    schema_text += f"{col_name}: {data_type}\n"
            
            # 获取明细表结构
            schema_text += "\n\n=== 订单明细表 (jx_orders_detail) ===\n\n"
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'jx_orders_detail' ORDER BY ORDINAL_POSITION")
            
            for row in cursor.fetchall():
                col_name = row.COLUMN_NAME
                data_type = row.DATA_TYPE
                length = row.CHARACTER_MAXIMUM_LENGTH
                
                if length:
                    schema_text += f"{col_name}: {data_type}({length})\n"
                else:
                    schema_text += f"{col_name}: {data_type}\n"
            
            # 获取记录计数
            cursor.execute("SELECT COUNT(*) AS count FROM jx_orders_master")
            master_count = cursor.fetchone().count
            
            cursor.execute("SELECT COUNT(*) AS count FROM jx_orders_detail")
            detail_count = cursor.fetchone().count
            
            schema_text += f"\n\n=== 数据统计 ===\n"
            schema_text += f"主表记录数: {master_count}\n"
            schema_text += f"明细表记录数: {detail_count}\n"
            
            conn.close()
            
            # 显示表结构
            self.schema_text.setText(schema_text)
            logger.info("已查询并显示数据库表结构")
            
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            self.schema_text.setText(f"获取表结构失败: {str(e)}")
            self.show_message("查询失败", f"获取表结构失败: {str(e)}", QMessageBox.Icon.Warning)
    
    def get_db_config(self):
        """获取数据库配置表单的值"""
        return {
            'server': self.db_server_edit.text(),
            'database': self.db_name_edit.text(),
            'username': self.db_user_edit.text(),
            'password': self.db_password_edit.text(),
            'batch_size': self.db_batch_size_edit.text(),
            'timeout': self.db_timeout_edit.text()
        }
    
    def reload_config(self):
        """重新加载配置"""
        import importlib
        import config
        importlib.reload(config)
    
    def init_about_tab(self):
        # 关于页面布局
        about_layout = QVBoxLayout(self.about_tab)
        
        # 创建一个容器widget，用于设置样式和布局
        about_container = QWidget()
        container_layout = QVBoxLayout(about_container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)
        
        # 判断是否为深色模式
        is_dark = self.is_dark_mode()
        
        # 添加标题
        title_label = QLabel("京东供销平台数据采集工具")
        if is_dark:
            title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #e0e0e0;")
        else:
            title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #333333;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title_label)
        
        # 添加版本信息
        version_label = QLabel("版本: 1.0.0")
        if is_dark:
            version_label.setStyleSheet("font-size: 14px; color: #aaaaaa;")
        else:
            version_label.setStyleSheet("font-size: 14px; color: #666666;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(version_label)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        if is_dark:
            line.setStyleSheet("background-color: #555555;")
        else:
            line.setStyleSheet("background-color: #dddddd;")
        container_layout.addWidget(line)
        
        # 添加描述文本
        description = QLabel("本工具用于自动化从京东供销平台获取订单数据，进行数据清洗并上传至SQL Server数据库。")
        description.setWordWrap(True)
        if is_dark:
            description.setStyleSheet("font-size: 14px; color: #e0e0e0; margin: 10px 0;")
        else:
            description.setStyleSheet("font-size: 14px; color: #333333; margin: 10px 0;")
        container_layout.addWidget(description)
        
        # 添加功能特点标题
        features_title = QLabel("功能特点")
        if is_dark:
            features_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0; margin-top: 10px;")
        else:
            features_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333; margin-top: 10px;")
        container_layout.addWidget(features_title)
        
        # 添加功能特点列表
        features_list = QTextEdit()
        features_list.setReadOnly(True)
        if is_dark:
            features_list.setStyleSheet("border: none; background-color: transparent; color: #e0e0e0;")
            text_color = "#e0e0e0"
        else:
            features_list.setStyleSheet("border: none; background-color: transparent; color: #333333;")
            text_color = "#333333"
        
        features_list.setHtml(f"""
        <ul style="margin-left: 15px; color: {text_color};">
            <li style="margin-bottom: 8px;">自动化登录京东供销平台，处理滑动验证场景</li>
            <li style="margin-bottom: 8px;">按日期范围采集订单数据并下载</li>
            <li style="margin-bottom: 8px;">自动清洗Excel数据，进行格式转换和字段标准化</li>
            <li style="margin-bottom: 8px;">支持将数据上传到SQL Server数据库，自动处理重复键</li>
            <li style="margin-bottom: 8px;">详细记录程序运行过程，便于追踪和调试</li>
        </ul>
        """)
        features_list.setMaximumHeight(150)
        container_layout.addWidget(features_list)
        
        # 添加版权信息
        copyright_label = QLabel("© 2025 KevinZou 版权所有")
        if is_dark:
            copyright_label.setStyleSheet("font-size: 12px; color: #aaaaaa; margin-top: 15px;")
        else:
            copyright_label.setStyleSheet("font-size: 12px; color: #888888; margin-top: 15px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(copyright_label)
        
        # 添加弹性空间
        container_layout.addStretch(1)
        
        # 将容器添加到滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(about_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # 将滚动区域添加到主布局
        about_layout.addWidget(scroll_area)
    
    def is_dark_mode(self):
        """检测是否为深色模式"""
        palette = self.palette()
        background_color = palette.color(QPalette.ColorRole.Window)
        # 如果背景色较暗，则认为是深色模式
        return background_color.lightness() < 128
    
    def apply_theme(self):
        """应用主题样式"""
        # 已移除全局样式应用，仅在关于页面适配深色模式 
    
    def on_save_db_config_clicked(self):
        """保存数据库配置"""
        db_config = self.get_db_config()
        
        # 验证配置是否填写完整
        for key, value in db_config.items():
            if key in ['server', 'database', 'username', 'password'] and not value:
                self.show_message("配置不完整", f"请填写 {key} 字段", QMessageBox.Icon.Warning)
                return
        
        try:
            import os
            import json
            
            # 获取程序所在目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_config_path = os.path.join(base_dir, 'database_config.json')
            
            # 将配置保存到JSON文件
            with open(db_config_path, 'w', encoding='utf-8') as f:
                json.dump(db_config, f, ensure_ascii=False, indent=4)
            
            # 发送数据库配置更新信号
            self.update_db_config_signal.emit()
            
            logger.info("数据库配置已保存")
            self.show_message("保存成功", "数据库配置已成功保存")
        except Exception as e:
            logger.error(f"保存数据库配置失败: {str(e)}")
            self.show_message("保存失败", f"数据库配置保存失败: {str(e)}", QMessageBox.Icon.Critical) 