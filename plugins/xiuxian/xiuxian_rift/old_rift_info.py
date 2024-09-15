import json
from datetime import datetime
from pathlib import Path
import os
from .riftmake import Rift

class OLD_RIFT_INFO(object):
    def __init__(self):
        self.dir_path = Path(__file__).parent
        self.data_path = os.path.join(self.dir_path, "rift_info.json")

        # 确保文件存在并初始化为空字典
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)

        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def __save(self):
        """
        :return: 保存
        """
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, cls=MyEncoder, ensure_ascii=False, indent=4)

    def save_rift(self, group_rift):
        """
        保存rift
        :param group_rift:
        """
        self.data = {}
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
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        else:
            return super(MyEncoder, self).default(obj)
