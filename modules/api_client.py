import requests
import json
import os
from datetime import datetime
import time
import random
import re

class ApiClient:
    def __init__(self, cache_dir='./cache', download_dir='./Downloads'):
        self.cache_dir = cache_dir
        self.download_dir = download_dir
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        self.cookie_path = os.path.join(cache_dir, 'cookies.json')
        self.cookies = self.load_cookies()
        
    def load_cookies(self):
        """从文件加载cookies"""
        if os.path.exists(self.cookie_path):
            try:
                with open(self.cookie_path, 'r') as f:
                    cookie_list = json.load(f)
                    return {cookie['name']: cookie['value'] for cookie in cookie_list}
            except Exception as e:
                print(f"加载cookies失败: {str(e)}")
                return {}
        return {}
    
    def generate_order_list(self, start_time, end_time):
        """生成订单列表"""
        url = "https://api.m.jd.com/api"
        
        # 刷新cookies
        self.cookies = self.load_cookies()
        
        # 生成timestamp
        timestamp = str(int(datetime.now().timestamp() * 1000))
        
        params = {
            "functionId": "api_order_export",
            "scval": "all",
            "loginType": "3",
            "appid": "gx-pc",
            "client": "pc",
            "t": timestamp
        }
        
        headers = {
            "authority": "api.m.jd.com",
            "method": "POST",
            "path": f"/api?functionId=api_order_export&scval=all&loginType=3&appid=gx-pc&client=pc&t={timestamp}",
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
            "ext": json.dumps({"requestSource":"color"})
        }
        
        try:
            response = requests.post(url, params=params, headers=headers, cookies=self.cookies, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"请求失败，状态码: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"请求异常: {str(e)}"}
    
    def download_order_list(self):
        """下载订单列表"""
        url = "https://gmall.jd.com/api/batchTask/list"
        
        # 刷新cookies
        self.cookies = self.load_cookies()
        
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
        
        try:
            response = requests.post(url, headers=headers, cookies=self.cookies, json=data)
            if response.status_code == 200:
                resp_json = response.json()
                
                if resp_json.get('success') and resp_json.get('data', {}).get('rows'):
                    file_url = resp_json['data']['rows'][0]['targetFile']
                    
                    # 提取文件名 - 只使用问号之前的部分
                    if '?' in file_url:
                        file_name = file_url.split('?')[0].split('/')[-1]
                    else:
                        file_name = file_url.split('/')[-1]
                    
                    # 确保文件名有效
                    file_name = re.sub(r'[\\/*?:"<>|]', '_', file_name)  # 替换非法字符
                    
                    # 下载文件
                    download_response = requests.get(file_url)
                    if download_response.status_code == 200:
                        # 确保使用标准化的路径分隔符
                        download_dir = os.path.abspath(self.download_dir)
                        file_path = os.path.join(download_dir, file_name)
                        
                        with open(file_path, 'wb') as f:
                            f.write(download_response.content)
                            
                        return {"success": True, "file_path": file_path}
                    else:
                        return {"success": False, "message": f"下载文件失败，状态码: {download_response.status_code}"}
                else:
                    return {"success": False, "message": "未找到可下载的文件或接口返回格式错误"}
            else:
                return {"success": False, "message": f"请求失败，状态码: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"请求异常: {str(e)}"} 