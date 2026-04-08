import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
import uuid

class DataComparator:
    """数据对比服务"""

    def __init__(self, factory_df: pd.DataFrame, jiuding_df: pd.DataFrame, factory_type: str):
        self.factory_df = factory_df
        self.jiuding_df = jiuding_df
        self.factory_type = factory_type

    def compare(self) -> pd.DataFrame:
        """执行数据对比，返回对比结果"""
        results = []

        # 获取单号列表
        if self.factory_type == "hengyi":
            factory_orders = set(self.factory_df['交货单'].astype(str).tolist())
            factory_map = self.factory_df.set_index('交货单').to_dict('index')
        else:  # xinfengming
            factory_orders = set(self.factory_df['交货单号'].astype(str).tolist())
            factory_map = self.factory_df.set_index('交货单号').to_dict('index')

        jiuding_orders = set(self.jiuding_df['出库单号'].astype(str).tolist())
        jiuding_map = self.jiuding_df.set_index('出库单号').to_dict('index')

        # 情况1: 单号在两端都存在
        common_orders = factory_orders & jiuding_orders
        for order_id in common_orders:
            factory_data = factory_map[order_id]
            jiuding_data = jiuding_map[order_id]
            result = self._create_comparison_row(order_id, factory_data, jiuding_data, "both")
            results.append(result)

        # 情况2: 单号只在工厂侧存在
        factory_only_orders = factory_orders - jiuding_orders
        for order_id in factory_only_orders:
            factory_data = factory_map[order_id]
            result = self._create_comparison_row(order_id, factory_data, None, "factory_only")
            results.append(result)

        # 情况3: 单号只在久鼎侧存在
        jiuding_only_orders = jiuding_orders - factory_orders
        for order_id in jiuding_only_orders:
            jiuding_data = jiuding_map[order_id]
            result = self._create_comparison_row(order_id, None, jiuding_data, "jiuding_only")
            results.append(result)

        return pd.DataFrame(results)

    def _create_comparison_row(self, order_id: str, factory_data: Dict, jiuding_data: Dict, source: str) -> Dict:
        """创建对比结果行"""
        if source == "both":
            # 两端都有数据
            factory_qty = factory_data.get('交货数量') if self.factory_type == "hengyi" else factory_data.get('件数')
            jiuding_qty = jiuding_data.get('实际出库数量')

            return {
                '日期': jiuding_data.get('订单日期'),
                '单号': order_id,
                '工厂': jiuding_data.get('客户名称'),  # 久鼎侧的客户名称（简称）
                '型号': jiuding_data.get('产品类型'),
                '公司': jiuding_data.get('会员名称'),  # 久鼎侧的会员名称
                '客户出库数': factory_qty,
                '久鼎出库数': jiuding_qty,
                '待处理数量': factory_qty - jiuding_qty if pd.notna(factory_qty) and pd.notna(jiuding_qty) else None
            }
        elif source == "factory_only":
            # 只有工厂侧数据
            factory_qty = factory_data.get('交货数量') if self.factory_type == "hengyi" else factory_data.get('件数')

            return {
                '日期': factory_data.get('交货日期') if self.factory_type == "hengyi" else factory_data.get('交货创建日期'),
                '单号': order_id,
                '工厂': None,  # 无法补充
                '型号': factory_data.get('物料组') if self.factory_type == "hengyi" else factory_data.get('物料组描述'),
                '公司': factory_data.get('送达方') if self.factory_type == "hengyi" else factory_data.get('客户名称'),
                '客户出库数': factory_qty,
                '久鼎出库数': None,
                '待处理数量': None
            }
        else:  # jiuding_only
            # 只有久鼎侧数据
            jiuding_qty = jiuding_data.get('实际出库数量')

            return {
                '日期': jiuding_data.get('订单日期'),
                '单号': order_id,
                '工厂': jiuding_data.get('客户名称'),
                '型号': jiuding_data.get('产品类型'),
                '公司': jiuding_data.get('会员名称'),
                '客户出库数': None,
                '久鼎出库数': jiuding_qty,
                '待处理数量': None
            }
