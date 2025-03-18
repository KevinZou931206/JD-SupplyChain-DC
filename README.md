# JD供销平台数据采集与处理系统开发文档

## 一、项目概述

本系统用于自动化从京东供销平台获取订单数据，进行数据清洗并上传至SQL Server数据库，通过QT6构建友好的用户界面，提高数据处理效率。

## 二、技术栈

- Python 3.10
- PyQt6
- Selenium WebDriver
- pandas
- pyodbc/SQLAlchemy
- requests

## 三、系统架构

### 3.1 模块组成

- **UI模块**：基于PyQt6构建用户界面
- **网络请求模块**：处理HTTP请求与响应
- **浏览器自动化模块**：使用Selenium控制Chrome浏览器
- **数据处理模块**：使用pandas清洗Excel数据
- **数据库交互模块**：连接与操作SQL Server

### 3.2 数据流程

1. 用户登录 → 获取Cookies
2. 用户设置日期 → 生成订单数据
3. 下载订单数据 → 数据清洗 → 数据上传
4. 清理缓存

## 四、功能模块详细设计

### 4.1 用户界面模块

```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QDateEdit, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import QDate

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('京东供销平台数据采集工具')
        self.setGeometry(300, 300, 600, 400)
        
        # 日期选择控件
        self.start_date_label = QLabel('开始日期:', self)
        self.start_date_label.move(20, 20)
        self.start_date = QDateEdit(self)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.move(100, 20)
        
        self.end_date_label = QLabel('结束日期:', self)
        self.end_date_label.move(20, 60)
        self.end_date = QDateEdit(self)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.move(100, 60)
        
        # 功能按钮
        self.login_button = QPushButton('登录京东', self)
        self.login_button.move(20, 100)
        self.login_button.clicked.connect(self.login_jd)
        
        self.generate_button = QPushButton('生成订单列表', self)
        self.generate_button.move(20, 140)
        self.generate_button.clicked.connect(self.generate_order_list)
        
        self.download_button = QPushButton('下载订单列表', self)
        self.download_button.move(20, 180)
        self.download_button.clicked.connect(self.download_order_list)
        
        self.upload_button = QPushButton('上传到数据库', self)
        self.upload_button.move(20, 220)
        self.upload_button.clicked.connect(self.upload_to_database)
        
        self.clear_button = QPushButton('清除缓存', self)
        self.clear_button.move(20, 260)
        self.clear_button.clicked.connect(self.clear_cache)
        
        # 状态显示区域
        self.status_label = QLabel('就绪', self)
        self.status_label.setGeometry(20, 300, 560, 80)
```

### 4.2 浏览器自动化模块

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import json
import time

class BrowserAutomation:
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.cookie_path = os.path.join(cache_dir, 'cookies.json')
        self.driver = None
        
    def init_browser(self):
        """初始化Chrome浏览器"""
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def login(self):
        """自动登录京东供销平台"""
        if self.driver is None:
            self.init_browser()
            
        self.driver.get('https://gongxiao.jd.com/vender/home')
        
        # 检查登录方式
        try:
            login_mode = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div[1]/div/div/div/div/div[1]/span'))
            ).text
            
            if login_mode == "密码登录":
                # 当前是扫码登录，点击切换到密码登录
                self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/div/div/div/div[1]/img').click()
            
            # 输入账号密码
            self.driver.find_element(By.XPATH, '//*[@id="loginname"]').send_keys('用户名')
            self.driver.find_element(By.XPATH, '//*[@id="el-id-4159-127"]').send_keys('密码')
            self.driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/div/div/div/div/div[3]/div/div[1]/form/div[4]/div/button').click()
            
            # 检查是否需要滑动验证
            try:
                slide_verify = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="JDJRV-wrap-passwordLoginSlideValidate"]'))
                )
                # 提示用户手动完成验证
                return "需要手动验证"
            except:
                pass
                
            # 等待登录成功
            WebDriverWait(self.driver, 30).until(
                EC.url_contains('gongxiao.jd.com/vender/home')
            )
            
            # 保存cookies
            self.save_cookies()
            return "登录成功"
            
        except Exception as e:
            return f"登录失败: {str(e)}"
    
    def save_cookies(self):
        """保存cookies到本地"""
        cookies = self.driver.get_cookies()
        with open(self.cookie_path, 'w') as f:
            json.dump(cookies, f)
```

### 4.3 网络请求模块

```python
import requests
import json
import os
from datetime import datetime

class ApiClient:
    def __init__(self, cache_dir='./cache', download_dir='./Downloads'):
        self.cache_dir = cache_dir
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        self.cookie_path = os.path.join(cache_dir, 'cookies.json')
        self.cookies = self.load_cookies()
        
    def load_cookies(self):
        """从文件加载cookies"""
        if os.path.exists(self.cookie_path):
            with open(self.cookie_path, 'r') as f:
                return {cookie['name']: cookie['value'] for cookie in json.load(f)}
        return {}
    
    def generate_order_list(self, start_time, end_time):
        """生成订单列表"""
        url = "https://api.m.jd.com/api"
        
        params = {
            "functionId": "api_order_export",
            "scval": "all",
            "loginType": "3",
            "appid": "gx-pc",
            "client": "pc",
            "t": str(int(datetime.now().timestamp() * 1000))
        }
        
        headers = {
            "authority": "api.m.jd.com",
            "method": "POST",
            "path": f"/api?functionId=api_order_export&scval=all&loginType=3&appid=gx-pc&client=pc&t={params['t']}",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://gongxiao.jd.com",
            "referer": "https://gongxiao.jd.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "x-referer-page": "https://gongxiao.jd.com/vender/home",
            "x-requested-with": "XMLHttpRequest",
            "x-rp-client": "h5_1.0.0"
        }
        
        data = {
            "body": json.dumps({
                "timeType": 1,
                "states": [],
                "startTime": start_time,
                "endTime": end_time
            }),
            "x-api-eid-token": "jdd03QW24EQMHXNUJSC646HJ263AQBTBWNYTS4GKAMXTDBCSXO5ZOGZWHAQGWNPXSLFGVB432DCKPOJPGO3RKUNBTUG644QAAAAMVU4KJG7AAAAAADN3OOCKQ22IJMIX",
            "ext": json.dumps({"requestSource":"color"})
        }
        
        response = requests.post(url, params=params, headers=headers, cookies=self.cookies, data=data)
        return response.json()
    
    def download_order_list(self):
        """下载订单列表"""
        url = "https://gmall.jd.com/api/batchTask/list"
        
        headers = {
            "authority": "gmall.jd.com",
            "method": "POST",
            "path": "/api/batchTask/list",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json",
            "origin": "https://gongxiao.jd.com",
            "referer": "https://gongxiao.jd.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        
        data = {
            "taskType": 18,
            "page": {
                "current": 1,
                "pageSize": 10
            }
        }
        
        response = requests.post(url, headers=headers, cookies=self.cookies, json=data)
        resp_json = response.json()
        
        if resp_json.get('success') and resp_json.get('data', {}).get('rows'):
            file_url = resp_json['data']['rows'][0]['targetFile']
            file_name = file_url.split('/')[-1]
            
            # 下载文件
            download_response = requests.get(file_url)
            file_path = os.path.join(self.download_dir, file_name)
            
            with open(file_path, 'wb') as f:
                f.write(download_response.content)
                
            return {"success": True, "file_path": file_path}
        
        return {"success": False, "message": "未找到可下载的文件"}
```

### 4.4 数据处理模块

```python
import pandas as pd
import os
import glob

class DataProcessor:
    def __init__(self, download_dir='./Downloads'):
        self.download_dir = download_dir
        
    def process_excel_files(self):
        """处理下载的Excel文件"""
        excel_files = glob.glob(os.path.join(self.download_dir, '*.xls'))
        if not excel_files:
            excel_files = glob.glob(os.path.join(self.download_dir, '*.xlsx'))
            
        if not excel_files:
            return {"success": False, "message": "未找到Excel文件"}
            
        processed_data = []
        
        for file_path in excel_files:
            try:
                # 读取Excel文件
                df = pd.read_excel(file_path)
                
                # 字段映射
                column_mapping = {
                    '订单编号': 'order_id',
                    '采购单号': 'purchase_order_no',
                    '换货单的原始订单编号': 'exchange_original_order_id',
                    '订单状态': 'status',
                    '订单锁定状态': 'lock_status',
                    '供应商编号': 'supplier_id',
                    '供应商商家名称': 'supplier_name',
                    '供应商店铺名称': 'supplier_store_name',
                    '分销商编号': 'distributor_id',
                    '分销商商家名称': 'distributor_name',
                    '分销商店铺名称': 'distributor_store_name',
                    '运费': 'shipping_fee',
                    '收货人姓名': 'receiver_name',
                    '联系方式': 'contact_phone',
                    '收货地址': 'shipping_address',
                    '订单备注': 'order_remark',
                    '订单创建时间': 'created_at',
                    '订单出库时间': 'outbound_at',
                    '订单完成时间': 'completed_at',
                    '订单取消时间': 'canceled_at',
                    '是否京仓': 'is_jd_warehouse',
                    '产品名称': 'product_name',
                    '产品颜色': 'product_color',
                    '产品尺码': 'product_size',
                    '商家SKU': 'merchant_sku',
                    '父SKU': 'parent_sku',
                    '子SKU': 'child_sku',
                    '产品采购价': 'purchase_price',
                    '采购数量': 'purchase_quantity',
                    '采购单支付状态': 'payment_status',
                    '采购单支付时间': 'paid_at',
                    '采购单支付模式': 'payment_method',
                    '采购单应付采购款': 'payable_amount',
                    '采购单实际支付总额': 'actual_payment',
                    '订单类型': 'order_type',
                    '用户实际支付总额': 'user_payment_total',
                    '指定承运商': 'carrier',
                    '物流运单号': 'tracking_number',
                    '一盘货商品序列号': 'inventory_serial_number',
                    '下单立减—政府补贴': 'gov_subsidy_instant_order',
                    '京东支付立减-政府补贴': 'gov_subsidy_jd_payment',
                    '云闪付支付立减-政府补贴': 'gov_subsidy_unionpay',
                    '建行支付立减-政府补贴': 'gov_subsidy_ccb',
                    '前台销售店铺': 'sales_store_front'
                }
                
                # 重命名列名
                df = df.rename(columns=column_mapping)
                
                # 清洗数据
                # 1. 处理缺失值
                df = df.fillna('')
                
                # 2. 处理日期格式
                date_columns = ['created_at', 'outbound_at', 'completed_at', 'canceled_at', 'paid_at']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                
                processed_data.append(df)
            
            except Exception as e:
                return {"success": False, "message": f"处理文件 {os.path.basename(file_path)} 时出错: {str(e)}"}
        
        # 合并所有处理后的数据
        if processed_data:
            combined_data = pd.concat(processed_data, ignore_index=True)
            return {"success": True, "data": combined_data}
        else:
            return {"success": False, "message": "没有数据被处理"}
```

### 4.5 数据库交互模块

```python
import pyodbc
import pandas as pd
from sqlalchemy import create_engine

class DatabaseManager:
    def __init__(self, server, database, username, password):
        self.connection_string = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        self.conn_str_sqlalchemy = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver=SQL+Server'
        
    def upload_data(self, df, table_name):
        """上传数据到SQL Server数据库"""
        try:
            # 使用SQLAlchemy创建引擎
            engine = create_engine(self.conn_str_sqlalchemy)
            
            # 上传数据，如果存在则替换
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            
            return {"success": True, "message": f"成功上传 {len(df)} 条数据到 {table_name} 表"}
        
        except Exception as e:
            return {"success": False, "message": f"数据库上传失败: {str(e)}"}
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            conn = pyodbc.connect(self.connection_string)
            conn.close()
            return {"success": True, "message": "数据库连接成功"}
        except Exception as e:
            return {"success": False, "message": f"数据库连接失败: {str(e)}"}
```

### 4.6 缓存管理模块

```python
import os
import glob
import shutil

class CacheManager:
    def __init__(self, cache_dir='./cache', download_dir='./Downloads'):
        self.cache_dir = cache_dir
        self.download_dir = download_dir
        
    def clear_cache(self):
        """清除缓存和下载文件"""
        try:
            # 清除缓存文件
            if os.path.exists(self.cache_dir):
                cookie_file = os.path.join(self.cache_dir, 'cookies.json')
                if os.path.exists(cookie_file):
                    os.remove(cookie_file)
            
            # 清除下载文件夹中的所有文件
            if os.path.exists(self.download_dir):
                for file in glob.glob(os.path.join(self.download_dir, '*.*')):
                    os.remove(file)
                    
            return {"success": True, "message": "缓存清除成功"}
            
        except Exception as e:
            return {"success": False, "message": f"缓存清除失败: {str(e)}"}
```

### 4.7 主程序模块

```python
import sys
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox
from PyQt6.QtCore import QDate, Qt
from datetime import datetime

class VerificationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("验证提醒")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        message = QLabel("请完成浏览器中的滑动验证，完成后点击确定继续。")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        
        self.setLayout(layout)

class MainApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.browser = BrowserAutomation()
        self.api_client = ApiClient()
        self.data_processor = DataProcessor()
        self.db_manager = DatabaseManager(
            server='your_server',
            database='your_database',
            username='your_username',
            password='your_password'
        )
        self.cache_manager = CacheManager()
        
        self.connect_signals()
        
    def connect_signals(self):
        """连接UI信号到处理函数"""
        self.window.login_button.clicked.connect(self.login_jd)
        self.window.generate_button.clicked.connect(self.generate_order_list)
        self.window.download_button.clicked.connect(self.download_order_list)
        self.window.upload_button.clicked.connect(self.upload_to_database)
        self.window.clear_button.clicked.connect(self.clear_cache)
        
    def login_jd(self):
        """登录京东"""
        self.window.status_label.setText("正在登录...")
        result = self.browser.login()
        
        if result == "需要手动验证":
            # 显示验证对话框
            dialog = VerificationDialog(self.window)
            dialog.exec()
            # 用户完成验证后继续
            self.window.status_label.setText("登录成功")
        else:
            self.window.status_label.setText(result)
    
    def generate_order_list(self):
        """生成订单列表"""
        start_date = self.window.start_date.date().toString("yyyy-MM-dd")
        end_date = self.window.end_date.date().toString("yyyy-MM-dd")
        
        start_time = f"{start_date} 00:00:00"
        end_time = f"{end_date} 23:59:59"
        
        self.window.status_label.setText("正在生成订单列表...")
        
        result = self.api_client.generate_order_list(start_time, end_time)
        
        if result.get('success'):
            total_num = result.get('data', {}).get('totalNum', 0)
            self.window.status_label.setText(f"生成订单列表成功，共 {total_num} 条数据")
        else:
            self.window.status_label.setText(f"生成订单列表失败: {result.get('message', '未知错误')}")
    
    def download_order_list(self):
        """下载订单列表"""
        self.window.status_label.setText("正在下载订单列表...")
        
        result = self.api_client.download_order_list()
        
        if result.get('success'):
            self.window.status_label.setText(f"下载订单列表成功，文件保存在: {result.get('file_path')}")
        else:
            self.window.status_label.setText(f"下载订单列表失败: {result.get('message')}")
    
    def upload_to_database(self):
        """数据处理与上传"""
        self.window.status_label.setText("正在处理数据...")
        
        process_result = self.data_processor.process_excel_files()
        
        if process_result.get('success'):
            self.window.status_label.setText("数据处理成功，正在上传到数据库...")
            
            upload_result = self.db_manager.upload_data(
                process_result.get('data'),
                'jd_orders'  # 数据库表名
            )
            
            self.window.status_label.setText(upload_result.get('message'))
        else:
            self.window.status_label.setText(f"数据处理失败: {process_result.get('message')}")
    
    def clear_cache(self):
        """清除缓存"""
        self.window.status_label.setText("正在清除缓存...")
        
        result = self.cache_manager.clear_cache()
        self.window.status_label.setText(result.get('message'))
    
    def run(self):
        """运行应用程序"""
        self.window.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = MainApp()
    app.run()
```

## 五、数据库设计

### 5.1 表结构

```sql
CREATE TABLE jd_orders (
    order_id NVARCHAR(50) PRIMARY KEY,
    purchase_order_no NVARCHAR(50),
    exchange_original_order_id NVARCHAR(50),
    status NVARCHAR(50),
    lock_status NVARCHAR(50),
    supplier_id NVARCHAR(50),
    supplier_name NVARCHAR(100),
    supplier_store_name NVARCHAR(100),
    distributor_id NVARCHAR(50),
    distributor_name NVARCHAR(100),
    distributor_store_name NVARCHAR(100),
    shipping_fee DECIMAL(10, 2),
    receiver_name NVARCHAR(50),
    contact_phone NVARCHAR(50),
    shipping_address NVARCHAR(255),
    order_remark NVARCHAR(255),
    created_at DATETIME,
    outbound_at DATETIME,
    completed_at DATETIME,
    canceled_at DATETIME,
    is_jd_warehouse NVARCHAR(10),
    product_name NVARCHAR(255),
    product_color NVARCHAR(50),
    product_size NVARCHAR(50),
    merchant_sku NVARCHAR(50),
    parent_sku NVARCHAR(50),
    child_sku NVARCHAR(50),
    purchase_price DECIMAL(10, 2),
    purchase_quantity INT,
    payment_status NVARCHAR(50),
    paid_at DATETIME,
    payment_method NVARCHAR(50),
    payable_amount DECIMAL(10, 2),
    actual_payment DECIMAL(10, 2),
    order_type NVARCHAR(50),
    user_payment_total DECIMAL(10, 2),
    carrier NVARCHAR(100),
    tracking_number NVARCHAR(100),
    inventory_serial_number NVARCHAR(100),
    gov_subsidy_instant_order DECIMAL(10, 2),
    gov_subsidy_jd_payment DECIMAL(10, 2),
    gov_subsidy_unionpay DECIMAL(10, 2),
    gov_subsidy_ccb DECIMAL(10, 2),
    sales_store_front NVARCHAR(100)
);
```

## 六、部署说明

### 6.1 环境准备

```
# 依赖包安装
pip install PyQt6 selenium pandas pyodbc sqlalchemy requests

# Chrome WebDriver 安装
# 请下载与您的Chrome版本匹配的WebDriver
# https://chromedriver.chromium.org/downloads
```

### 6.2 配置文件

```python
# config.py
CONFIG = {
    'db': {
        'server': 'your_server',
        'database': 'your_database',
        'username': 'your_username',
        'password': 'your_password'
    },
    'paths': {
        'cache_dir': './cache',
        'download_dir': './Downloads'
    },
    'jd': {
        'username': 'your_jd_username',
        'password': 'your_jd_password'
    }
}
```

### 6.3 打包说明

```
# 使用PyInstaller打包成可执行文件
pip install pyinstaller
pyinstaller --onefile --windowed --icon=app.ico main.py
```

## 七、测试计划

1. 登录功能测试
2. 订单生成功能测试 
3. 订单下载功能测试
4. 数据处理功能测试
5. 数据库上传功能测试
6. 缓存清理功能测试
7. UI交互测试
8. 异常处理测试

## 八、安全与注意事项

1. 账号密码不要硬编码在源代码中
2. 定期修改登录密码
3. 使用环境变量或配置文件存储敏感信息
4. 请勿在公共网络使用此工具
5. 定期备份数据库 

## 版本控制说明

本项目使用Git进行版本控制，已完成初始化配置。主要分支为`main`，作为稳定版本分支。

### 常用Git命令

```bash
# 查看当前状态
git status

# 添加修改到暂存区
git add .                   # 添加所有文件
git add <文件名>            # 添加指定文件

# 提交修改
git commit -m "提交说明"    # 提交已暂存的修改

# 查看提交历史
git log                     # 查看详细历史
git log --oneline           # 查看简洁历史

# 创建新分支
git branch <分支名>         # 创建新分支
git checkout <分支名>       # 切换到指定分支
git checkout -b <分支名>    # 创建并切换到新分支

# 合并分支
git merge <分支名>          # 将指定分支合并到当前分支

# 推送到远程仓库
git remote add origin <远程仓库URL>  # 添加远程仓库
git push -u origin main              # 首次推送
git push                             # 后续推送
```

## 项目介绍

// ... 原有内容保留 ... 