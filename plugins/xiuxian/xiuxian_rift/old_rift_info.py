import json
from datetime import datetime
from pathlib import Path
import os
from .riftmake import Rift

class OLD_RIFT_INFO(object):
    def __init__(self):
        self.dir_path = Path(__file__).parent
        self.data_path = self.dir_path / "rift_info.json"

        # 确保文件存在并初始化为空字典
        if not self.data_path.exists():
            self.data_path.write_text(json.dumps({}, ensure_ascii=False, indent=4), encoding='utf-8')

        self.data = json.loads(self.data_path.read_text(encoding='utf-8'))

    def __save(self):
        """
        保存数据
        """
        try:
            self.data_path.write_text(json.dumps(self.data, cls=MyEncoder, ensure_ascii=False, indent=4), encoding='utf-8')
        except Exception as e:
            print(f"保存数据时发生错误: {e}")

    def save_rift(self, group_rift):
        """
        保存rift信息
        :param group_rift: 包含群组和rift信息的字典
        """
        self.data.clear()
        for group_id, rift in group_rift.items():
            rift_data = {
                str(group_id): {
                    "name": rift.name,
                    "rank": rift.rank,
                    "count": rift.count,
                    "l_user_id": rift.l_user_id,
                    "time": rift.time
                }
            }
            self.data.update(rift_data)
        self.__save()
        return True

    def read_rift_info(self):
        """
        读取rift信息
        """
        group_rift = {}
        for group_id, rift_data in self.data.items():
            rift = Rift()
            rift.name = rift_data["name"]
            rift.rank = rift_data["rank"]
            rift.count = rift_data["count"]
            rift.l_user_id = rift_data["l_user_id"]
            rift.time = rift_data["time"]
            group_rift[group_id] = rift
        return group_rift

# 实例化对象
old_rift_info = OLD_RIFT_INFO()

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        else:
            return super(MyEncoder, self).default(obj)
