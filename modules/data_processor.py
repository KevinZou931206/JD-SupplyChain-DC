import pandas as pd
import os
import glob
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DataProcessor')

class DataProcessor:
    def __init__(self, download_dir='./Downloads'):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
    def process_excel_files(self):
        """处理下载的Excel文件，分离为主表和明细表"""
        logger.info(f"开始处理Excel文件，路径: {self.download_dir}")
        
        # 查找Excel文件
        excel_files = glob.glob(os.path.join(self.download_dir, '*.xls'))
        if not excel_files:
            excel_files = glob.glob(os.path.join(self.download_dir, '*.xlsx'))
            
        if not excel_files:
            logger.warning("未找到Excel文件")
            return {"success": False, "message": "未找到Excel文件"}
        
        logger.info(f"找到 {len(excel_files)} 个Excel文件")
        
        # 定义字段映射关系
        column_mapping = {
            # 主表字段
            '订单编号': 'order_id',
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
            '采购单应付采购款': 'payable_amount',
            '用户实际支付总额': 'user_payment_total',
            '指定承运商': 'carrier',
            '物流运单号': 'tracking_number',
            
            # 明细表字段
            '产品名称': 'product_name',
            '产品颜色': 'product_color',
            '产品尺码': 'product_size',
            '商家SKU': 'merchant_sku',
            '父SKU': 'parent_sku',
            '子SKU': 'child_sku',
            '产品采购价': 'purchase_price',
            '采购数量': 'purchase_quantity'
        }
        
        # 定义主表和明细表字段
        master_fields = [
            'order_id', 'exchange_original_order_id', 'status', 'lock_status',
            'supplier_id', 'supplier_name', 'supplier_store_name',
            'distributor_id', 'distributor_name', 'distributor_store_name',
            'shipping_fee', 'receiver_name', 'contact_phone', 'shipping_address',
            'order_remark', 'created_at', 'outbound_at', 'completed_at', 'canceled_at',
            'is_jd_warehouse', 'payable_amount', 'user_payment_total',
            'carrier', 'tracking_number'
        ]
        
        # 定义明细表字段
        detail_fields = [
            'order_id', 'supplier_id', 'product_name', 'product_color', 'product_size',
            'merchant_sku', 'parent_sku', 'child_sku', 'purchase_price',
            'purchase_quantity'
        ]
        
        all_processed_data_master = []
        all_processed_data_details = []
        
        for file_path in excel_files:
            try:
                logger.info(f"处理文件: {os.path.basename(file_path)}")
                # 读取Excel文件
                df = pd.read_excel(file_path)
                
                logger.info(f"原始数据行数: {len(df)}, 列数: {len(df.columns)}")
                
                # 重命名列名
                df = df.rename(columns=column_mapping)
                
                # 清洗数据
                # 1. 处理缺失值
                df = df.fillna('')
                
                # 2. 处理日期格式
                date_columns = ['created_at', 'outbound_at', 'completed_at', 'canceled_at']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                
                # 3. 处理数值列
                numeric_columns = ['shipping_fee', 'purchase_price', 'purchase_quantity', 
                                   'payable_amount', 'user_payment_total']
                
                for col in numeric_columns:
                    if col in df.columns:
                        # 将空字符串转为0并转换为数值类型
                        df[col] = df[col].replace('', '0')
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # 创建主表和明细表
                # 主表只保留一个订单一条记录
                df_master = df.drop_duplicates(subset=['order_id'])
                # 保留主表需要的字段
                available_master_fields = [f for f in master_fields if f in df.columns]
                df_master = df_master[available_master_fields]
                
                # 明细表只保留有产品名称的记录
                df_details = df[df['product_name'] != ''].copy()
                # 保留明细表需要的字段
                available_detail_fields = [f for f in detail_fields if f in df.columns]
                df_details = df_details[available_detail_fields]
                
                logger.info(f"处理后主表数据行数: {len(df_master)}, 明细表数据行数: {len(df_details)}")
                
                all_processed_data_master.append(df_master)
                all_processed_data_details.append(df_details)
            
            except Exception as e:
                logger.error(f"处理文件出错: {str(e)}")
                return {"success": False, "message": f"处理文件 {os.path.basename(file_path)} 时出错: {str(e)}"}
        
        # 合并所有处理后的数据
        if all_processed_data_master and all_processed_data_details:
            combined_master = pd.concat(all_processed_data_master, ignore_index=True)
            combined_details = pd.concat(all_processed_data_details, ignore_index=True)
            
            logger.info(f"合并后主表总数据行数: {len(combined_master)}, 明细表总数据行数: {len(combined_details)}")
            
            # 验证数据
            master_order_count = combined_master['order_id'].nunique()
            detail_order_count = combined_details['order_id'].nunique()
            
            logger.info(f"主表订单数: {master_order_count}, 明细表包含的订单数: {detail_order_count}")
            
            # 检查明细表中是否有主表中不存在的订单
            detail_only_orders = set(combined_details['order_id'].unique()) - set(combined_master['order_id'].unique())
            if detail_only_orders:
                logger.warning(f"明细表中有 {len(detail_only_orders)} 个订单在主表中不存在")
            
            return {
                "success": True, 
                "master_data": combined_master, 
                "detail_data": combined_details,
                "message": f"处理成功，生成主表 {len(combined_master)} 行，明细表 {len(combined_details)} 行"
            }
        else:
            logger.warning("没有数据被处理")
            return {"success": False, "message": "没有数据被处理"} 