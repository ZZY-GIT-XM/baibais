import random
from datetime import datetime, timedelta
from nonebot import get_bots, on_command, require, on_fullmatch
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    GROUP_ADMIN,
    GROUP_OWNER,
    MessageSegment
)
from .old_rift_info import old_rift_info
from .. import DRIVER
from ..xiuxian_utils.lay_out import assign_bot, assign_bot_group, Cooldown
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_utils.utils import (
    check_user, check_user_type,
    send_msg_handler, get_msg_pic, CommandObjectID
)
from .riftconfig import get_rift_config, savef_rift
from .jsondata import save_rift_data, read_rift_data
from ..xiuxian_config import XiuConfig
from .riftmake import (
    Rift, get_rift_type, get_story_type, NONEMSG, get_battle_type,
    get_dxsj_info, get_boss_battle_info, get_treasure_info
)

config = get_rift_config()
sql_message = XiuxianDateManage()  # sql类
cache_help = {}
group_rift = config.get("group_rift", {})  # 读取配置文件
groups = config.get('open', [])
# 定时任务
set_rift = require("nonebot_plugin_apscheduler").scheduler

set_group_rift = on_command("群秘境", priority=4, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),
                            block=True)
explore_rift = on_fullmatch("探索秘境", priority=5, permission=GROUP, block=True)
rift_help = on_fullmatch("秘境帮助", priority=6, permission=GROUP, block=True)
create_rift = on_fullmatch("生成秘境", priority=5, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),
                           block=True)
complete_rift = on_command("秘境结算", aliases={"结算秘境"}, priority=7, permission=GROUP, block=True)
break_rift = on_command("秘境探索终止", aliases={"终止探索秘境"}, priority=7, permission=GROUP, block=True)
view_rift = on_command("秘境查看", aliases={"查看秘境"}, priority=7, permission=GROUP, block=True)

__rift_help__ = f"""
秘境帮助信息(默认开启中):
指令：
1. 群秘境开启: 开启本群的秘境生成功能，管理员权限
2. 群秘境关闭: 关闭本群的秘境生成功能，管理员权限
3. 生成秘境: 生成一个随机秘境，超管权限
4. 探索秘境: 探索秘境获取随机奖励
5. 秘境结算: 结算秘境奖励
6. 终止探索秘境: 终止秘境事件
7. 秘境帮助: 获取秘境帮助信息

非指令：
1. 每天早上8点自动生成一个随机等级的秘境

说明：
- 群秘境开启：开启本群的秘境生成功能，允许生成新的秘境。
- 群秘境关闭：关闭本群的秘境生成功能，不允许生成新的秘境。
""".strip()


@DRIVER.on_startup
async def read_rift_():
    global group_rift
    group_rift.update(old_rift_info.read_rift_info())
    logger.opt(colors=True).info("<green>历史rift数据读取成功</green>")


@DRIVER.on_shutdown
async def save_rift_():
    global group_rift
    old_rift_info.save_rift(group_rift)
    logger.opt(colors=True).info("<green>rift数据已保存</green>")


# 定时任务生成群秘境
@set_rift.scheduled_job("cron", hour=8, minute=0)
async def set_rift_():
    global group_rift
    group_rift = config.get("group_rift", {})

    # 确保groups变量存在且非空
    if not groups:
        return

    for group_id in groups:
        if group_id not in config.get('blocked', []):  # 检查是否被屏蔽
            bot = await assign_bot_group(group_id=group_id)
            rift = Rift()
            rift.name = get_rift_type()
            rift.rank = config['rift'].get(rift.name, {}).get('rank', 1)  # 默认值为1
            rift.count = config['rift'].get(rift.name, {}).get('count', 1)  # 默认值为1
            rift.time = config['rift'].get(rift.name, {}).get('time', 0)  # 默认值为0
            group_rift[group_id] = rift
            msg = f"秘境已刷新，野生的{rift.name}已开启！可探索次数：{rift.count}次，请诸位道友发送 探索秘境 来加入吧！"
            pic = await get_msg_pic(msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))

    # 保存新的秘境信息到配置文件
    config['group_rift'] = group_rift
    savef_rift(config)


@rift_help.handle(parameterless=[Cooldown(at_sender=False)])
async def rift_help_(bot: Bot, event: GroupMessageEvent):
    """秘境帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    # 构造帮助信息
    msg = __rift_help__

    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await rift_help.finish()


@view_rift.handle()
async def view_rift_(bot: Bot, event: GroupMessageEvent):
    """秘境查看"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    group_id = str(event.group_id)

    # 从全局变量中获取秘境信息
    rift = group_rift.get(group_id, {})

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await view_rift.finish()

    if not rift:
        msg = f"当前没有正在进行的秘境。"
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await view_rift.finish()

    user_id = user_info['user_id']
    has_participated = user_id in getattr(rift, 'l_user_id', [])

    msg = f"当前秘境：{getattr(rift, 'name', '未知秘境')}\n可探索次数：{getattr(rift, 'count', 0)}次"
    if has_participated:
        msg += f"\n(您已参加过此秘境)"

    # 添加剩余时间提示
    if hasattr(rift, 'start_time') and hasattr(rift, 'duration'):
        start_time = datetime.strptime(getattr(rift, 'start_time'), "%Y-%m-%d %H:%M:%S")
        remaining_time = (start_time + timedelta(minutes=getattr(rift, 'duration'))) - datetime.now()
        if remaining_time.total_seconds() > 0:
            msg += f"\n剩余时间：{int(remaining_time.total_seconds() / 60)}分钟"

    await bot.send_group_msg(group_id=int(group_id), message=msg)
    await view_rift.finish()


@create_rift.handle(parameterless=[Cooldown(stamina_cost=6, at_sender=False)])
async def create_rift_(bot: Bot, event: GroupMessageEvent):
    """生成秘境"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)

    # 使用全局配置
    is_blocked = group_id in config.get('blocked', [])  # 检查群聊是否被屏蔽

    if is_blocked:
        msg = '本群已被屏蔽，请联系管理员解除屏蔽'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await create_rift.finish()

    # 检查 group_rift 中是否有 group_id
    if group_id in group_rift:
        msg = f"当前已存在{group_rift[group_id].name}，秘境可探索次数：{group_rift[group_id].count}次，请诸位道友发送 探索秘境 来加入吧！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await create_rift.finish()

    # 创建新的秘境
    rift = Rift()
    rift.name = get_rift_type()

    # 确保 config 中有 'rift' 键
    if 'rift' not in config:
        config['rift'] = {}

    # 确保 config['rift'] 中有 rift.name 键
    if rift.name not in config['rift']:
        config['rift'][rift.name] = {
            'rank': 1,  # 默认值
            'count': 10,  # 默认值
            'time': 60  # 默认值
        }

    rift.rank = config['rift'][rift.name]['rank']
    rift.count = config['rift'][rift.name]['count']
    rift.time = config['rift'][rift.name]['time']

    # 将新秘境保存到 group_rift
    group_rift[group_id] = rift

    # 发送消息通知群成员
    msg = f"野生的{rift.name}出现了！秘境可探索次数：{rift.count}次，请诸位道友发送 探索秘境 来加入吧！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    # 保存配置文件
    try:
        old_rift_info.save_rift(group_rift)
    except Exception as e:
        msg = "秘境生成成功，但保存配置文件失败，请稍后再试。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await create_rift.finish()
    else:
        await create_rift.finish()




@explore_rift.handle(parameterless=[Cooldown(stamina_cost=6, at_sender=False)])
async def _(bot: Bot, event: GroupMessageEvent):
    """探索秘境"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    user_id = user_info['user_id']
    is_type, msg = check_user_type(user_id, 0)  # 需要无状态的用户
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    group_id = str(event.group_id)
    config = get_rift_config()  # 获取配置
    is_blocked = group_id in config.get('blocked', [])  # 检查群聊是否被屏蔽

    if is_blocked:
        msg = '本群已被屏蔽，请联系管理员解除屏蔽'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    try:
        rift = group_rift[group_id]
    except KeyError:
        msg = '野外秘境尚未生成，请道友耐心等待!'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    if user_id in rift.l_user_id:
        msg = '道友已经参加过本次秘境啦，请把机会留给更多的道友！'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    rift.l_user_id.append(user_id)
    rift.count -= 1
    msg = f"道友进入秘境：{rift.name}，探索需要花费时间：{rift.time}分钟！"
    rift_data = {
        "name": rift.name,
        "time": rift.time,
        "rank": rift.rank
    }

    save_rift_data(user_id, rift_data)
    sql_message.do_work(user_id, 3, rift_data["time"])

    if rift.count == 0:
        del group_rift[group_id]
        logger.opt(colors=True).info(f"<green>群{group_id}秘境已到上限次数！</green>")
        msg += "秘境随着道友的进入，已无法再维持更多的人，而关闭了！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    # 在保存配置文件之前将 Rift 对象转换为可序列化的字典
    old_rift_info.save_rift(group_rift)
    await explore_rift.finish()


@complete_rift.handle(parameterless=[Cooldown(at_sender=False)])
async def complete_rift_(bot: Bot, event: GroupMessageEvent):
    """秘境结算"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    user_id = user_info['user_id']
    group_id = str(event.group_id)
    config = get_rift_config()  # 获取配置
    is_blocked = group_id in config.get('blocked', [])  # 检查群聊是否被屏蔽

    if is_blocked:
        msg = '本群已被屏蔽，请联系管理员解除屏蔽'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    is_type, msg = check_user_type(user_id, 3)  # 需要在秘境的用户
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    try:
        rift_info = read_rift_data(user_id)
    except Exception as e:
        msg = '发生未知错误！'
        sql_message.do_work(user_id, 0)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    user_cd_message = sql_message.get_user_cd(user_id)
    work_time = datetime.strptime(user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f")
    exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
    time2 = rift_info["time"]

    if exp_time < time2:
        msg = f"进行中的：{rift_info['name']}探索，预计{time2 - exp_time}分钟后可结束"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()
    else:  # 秘境结算逻辑
        sql_message.do_work(user_id, 0)
        rift_rank = rift_info["rank"]  # 秘境等级
        rift_type = get_story_type()  # 无事、宝物、战斗

        if rift_type == "无事":
            msg = random.choice(NONEMSG)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await complete_rift.finish()

        elif rift_type == "战斗":
            rift_type = get_battle_type()
            if rift_type == "掉血事件":
                msg = get_dxsj_info("掉血事件", user_info)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await complete_rift.finish()

            elif rift_type == "Boss战斗":
                result, msg = await get_boss_battle_info(user_info, rift_rank, bot.self_id)
                await send_msg_handler(bot, event, result)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await complete_rift.finish()

        elif rift_type == "宝物":
            msg = get_treasure_info(user_info, rift_rank)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await complete_rift.finish()


@break_rift.handle(parameterless=[Cooldown(at_sender=False)])
async def break_rift_(bot: Bot, event: GroupMessageEvent):
    """终止探索秘境"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()

    user_id = user_info['user_id']
    group_id = str(event.group_id)
    config = get_rift_config()  # 获取配置
    is_blocked = group_id in config.get('blocked', [])  # 检查群聊是否被屏蔽

    if is_blocked:
        msg = '本群已被屏蔽，请联系管理员解除屏蔽'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()

    is_type, msg = check_user_type(user_id, 3)  # 需要在秘境的用户
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()
    else:
        try:
            rift_info = read_rift_data(user_id)
        except Exception as e:
            msg = '发生未知错误！'
            sql_message.do_work(user_id, 0)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await break_rift.finish()

        # 更新用户状态，确认用户已参加过本次探索
        rift = group_rift[group_id]
        rift.l_user_id.append(user_id)

        sql_message.do_work(user_id, 0)
        msg = f"已终止{rift_info['name']}秘境的探索！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()


@set_group_rift.handle(parameterless=[Cooldown(at_sender=False)])
async def set_group_rift_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """群秘境开启、关闭"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)

    # 获取配置
    config = get_rift_config()  # 假设有一个函数 get_rift_config() 来获取配置

    is_blocked = group_id in config['blocked']  # True 表示被屏蔽，False 表示未被屏蔽

    if mode == '开启':
        if is_blocked:
            msg = f"本群已被屏蔽，请先解除屏蔽再开启!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_rift.finish()
        else:
            msg = f"本群秘境已开启，无需重复开启!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_rift.finish()

    elif mode == '关闭':
        if is_blocked:
            msg = f"本群已被屏蔽，无需再次关闭!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_rift.finish()
        else:
            config['blocked'].append(group_id)
            savef_rift(config)  # 使用你现有的保存方法
            msg = f"已关闭本群秘境!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_rift.finish()

    else:
        msg = __rift_help__
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await set_group_rift.finish()


def is_in_groups(event: GroupMessageEvent):
    return str(event.group_id) in groups
