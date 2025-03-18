"""
配置文件，存储应用程序需要的各种配置信息
"""
import os

# 获取当前脚本所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    'db': {
        'server': 'www.taiyian.com',
        'database': 'dxmy',
        'username': 'kevin',
        'password': '19890324*sL'
    , 'batch_size': '100', 'timeout': '30'},
    'paths': {
        'cache_dir': os.path.join(BASE_DIR, 'cache'),
        'download_dir': os.path.join(BASE_DIR, 'Downloads')
    },
    'jd': {
        'username': 'kevin',  # 填入京东账号
        'password': '19890324*sL'   # 填入京东密码
    }
} 