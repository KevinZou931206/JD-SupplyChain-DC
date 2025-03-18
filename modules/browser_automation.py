from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import json
import time

class BrowserAutomation:
    def __init__(self, cache_dir='./cache', jd_username='', jd_password=''):
        self.cache_dir = cache_dir
        self.jd_username = jd_username
        self.jd_password = jd_password
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        self.cookie_path = os.path.join(cache_dir, 'cookies.json')
        self.driver = None
        
    def init_browser(self):
        """初始化Chrome浏览器"""
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 自动下载和安装ChromeDriver
        service = Service(ChromeDriverManager().install())
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
                time.sleep(1)  # 等待切换完成
            
            # 输入账号密码
            username_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="loginname"]'))
            )
            username_input.clear()
            username_input.send_keys(self.jd_username)
            
            # 等待密码输入框加载，XPath可能每次都不同，可以尝试使用name属性查找
            try:
                password_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="nloginpwd"]'))
                )
            except:
                # 如果找不到特定ID，尝试找所有密码输入框
                password_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))
                )
                
            password_input.clear()
            password_input.send_keys(self.jd_password)
            
            # 点击登录按钮
            login_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div/div/div/div/div[3]/div/div[1]/form/div[4]/div/button'))
            )
            login_button.click()
            
            # 检查是否需要滑动验证
            try:
                slide_verify = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[contains(@id, "JDJRV") or contains(@class, "verify")]'))
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
        if self.driver:
            cookies = self.driver.get_cookies()
            with open(self.cookie_path, 'w') as f:
                json.dump(cookies, f)
                
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None 