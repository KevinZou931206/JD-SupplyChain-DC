import os
import json
import logging

# 配置日志
logger = logging.getLogger('AccountManager')

class AccountManager:
    def __init__(self, config_file='accounts.json'):
        self.config_file = config_file
        self.accounts = {}
        self.load_accounts()
    
    def load_accounts(self):
        """从文件加载账号配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                logger.info(f"已加载 {len(self.accounts)} 个账号配置")
        except Exception as e:
            logger.error(f"加载账号配置失败: {str(e)}")
            self.accounts = {}
    
    def save_account(self, account_info):
        """保存或更新账号配置"""
        try:
            account_name = account_info.get('account_name')
            if not account_name:
                return {"success": False, "message": "账号名称不能为空"}
            
            # 加载最新的账号配置
            self.load_accounts()
            
            # 更新账号信息
            self.accounts[account_name] = {
                # 确保username使用账号名称
                'username': account_name,
                'password': account_info.get('password', ''),
                'merchant_id': account_info.get('merchant_id', ''),
                'store_name': account_info.get('store_name', '')
                # 已移除eid字段
            }
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存账号 {account_name} 的配置")
            return {"success": True, "message": f"已保存账号 {account_name} 的配置"}
        
        except Exception as e:
            logger.error(f"保存账号配置失败: {str(e)}")
            return {"success": False, "message": f"保存账号配置失败: {str(e)}"}
    
    def delete_account(self, account_name):
        """删除账号配置"""
        try:
            if not account_name:
                return {"success": False, "message": "账号名称不能为空"}
            
            # 加载最新的账号配置
            self.load_accounts()
            
            if account_name in self.accounts:
                del self.accounts[account_name]
                
                # 保存到文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts, f, ensure_ascii=False, indent=2)
                
                logger.info(f"已删除账号 {account_name} 的配置")
                return {"success": True, "message": f"已删除账号 {account_name} 的配置"}
            else:
                return {"success": False, "message": f"账号 {account_name} 不存在"}
        
        except Exception as e:
            logger.error(f"删除账号配置失败: {str(e)}")
            return {"success": False, "message": f"删除账号配置失败: {str(e)}"}
    
    def get_account_info(self, account_name):
        """获取账号信息"""
        try:
            # 加载最新的账号配置
            self.load_accounts()
            
            if account_name in self.accounts:
                account_info = self.accounts[account_name].copy()  # 创建一个副本
                account_info['account_name'] = account_name
                # 确保username字段存在并使用account_name
                account_info['username'] = account_name
                return {"success": True, "data": account_info}
            else:
                return {"success": False, "message": f"账号 {account_name} 不存在"}
        
        except Exception as e:
            logger.error(f"获取账号信息失败: {str(e)}")
            return {"success": False, "message": f"获取账号信息失败: {str(e)}"}
    
    def get_all_accounts(self):
        """获取所有账号名称"""
        try:
            # 加载最新的账号配置
            self.load_accounts()
            return {"success": True, "data": list(self.accounts.keys())}
        
        except Exception as e:
            logger.error(f"获取所有账号失败: {str(e)}")
            return {"success": False, "message": f"获取所有账号失败: {str(e)}"} 