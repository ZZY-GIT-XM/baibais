import psycopg2
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Items:
    def __init__(self) -> None:
        # 初始化数据库连接
        self._connect_to_db()
        # 存储从数据库加载的所有物品数据
        self.items = {}
        self.load_data()

    def _connect_to_db(self):
        """
        建立到数据库的连接
        """
        try:
            self.conn = psycopg2.connect(
                dbname="baibaidb",
                user="postgres",
                password="robots666",
                host="localhost",
                port=5432
            )
            self.conn.autocommit = True  # 确保每次操作都自动提交
            # logger.info("修仙数据库已连接！")
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")

    def fetch_data_from_db(self, table_name: str, columns: List[str]) -> List[Dict[str, Any]]:
        """
        从数据库中获取指定表格的数据
        参数:
        - table_name: 数据库中的表名
        - columns: 要查询的列名列表
        返回:
        - 包含查询结果的字典列表
        """
        # 构建SQL查询语句
        query = f"SELECT {', '.join(columns)} FROM {table_name}"
        # 使用上下文管理器执行SQL并获取结果
        with self.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            # 获取列名作为字典的键
            columns = [desc[0] for desc in cur.description]
            # 将每一行转换为字典格式
            result = [{col: row[i] for i, col in enumerate(columns)} for row in rows]
        return result

    def fetch_item_base_info(self, item_id: int) -> Dict[str, Any]:
        """
        获取物品的基础信息
        参数:
        - item_id: 物品的ID
        返回:
        - 包含物品基础信息的字典
        """
        query = "SELECT item_name, item_type, description FROM xiuxian_wupin_jichu WHERE item_id = %s"
        with self.conn.cursor() as cur:
            cur.execute(query, (item_id,))
            result = cur.fetchone()
            if result:
                return {'name': result[0], 'type': result[1], 'description': result[2]}
        return {}

    def set_item_data(self, data: List[Dict[str, Any]], item_type: str):
        """
        设置物品数据，将从数据库获取的数据存入self.items字典中

        参数:
        - data: 从数据库查询得到的物品数据列表
        - item_type: 物品类型（如：防具、法器等）
        """
        # 遍历数据列表，为每件物品添加类型标签，并存入self.items字典
        for item in data:
            item_id = str(item['item_id'])
            base_info = self.fetch_item_base_info(item_id)
            item.update(base_info)
            self.items[item_id] = item
            self.items[item_id].update({'item_type': item_type})

            # 如果物品包含'境界'字段，则添加此字段
            if 'realm' in item:
                self.items[item_id]['realm'] = item['realm']

    def load_data(self):
        """
        加载所有类型的物品数据
        """
        self.get_armor_data()
        self.get_weapon_data()
        self.get_main_buff_data()
        self.get_sub_buff_data()
        self.get_sec_buff_data()
        self.get_elixir_data()
        self.get_yaocai_data()
        self.get_mix_elixir_type_data()
        self.get_ldl_data()
        self.get_jlq_data()
        self.get_sw_data()

    def get_armor_data(self) -> List[Dict[str, Any]]:
        """
        获取防具数据
        返回:
        - 防具数据列表
        """
        armor_data = self.fetch_data_from_db(
            'xiuxian_fangju',
            ['item_id', 'level', 'def_buff', 'atk_buff', 'crit_buff', 'rank']
        )
        self.set_item_data(armor_data, '防具')
        return armor_data

    def get_weapon_data(self) -> List[Dict[str, Any]]:
        """
        获取法器数据
        返回:
        - 法器数据列表
        """
        weapon_data = self.fetch_data_from_db(
            'xiuxian_faqi',
            ['item_id', 'atk_buff', 'crit_buff', 'def_buff', 'critatk', 'zw', 'mp_buff', 'rank', 'level']
        )
        self.set_item_data(weapon_data, '法器')
        return weapon_data

    def get_main_buff_data(self) -> List[Dict[str, Any]]:
        """
        获取主要功法数据
        返回:
        - 主要功法数据列表
        """
        main_buff_data = self.fetch_data_from_db(
            'xiuxian_gongfa',
            ['item_id', 'hpbuff', 'mpbuff', 'atkbuff', 'ratebuff', 'crit_buff', 'def_buff', 'dan_exp', 'dan_buff',
             'reap_buff', 'exp_buff', 'critatk', 'two_buff', 'number', 'clo_exp', 'clo_rs', 'random_buff', 'ew', 'rank',
             'level']
        )
        self.set_item_data(main_buff_data, '主要功法')
        return main_buff_data

    def get_sub_buff_data(self) -> List[Dict[str, Any]]:
        """
        获取辅助功法数据
        返回:
        - 辅助功法数据列表
        """
        sub_buff_data = self.fetch_data_from_db(
            'xiuxian_fuxiu_gongfa',
            ['item_id', 'buff_type', 'buff', 'buff2', 'stone', 'integral', 'jin', 'drop', 'fan', 'break', 'exp', 'rank',
             'level']
        )
        self.set_item_data(sub_buff_data, '辅助功法')
        return sub_buff_data

    def get_sec_buff_data(self) -> List[Dict[str, Any]]:
        """
        获取神通数据
        返回:
        - 神通数据列表
        """
        sec_buff_data = self.fetch_data_from_db(
            'xiuxian_shentong',
            ['item_id', 'skill_type', 'atkvalue', 'hpcost', 'mpcost', 'turncost', 'jndesc', 'rate', 'rank', 'level']
        )
        self.set_item_data(sec_buff_data, '神通')
        return sec_buff_data

    def get_elixir_data(self) -> List[Dict[str, Any]]:
        """
        获取丹药数据
        返回:
        - 丹药数据列表
        """
        elixir_data = self.fetch_data_from_db(
            'xiuxian_danyao',
            ['item_id', 'buff_type', 'buff', 'price', 'selling', 'realm', 'status', 'quantity', 'day_num', 'all_num',
             'rank']
        )
        self.set_item_data(elixir_data, '丹药')
        return elixir_data

    def get_yaocai_data(self) -> List[Dict[str, Any]]:
        """
        获取药材数据
        返回:
        - 药材数据列表
        """
        yaocai_data = self.fetch_data_from_db(
            'xiuxian_yaocai',
            ['item_id', 'level', 'primary_ingredient', 'catalyst', 'auxiliary_ingredient', 'rank']
        )
        self.set_item_data(yaocai_data, '药材')
        return yaocai_data

    def get_mix_elixir_type_data(self) -> List[Dict[str, Any]]:
        """
        获取合成丹药数据
        返回:
        - 合成丹药数据列表
        """
        mix_elixir_data = self.fetch_data_from_db(
            'xiuxian_liandandanyao',
            ['item_id', 'buff_type', 'all_num', 'buff', 'realm', 'mix_need_time', 'mix_exp', 'mix_all', 'elixir_config',
             'rank']
        )
        self.set_item_data(mix_elixir_data, '合成丹药')
        return mix_elixir_data

    def get_ldl_data(self) -> List[Dict[str, Any]]:
        """
        获取炼丹炉数据
        返回:
        - 炼丹炉数据列表
        """
        ldl_data = self.fetch_data_from_db(
            'xiuxian_liandanlu',
            ['item_id', 'type', 'buff', 'rank']
        )
        self.set_item_data(ldl_data, '炼丹炉')
        return ldl_data

    def get_jlq_data(self) -> List[Dict[str, Any]]:
        """
        获取聚灵旗数据
        返回:
        - 聚灵旗数据列表
        """
        jlq_data = self.fetch_data_from_db(
            'xiuxian_xiulian_wupin',
            ['item_id', 'type', 'cultivation_speed', 'herb_speed', 'rank']
        )
        self.set_item_data(jlq_data, '聚灵旗')
        return jlq_data

    def get_sw_data(self) -> List[Dict[str, Any]]:
        """
        获取神物数据
        返回:
        - 神物数据列表
        """
        sw_data = self.fetch_data_from_db(
            'xiuxian_shenwu',
            ['item_id', 'buff_type', 'all_num', 'buff', 'realm', 'mix_need_time', 'mix_exp', 'mix_all', 'elixir_config',
             'rank']
        )
        self.set_item_data(sw_data, '神物')
        return sw_data

    def get_data_by_item_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        根据物品ID获取数据
        参数:
        - item_id: 物品的ID
        返回:
        - 物品数据字典，如果没有找到则返回None
        """
        return self.items.get(str(item_id), None)

    def get_data_by_item_type(self, item_type: str) -> Dict[str, Any]:
        """
        根据物品类型获取数据
        参数:
        - item_type: 物品类型
        返回:
        - 符合类型的物品数据字典
        """
        return {k: v for k, v in self.items.items() if v.get('item_type') == item_type}

    def get_random_id_list_by_rank_and_item_type(
            self,
            fanil_rank: int,
            item_type: List[str] = None
    ) -> List[int]:
        """
        获取符合条件的随机物品ID列表
        参数:
        - fanil_rank: 用户的最终rank
        - item_type: 物品类型列表
        返回:
        - 满足条件的物品ID列表
        """
        valid_ids = []
        for k, v in self.items.items():
            # 检查是否指定了物品类型
            if item_type is not None and v.get('item_type') in item_type:
                # 获取物品的rank
                rank = int(v.get('rank', 0))
                # 检查物品rank是否符合要求
                if rank >= fanil_rank and rank - fanil_rank <= 40:
                    valid_ids.append(int(k))
        return valid_ids

    def convert_rank(self, rank_input: str) -> Tuple[Optional[int], List[str]]:
        """
        获取境界等级，替代原来的USERRANK
        convert_rank('江湖好手')[0] 返回江湖好手的境界ID
        convert_rank('江湖好手')[1] 返回境界列表
        convert_rank('1')[0] 返回ID为1的境界名称
        convert_rank('1')[1] 返回境界列表
        """
        if isinstance(rank_input, str) and rank_input.isdigit():
            # 如果输入的是字符串形式的数字，则尝试按ID查找境界名称
            rank_id = int(rank_input)
            query = "SELECT jingjie_name FROM xiuxian_jingjie WHERE id = %s"
            with self.conn.cursor() as cursor:
                cursor.execute(query, (rank_id,))
                result = cursor.fetchone()
                if result:
                    rank_name = result[0]
                    rank_number = 58 - rank_id  # 调整返回的ID
                else:
                    rank_name = None
                    rank_number = None
        else:
            # 如果输入的是境界名称，则尝试按名称查找ID
            rank_name = rank_input
            query = "SELECT id FROM xiuxian_jingjie WHERE jingjie_name = %s"
            with self.conn.cursor() as cursor:
                cursor.execute(query, (rank_name,))
                result = cursor.fetchone()
                if result:
                    rank_number = 58 - result[0]  # 调整返回的ID
                else:
                    rank_number = None

        # 获取所有境界名称的列表
        query = "SELECT jingjie_name FROM xiuxian_jingjie ORDER BY id ASC"
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            all_ranks = [row[0] for row in cursor.fetchall()]

        return rank_number, all_ranks


# if __name__ == "__main__":
#     # 创建 Items 实例
#     items = Items()
#     # 加载所有数据
#     items.load_data()
#     # 输出 self.items 的内容以查看是否正确加载了数据
#     print("self.items 内容:", items.items)


if __name__ == "__main__":
    # 创建 Items 实例
    items = Items()
    # 加载所有数据
    items.load_data()
    # 输出 self.items 的内容以查看是否正确加载了数据
    # print("self.items 内容:", items.items)
    # 测试已知存在的物品ID
    test_item_id = 9201  # 假设数据库中有物品ID为1的数据
    item_info = items.get_data_by_item_id(test_item_id)
    # 打印结果
    if item_info:
        print(f"物品ID {test_item_id} 的信息: {item_info}")
    else:
        print(f"物品ID {test_item_id} 的信息不存在。")

# # 测试使用：
# if __name__ == "__main__":
#     items = Items()
#     # 加载所有数据
#     items.load_data()
#     # 获取用户对应的境界ID
#     rank_number = 39
#     # 获取符合条件的随机物品ID列表
#     yaocai_id_list = items.get_random_id_list_by_rank_and_item_type(rank_number, ['药材'])
#     print(f"符合条件的物品ID列表:{yaocai_id_list}\n")
#
# # 测试使用：
# if __name__ == "__main__":
#     items = Items()
#     # 获取境界ID
#     rank_number = items.convert_rank('圣祭境圆满')[0]
#     # 获取境界列表
#     rank_list = items.convert_rank('圣祭境圆满')[1]
#     print(f"圣祭境圆满的等级: {rank_number}")
#     print(f"境界列表: {rank_list}")
#
# # 测试使用：
# if __name__ == "__main__":
#     items = Items()
#     # 获取境界ID
#     rank_number = items.get_data_by_item_id(1)
#     print(f"物品: {rank_number}")
