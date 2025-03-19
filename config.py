"""
配置文件，存储应用程序需要的各种配置信息
"""
import os
import json

# 获取当前脚本所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 从JSON文件加载数据库配置
def load_db_config():
    db_config_path = os.path.join(BASE_DIR, 'database_config.json')
    # 如果配置文件不存在，尝试使用模板创建一个
    if not os.path.exists(db_config_path):
        template_path = os.path.join(BASE_DIR, 'database_config_template.json')
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_config = json.load(f)
                with open(db_config_path, 'w', encoding='utf-8') as f:
                    json.dump(template_config, f, ensure_ascii=False, indent=4)
                print(f"已创建数据库配置文件模板，请在 {db_config_path} 中填写正确的配置信息")
            except Exception as e:
                print(f"创建数据库配置文件失败: {str(e)}")
        return {}
    
    try:
        with open(db_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载数据库配置失败: {str(e)}")
        return {}

# 主配置
CONFIG = {
    'paths': {
        'cache_dir': os.path.join(BASE_DIR, 'cache'),
        'download_dir': os.path.join(BASE_DIR, 'Downloads')
    },
    'jd': {
        'username': '',  # 不再在此存储敏感信息
        'password': ''   # 不再在此存储敏感信息
    }
} 