import pyodbc
import pandas as pd
from sqlalchemy import create_engine
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DatabaseManager')

class DatabaseManager:
    def __init__(self, server, database, username, password, batch_size=100, timeout=30):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.batch_size = int(batch_size)
        self.timeout = int(timeout)
        
        self.connection_string = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Connection Timeout={timeout}'
        self.conn_str_sqlalchemy = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver=SQL+Server&timeout={timeout}'
        
    def test_connection(self):
        """测试数据库连接"""
        try:
            conn = pyodbc.connect(self.connection_string)
            conn.close()
            logger.info("数据库连接测试成功")
            return {"success": True, "message": "数据库连接成功"}
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return {"success": False, "message": f"数据库连接失败: {str(e)}"}
            
    def create_tables_if_not_exist(self):
        """创建主表和明细表（如果不存在）"""
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()
            
            # 创建订单主表
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jx_orders_master' AND xtype='U')
                CREATE TABLE jx_orders_master (
                    order_id NVARCHAR(50) PRIMARY KEY,
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
                    payable_amount DECIMAL(10, 2),
                    user_payment_total DECIMAL(10, 2),
                    carrier NVARCHAR(100),
                    tracking_number NVARCHAR(100),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建订单明细表
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jx_orders_detail' AND xtype='U')
                CREATE TABLE jx_orders_detail (
                    order_id NVARCHAR(50) NOT NULL,
                    supplier_id NVARCHAR(50),
                    product_name NVARCHAR(255),
                    product_color NVARCHAR(50),
                    product_size NVARCHAR(50),
                    merchant_sku NVARCHAR(50),
                    parent_sku NVARCHAR(50),
                    child_sku NVARCHAR(50),
                    purchase_price DECIMAL(10, 2),
                    purchase_quantity INT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT FK_OrderDetail_OrderMaster FOREIGN KEY (order_id) 
                    REFERENCES jx_orders_master(order_id)
                )
            """)
            
            # 删除不再需要的触发器
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'trg_GenerateFormattedID')
                    DROP TRIGGER trg_GenerateFormattedID;
            """)
            
            conn.commit()
            conn.close()
            logger.info("主表和明细表创建成功或已存在")
            return {"success": True, "message": "主表和明细表已创建或已存在"}
            
        except Exception as e:
            logger.error(f"创建表失败: {str(e)}")
            return {"success": False, "message": f"创建表失败: {str(e)}"}
    
    def upload_master_data(self, df):
        """上传主表数据到SQL Server"""
        return self._upload_data(df, 'jx_orders_master', 'order_id')
    
    def upload_detail_data(self, df):
        """上传明细表数据到SQL Server"""
        return self._upload_data(df, 'jx_orders_detail', None)
    
    def upload_data(self, data_result):
        """上传主表和明细表数据到SQL Server数据库"""
        try:
            # 确保表存在
            create_result = self.create_tables_if_not_exist()
            if not create_result['success']:
                return create_result
            
            # 检查数据是否包含主表和明细表
            if 'master_data' not in data_result or 'detail_data' not in data_result:
                return {"success": False, "message": "数据格式不正确，缺少主表或明细表数据"}
            
            # 上传主表数据
            master_result = self.upload_master_data(data_result['master_data'])
            if not master_result['success']:
                return master_result
            
            # 上传明细表数据
            detail_result = self.upload_detail_data(data_result['detail_data'])
            if not detail_result['success']:
                return detail_result
            
            # 返回成功结果
            return {
                "success": True, 
                "message": f"数据上传成功，主表：{master_result['count']}条记录，明细表：{detail_result['count']}条记录",
                "master_count": master_result['count'],
                "detail_count": detail_result['count']
            }
            
        except Exception as e:
            logger.error(f"数据上传失败: {str(e)}")
            return {"success": False, "message": f"数据上传失败: {str(e)}"}
    
    def _upload_data(self, df, table_name, key_column=None):
        """上传数据到SQL Server数据库的通用方法"""
        try:
            logger.info(f"开始上传数据到 {table_name} 表，共 {len(df)} 条记录")
            
            if df.empty:
                logger.warning(f"没有数据需要上传到 {table_name} 表")
                return {"success": True, "message": f"没有数据上传到 {table_name} 表", "count": 0}
            
            # 处理数据类型兼容性问题
            date_columns = ['created_at', 'outbound_at', 'completed_at', 'canceled_at']
            for col in date_columns:
                if col in df.columns:
                    # 将空字符串的日期设为None
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # 建立数据库连接
            conn = pyodbc.connect(self.connection_string)
            
            # 获取表的所有列
            cursor = conn.cursor()
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
            table_columns = [row.COLUMN_NAME for row in cursor.fetchall()]
            
            # 过滤出匹配的列
            df_filtered = df[[col for col in df.columns if col in table_columns]]
            
            if df_filtered.empty:
                logger.error(f"没有匹配的列，无法上传数据到 {table_name} 表")
                return {"success": False, "message": f"没有匹配的列，无法上传数据到 {table_name} 表", "count": 0}
            
            records_count = 0
            error_count = 0
            skip_count = 0
            
            # 对于主表（有主键的表），使用UPSERT逻辑
            if key_column and key_column in df_filtered.columns:
                for i in range(0, len(df_filtered), self.batch_size):
                    batch = df_filtered.iloc[i:i+self.batch_size]
                    batch_count = 0
                    
                    for _, row in batch.iterrows():
                        try:
                            # 先检查记录是否存在
                            key_value = row[key_column]
                            cursor.execute(f"SELECT 1 FROM {table_name} WHERE {key_column} = ?", key_value)
                            exists = cursor.fetchone() is not None
                            
                            if exists:
                                # 更新现有记录
                                non_key_columns = [col for col in row.index if col != key_column]
                                
                                if not non_key_columns:  # 如果没有非主键列，跳过更新
                                    skip_count += 1
                                    continue
                                    
                                update_pairs = ', '.join([f"{col} = ?" for col in non_key_columns])
                                sql = f"UPDATE {table_name} SET {update_pairs} WHERE {key_column} = ?"
                                
                                values = [val if pd.notna(val) else None for col, val in row.items() if col != key_column]
                                values.append(key_value)
                                cursor.execute(sql, values)
                            else:
                                # 插入新记录
                                columns = ', '.join(row.index)
                                placeholders = ', '.join(['?' for _ in range(len(row))])
                                sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                                
                                values = [val if pd.notna(val) else None for val in row.values]
                                cursor.execute(sql, values)
                            
                            batch_count += 1
                            records_count += 1
                        except pyodbc.IntegrityError as e:
                            if "PRIMARY KEY" in str(e) or "UNIQUE KEY" in str(e):
                                logger.warning(f"存在主键冲突，尝试更新: {row[key_column]}")
                                try:
                                    # 尝试更新而不是插入
                                    non_key_columns = [col for col in row.index if col != key_column]
                                    if non_key_columns:
                                        update_pairs = ', '.join([f"{col} = ?" for col in non_key_columns])
                                        sql = f"UPDATE {table_name} SET {update_pairs} WHERE {key_column} = ?"
                                        
                                        values = [val if pd.notna(val) else None for col, val in row.items() if col != key_column]
                                        values.append(key_value)
                                        cursor.execute(sql, values)
                                        batch_count += 1
                                        records_count += 1
                                    else:
                                        skip_count += 1
                                except Exception as inner_e:
                                    logger.error(f"更新冲突记录时出错: {str(inner_e)}")
                                    error_count += 1
                            else:
                                logger.error(f"处理记录时出错: {str(e)}")
                                error_count += 1
                        except Exception as e:
                            logger.error(f"处理记录时出错: {str(e)}")
                            error_count += 1
                    
                    conn.commit()
                    logger.info(f"已处理 {batch_count} 条主表记录 (批次 {i//self.batch_size + 1})")
            else:
                # 对于明细表，批量删除需要更新的订单明细记录
                try:
                    # 如果是明细表，直接收集所有订单ID
                    if table_name == 'jx_orders_detail' and 'order_id' in df_filtered.columns:
                        # 获取所有涉及的订单ID
                        order_ids = df_filtered['order_id'].unique().tolist()
                        if order_ids:
                            # 构建参数占位符
                            placeholders = ','.join(['?' for _ in order_ids])
                            # 直接执行一条SQL语句删除所有相关明细
                            sql = f"DELETE FROM {table_name} WHERE order_id IN ({placeholders})"
                            cursor.execute(sql, order_ids)
                            rows_affected = cursor.rowcount
                            conn.commit()
                            logger.info(f"已删除 {rows_affected} 条明细记录，涉及 {len(order_ids)} 个订单")
                        else:
                            logger.info("没有需要更新的订单明细记录")
                except Exception as e:
                    logger.warning(f"批量删除明细记录时出错: {str(e)}")
                
                # 直接插入新数据
                for i in range(0, len(df_filtered), self.batch_size):
                    batch = df_filtered.iloc[i:i+self.batch_size]
                    batch_count = 0
                    
                    for _, row in batch.iterrows():
                        try:
                            # 准备SQL
                            columns = ', '.join(row.index)
                            placeholders = ', '.join(['?' for _ in range(len(row))])
                            sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                            
                            # 执行SQL
                            values = [val if pd.notna(val) else None for val in row.values]
                            cursor.execute(sql, values)
                            batch_count += 1
                            records_count += 1
                        except Exception as e:
                            logger.error(f"插入记录时出错: {str(e)}")
                            error_count += 1
                    
                    conn.commit()
                    logger.info(f"已处理 {batch_count} 条明细记录 (批次 {i//self.batch_size + 1})")
            
            conn.close()
            message = f"数据上传完成，共成功处理 {records_count} 条数据"
            if skip_count > 0:
                message += f"，跳过 {skip_count} 条数据"
            if error_count > 0:
                message += f"，失败 {error_count} 条数据"
                
            logger.info(message)
            
            if error_count > 0 and records_count == 0:
                return {"success": False, "message": f"数据上传失败，所有 {error_count} 条记录处理出错", "count": 0}
            else:
                return {"success": True, "message": message, "count": records_count}
        
        except Exception as e:
            logger.error(f"数据库上传失败: {str(e)}")
            return {"success": False, "message": f"数据库上传失败: {str(e)}", "count": 0} 