from pathlib import Path
from nonebot import require, load_plugins
import sys

# 获取当前文件所在的目录
dir_ = Path(__file__).parent

# 构建插件目录路径
plugin_dir = dir_ / "xiuxian"

# 动态加载插件前的验证
if not plugin_dir.exists() or not plugin_dir.is_dir():
    print(f"插件目录 {plugin_dir} 不存在或不是一个有效的目录")
    sys.exit(1)

# 加载插件
try:
    require('nonebot_plugin_apscheduler')
    load_plugins(str(plugin_dir))
except Exception as e:
    print(f"加载插件时发生错误: {e}")
    sys.exit(1)
