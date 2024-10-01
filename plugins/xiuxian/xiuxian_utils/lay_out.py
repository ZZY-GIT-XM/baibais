import random
from nonebot.log import logger
from nonebot.rule import Rule
from nonebot import get_bots, get_bot, require
from enum import IntEnum, auto
from collections import defaultdict
from asyncio import get_running_loop
from typing import DefaultDict, Dict, Any
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11 import Bot, MessageSegment

from ..xiuxian_config import XiuConfig
from .xiuxian2_handle import XiuxianDateManage
from .utils import get_msg_pic

sql_message = XiuxianDateManage()
limit_num = 99999

reset_xiaoxizidian = require("nonebot_plugin_apscheduler").scheduler
limit_all_data: Dict[str, Any] = {}


@reset_xiaoxizidian.scheduled_job('interval', minutes=1)
def reset_xiaoxizidian_():
    """重置消息字典"""
    global limit_all_data
    limit_all_data = {}
    logger.opt(colors=True).success(f"<green>已重置消息字典！</green>")


def limit_all_run(user_id: str):
    """
    limit_all_run 方法用于限制用户在一定时间内可以执行某项操作的次数。
    它维护了一个全局字典 limit_all_data 来记录每个用户的使用次数。
    当用户的使用次数超过预设的限制次数 limit_num 时，会返回不同的状态值。
    """
    # 声明全局变量 limit_all_data，确保可以在函数内部修改它
    global limit_all_data

    # 确保 user_id 是字符串类型
    user_id = str(user_id)

    # 初始化 num 和 tip 为 None，它们会在后续的逻辑中被赋值
    num = None
    tip = None

    # 尝试从全局字典中获取用户的使用次数和提示状态
    try:
        num = limit_all_data[user_id]["num"]
        tip = limit_all_data[user_id]["tip"]
    except KeyError:
        # 如果用户第一次访问，则初始化他们的使用次数为 0，提示状态为 False
        limit_all_data[user_id] = {"num": 0, "tip": False}
        num = 0
        tip = False

    # 增加用户的使用次数
    num += 1

    # 检查是否超过了使用次数的限制
    if num > limit_num and tip == False:
        # 如果之前没有提示过，设置提示状态为 True，并返回 True 表示需要提示用户
        tip = True
        limit_all_data[user_id]["num"] = num
        limit_all_data[user_id]["tip"] = tip
        return True
    elif num > limit_num and tip == True:
        # 如果之前已经提示过，则直接返回 False 表示不需要再次提示
        limit_all_data[user_id]["num"] = num
        return False
    else:
        # 如果没有超过限制次数，则更新用户的使用次数，并返回 None 表示一切正常
        limit_all_data[user_id]["num"] = num
        return None


def format_time(seconds: int) -> str:
    """将秒数转换为更大的时间单位"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        return f"{days}天{hours}小时{minutes}分钟{seconds}秒"
    elif hours > 0:
        return f"{hours}小时{minutes}分钟{seconds}秒"
    elif minutes > 0:
        return f"{minutes}分钟{seconds}秒"
    else:
        return f"{seconds}秒"


def get_random_chat_notice():
    return random.choice([
        "慢...慢一..点❤，还有{}，让我再歇会！",
        "冷静一下，还有{}，让我再歇会！",
        "时间还没到，还有{}，歇会歇会~~"
    ])


bu_ji_notice = random.choice(["别急！", "急也没用!", "让我先急!"])


class CooldownIsolateLevel(IntEnum):
    """命令冷却的隔离级别"""

    GLOBAL = auto()
    GROUP = auto()
    USER = auto()
    GROUP_USER = auto()


def Cooldown(
        cd_time: float = 0.5,
        at_sender: bool = True,
        isolate_level: CooldownIsolateLevel = CooldownIsolateLevel.USER,
        parallel: int = 1,
        stamina_cost: int = 0
) -> None:
    """依赖注入形式的命令冷却

    用法:
        ```python
        @matcher.handle(parameterless=[Cooldown(cooldown=11.4514, ...)])
        async def handle_command(matcher: Matcher, message: Message):
            ...
        ```

    参数:
        cd_time: 命令冷却间隔
        at_sender: 是否at
        isolate_level: 命令冷却的隔离级别, 参考 `CooldownIsolateLevel`
        parallel: 并行执行的命令数量
        stamina_cost: 每次执行命令消耗的体力值
    """
    if not isinstance(isolate_level, CooldownIsolateLevel):
        raise ValueError(
            f"invalid isolate level: {isolate_level!r}, "
            "isolate level must use provided enumerate value."
        )
    running: DefaultDict[str, int] = defaultdict(lambda: parallel)
    time_sy: Dict[str, int] = {}

    def increase(key: str, value: int = 1):
        running[key] += value
        if running[key] >= parallel:
            del running[key]
            del time_sy[key]
        return

    async def dependency(bot: Bot, matcher: Matcher, event: MessageEvent):
        user_id = str(event.get_user_id())
        group_id = str(event.group_id)

        limit_type = limit_all_run(str(event.get_user_id()))
        if limit_type is True:
            bot = await assign_bot_group(group_id=group_id)
            await bot.send(event=event, message=bu_ji_notice)
            await matcher.finish()
        elif limit_type is False:
            await matcher.finish()
        else:
            pass

        loop = get_running_loop()

        if isolate_level is CooldownIsolateLevel.GROUP:
            key = str(
                event.group_id
                if isinstance(event, GroupMessageEvent)
                else event.user_id,
            )
        elif isolate_level is CooldownIsolateLevel.USER:
            key = str(event.user_id)
        elif isolate_level is CooldownIsolateLevel.GROUP_USER:
            key = (
                f"{event.group_id}_{event.user_id}"
                if isinstance(event, GroupMessageEvent)
                else str(event.user_id)
            )
        else:
            key = CooldownIsolateLevel.GLOBAL.name
        if XiuConfig().third_party_bot:
            if sql_message.is_xiuxian_enabled(group_id):
                if (
                        event.sender.role == "admin" or
                        event.sender.role == "owner" or
                        event.get_user_id() in bot.config.superusers
                ):
                    bot = await assign_bot_group(group_id=group_id)
                    if at_sender:
                        await bot.send(event=event, message=MessageSegment.at(
                            event.get_user_id()) + "本群已关闭修仙模组,请联系管理员开启,开启命令为【启用修仙功能】!")
                    else:
                        await bot.send(event=event,
                                       message="本群已关闭修仙模组,请联系管理员开启,开启命令为【启用修仙功能】!")
                    await matcher.finish()
                else:
                    await matcher.finish()
            else:
                pass
        if stamina_cost > 0:
            user_data = sql_message.get_user_info_with_id(user_id)
            if user_data:
                if user_data['user_stamina'] < stamina_cost:
                    msg = "你没有足够的体力，请等待体力恢复后再试！"
                    await bot.send_group_msg(group_id=int(group_id), message=msg)
                    await matcher.finish()
                sql_message.update_user_stamina(user_id, stamina_cost, 2)  # 减少体力
        if running[key] <= 0:
            if cd_time >= 1.5:
                time = int(cd_time - (loop.time() - time_sy[key]))
                if time <= 1:
                    time = 1
                formatted_time = format_time(time)
                if XiuConfig().img:
                    pic = await get_msg_pic(
                        f"@{event.sender.nickname}\n" + get_random_chat_notice().format(formatted_time))
                    bot = await assign_bot_group(group_id=group_id)
                    await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
                    await matcher.finish()
                else:
                    bot = await assign_bot_group(group_id=group_id)
                    await bot.send_group_msg(group_id=int(group_id),
                                             message=get_random_chat_notice().format(formatted_time))
                    await matcher.finish()
            else:
                await matcher.finish()
        else:
            time_sy[key] = int(loop.time())
            running[key] -= 1
            loop.call_later(cd_time, lambda: increase(key))
        return

    return Depends(dependency)


put_bot = XiuConfig().put_bot
main_bot = XiuConfig().main_bo
layout_bot_dict = XiuConfig().layout_bot_dict


async def check_bot(bot: Bot) -> bool:  # 检测bot实例是否为主qq
    if str(bot.self_id) in put_bot:
        return True
    else:
        return False


def check_rule_bot() -> Rule:  # 对传入的消息检测，是主qq传入的消息就响应，其他的不响应
    async def _check_bot_(bot: Bot, event: GroupMessageEvent) -> bool:
        if str(bot.self_id) in put_bot:
            if str(event.get_user_id()) in main_bot:
                return False
            else:
                return True
        else:
            return False

    return Rule(_check_bot_)


async def range_bot(bot: Bot, event: GroupMessageEvent):  # 随机一个qq发送消息
    group_id = str(event.group_id)
    bot_list = list(get_bots().keys())
    try:
        bot = get_bots()[random.choice(bot_list)]
    except KeyError:
        pass
    return bot, group_id


async def assign_bot(bot=None, event=None):  # 按字典分配对应qq发送消息
    group_id = str(event.group_id)
    try:
        bot_id = layout_bot_dict[group_id]
        if type(bot_id) is str:
            bot = get_bots()[bot_id]
        elif type(bot_id) is list:
            bot = get_bots()[random.choice(bot_id)]
        else:
            bot = bot
    except:
        bot = bot
    return bot, group_id


async def assign_bot_group(group_id):  # 只导入群号，按字典分配对应qq发送消息
    group_id = str(group_id)
    try:
        bot_id = layout_bot_dict[group_id]
        if type(bot_id) is str:
            bot = get_bots()[bot_id]
        elif type(bot_id) is list:
            bot = get_bots()[random.choice(bot_id)]
        else:
            bot = get_bots()[put_bot[0]]
    except KeyError:
        bot = None
    except Exception as e:
        logger.opt(colors=True).error(f"<red>错误: {e}</red>")

    if bot is None:
        try:
            bot = get_bot()
        except ValueError:
            logger.opt(colors=True).error(f"<red>未找到对应的bot实例,请检查实现端链接状况！</red>")
            bot = None

    return bot
