try:
    import ujson as json
except ImportError:
    import json
import os
from pathlib import Path

configkey = ["open", "rift"]
CONFIG_DEFAULT = {
    "open": [],
    "rift": {
        "东玄域": {
            "type_rate": 200,  # 概率
            "rank": 1,  # 增幅等级
            "count": 100,  # 次数
            "time": 60,  # 时间，单位分
        },
        "西玄域": {
            "type_rate": 200,
            "rank": 1,
            "count": 100,
            "time": 60,
        },
        "妖域": {
            "type_rate": 100,
            "rank": 2,
            "count": 100,
            "time": 90,
        },
        "乱魔海": {
            "type_rate": 100,
            "rank": 2,
            "count": 100,
            "time": 90,
        },
        "幻雾林": {
            "type_rate": 50,
            "rank": 3,
            "count": 100,
            "time": 120,
        },
        "狐鸣山": {
            "type_rate": 50,
            "rank": 3,
            "count": 100,
            "time": 120,
        },
        "云梦泽": {
            "type_rate": 25,
            "rank": 4,
            "count": 100,
            "time": 150,
        },
        "乱星原": {
            "type_rate": 12,
            "rank": 4,
            "count": 100,
            "time": 150,
        },
        "黑水湖": {
            "type_rate": 6,
            "rank": 5,
            "count": 100,
            "time": 180,
        }
    },
    "group_rift": {}  # 新增的秘境信息
}

CONFIGJSONPATH = Path(__file__).parent
FILEPATH = CONFIGJSONPATH / 'config.json'

def get_rift_config():
    try:
        config = readf()
        for key in configkey:
            if key not in config:
                config[key] = CONFIG_DEFAULT[key]
        if "group_rift" not in config:
            config["group_rift"] = CONFIG_DEFAULT["group_rift"]
        savef_rift(config)
    except Exception as e:
        print(f"读取配置文件失败：{e}")
        config = CONFIG_DEFAULT
        savef_rift(config)
    return config

def readf():
    try:
        with open(FILEPATH, "r", encoding="UTF-8") as f:
            data = f.read()
        return json.loads(data)
    except FileNotFoundError:
        print("配置文件未找到，使用默认配置")
        return CONFIG_DEFAULT
    except json.JSONDecodeError:
        print("配置文件格式错误，使用默认配置")
        return CONFIG_DEFAULT

def savef_rift(data):
    try:
        data_str = json.dumps(data, ensure_ascii=False, indent=3)
        savemode = "w" if os.path.exists(FILEPATH) else "x"
        with open(FILEPATH, mode=savemode, encoding="UTF-8") as f:
            f.write(data_str)
    except Exception as e:
        print(f"保存配置文件失败：{e}")
        return False
    return True
