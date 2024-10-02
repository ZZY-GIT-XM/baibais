from typing import Set
from nonebot import get_driver
from pydantic.v1 import Field, BaseModel


# 定义一个配置类 Config，继承自 Pydantic 的 BaseModel。
# 这个类用于封装配置信息。
class Config(BaseModel):
    # 定义一个名为 disabled_plugins 的属性，类型为 Set[str]（字符串集合）。
    # 默认值为一个空集合，并且它在配置文件中的别名为 "xiuxian_disabled_plugins"。
    disabled_plugins: Set[str] = Field(
        default_factory=set, alias="xiuxian_disabled_plugins"
    )

    # 定义一个名为 priority 的属性，类型为 int（整数）。
    # 默认值为 2，并且它在配置文件中的别名为 "xiuxian_priority"。
    priority: int = Field(2, alias="xiuxian_priority")


# 获取 NoneBot 的驱动器实例，并从中解析出配置信息。
# 然后使用这些配置信息来创建 Config 类的一个实例。
config = Config.parse_obj(get_driver().config)

# 从 Config 实例中获取 priority 属性的值。
priority = config.priority
