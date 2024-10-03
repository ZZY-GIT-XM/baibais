try:
    import ujson as json
except ImportError:
    import json
from pathlib import Path

SKILLPATH = Path() / "data" / "xiuxian" / "功法" / "功法概率设置.json"
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"


def read_f():
    with open(SKILLPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)

