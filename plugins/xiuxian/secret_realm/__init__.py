import random
from datetime import datetime, timedelta
from nonebot import get_bots, on_command, require
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
from nonebot.permission import SUPERUSER
from nonebot.log import logger

from .riftmake import get_story_type, NONEMSG, get_battle_type, get_dxsj_info, get_boss_battle_info, get_treasure_info
from ..xiuxian_utils.lay_out import assign_bot, assign_bot_group, Cooldown
from ..xiuxian_utils.utils import check_user, check_user_type, send_msg_handler
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage

sql_message = XiuxianDateManage()  # sql类

create_rift = on_command("生成秘境", priority=5, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),
                         block=True)
explore_rift = on_command("探索秘境", priority=5, permission=GROUP, block=True)
complete_rift = on_command("秘境结算", priority=7, permission=GROUP, block=True)
break_rift = on_command("秘境探索终止", priority=7, permission=GROUP, block=True)
view_rift = on_command("秘境查看", priority=7, permission=GROUP, block=True)

# 定时任务
set_rift = require("nonebot_plugin_apscheduler").scheduler


@set_rift.scheduled_job("cron", hour=21, minute=59)
async def set_rift_():
    """秘境信息次数重置成功"""
    # 获取秘境信息
    rift_info = sql_message.get_mijing_info()
    rift_info_name = rift_info['name']
    config_id = sql_message.get_random_config_id()
    rift_info = sql_message.get_config_by_id(config_id)
    # 更新秘境信息
    sql_message.update_dingshi_mijing_info(rift_info_name, rift_info['name'], rift_info['rank'],
                                           rift_info['base_count'], '', rift_info['time'])

    logger.opt(colors=True).info(f"<green>秘境信息次数重置成功</green>")


@view_rift.handle(parameterless=[Cooldown(at_sender=False)])
async def view_rift_(bot: Bot, event: GroupMessageEvent):
    """秘境查看"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await view_rift.finish()

    if not sql_message.is_mijing_enabled(send_group_id):  # 不在配置表内
        msg = f"本群尚未开启秘境功能,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await view_rift.finish()
    # 获取秘境信息
    rift_info = sql_message.get_mijing_info()
    if not rift_info:
        msg = f"当前没有正在进行的秘境。"
        await bot.send_group_msg(group_id=int(event.group_id), message=msg)
        await view_rift.finish()

    has_participated = False
    user_id = str(event.user_id)
    if rift_info['l_user_id']:
        user_ids = rift_info['l_user_id'].split(',')
        has_participated = user_id in user_ids

    msg = f"当前秘境：{rift_info['name']}\n可探索次数：{rift_info['current_count']}次"
    if has_participated:
        msg += f"\n(您已参加过此秘境)"

    # 秘境剩余时间提示 待处理
    if rift_info['time'] > 0:
        msg += f"\n预计耗时：{rift_info['time']}分钟"

    await bot.send_group_msg(group_id=int(event.group_id), message=msg)
    await view_rift.finish()


@create_rift.handle()
async def create_rift_(bot: Bot, event: GroupMessageEvent):
    """生成秘境"""
    # 获取秘境信息
    rift_info = sql_message.get_mijing_info()
    if rift_info:
        msg = f"当前已存在秘境，请诸位道友发送 探索秘境 来加入吧！"
        await bot.send_group_msg(group_id=int(event.group_id), message=msg)
        await create_rift.finish()

    # 创建新的秘境
    config_id = sql_message.get_random_config_id()
    rift_info = sql_message.get_config_by_id(config_id)
    if not rift_info:
        raise ValueError("No valid configuration found.")

    # 使用字典索引
    sql_message.insert_mijing_info(rift_info['name'], rift_info['rank'], rift_info['base_count'], "", rift_info['time'])

    # 发送消息通知群成员
    msg = f'''野生的{rift_info['name']}出现了！
    秘境可探索次数：{rift_info['base_count']}次;
    请诸位道友发送 探索秘境 来加入吧！'''
    await bot.send_group_msg(group_id=int(event.group_id), message=msg)

    await create_rift.finish()


@explore_rift.handle(parameterless=[Cooldown(stamina_cost=6, at_sender=False)])
async def explore_rift_(bot: Bot, event: GroupMessageEvent):
    """探索秘境"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    if not sql_message.is_mijing_enabled(send_group_id):  # 不在配置表内
        msg = f"本群尚未开启秘境功能,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()

    user_id = user_info['user_id']
    is_type, msg = check_user_type(user_id, 0)  # 需要无状态的用户
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await explore_rift.finish()
    # 获取秘境信息
    rift_info = sql_message.get_mijing_info()
    if not rift_info:
        msg = '野外秘境尚未生成，请道友耐心等待!'
        await bot.send_group_msg(group_id=int(event.group_id), message=msg)
        await explore_rift.finish()

    if str(event.user_id) in rift_info['l_user_id'].split(','):
        msg = '道友已经参加过本次秘境啦，请把机会留给更多的道友！'
        await bot.send_group_msg(group_id=int(event.group_id), message=msg)
        await explore_rift.finish()

    sql_message.do_work(user_id, 3, rift_info["name"])
    rift_count = rift_info['current_count']
    if rift_count <= 0:
        msg = '秘境随着道友的进入，已无法再维持更多的人，而关闭了！'
        await bot.send_group_msg(group_id=int(event.group_id), message=msg)
        await explore_rift.finish()

    # 更新秘境信息
    new_count = rift_count - 1
    updated_l_user_id = f"{rift_info['l_user_id']},{event.user_id}" if rift_info['l_user_id'] else str(event.user_id)
    sql_message.update_mijing_info(rift_info['name'], rift_info['rank'], new_count, updated_l_user_id,
                                   rift_info['time'])

    msg = f"道友进入秘境：{rift_info['name']}，探索需要花费时间：{rift_info['time']}分钟！"
    await bot.send_group_msg(group_id=int(event.group_id), message=msg)

    if new_count == 0:
        msg += "秘境随着道友的进入，已无法再维持更多的人，而关闭了！"
        await bot.send_group_msg(group_id=int(event.group_id), message=msg)
        await explore_rift.finish()

    await explore_rift.finish()


@complete_rift.handle(parameterless=[Cooldown(at_sender=False)])
async def complete_rift_(bot: Bot, event: GroupMessageEvent):
    """秘境结算"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    if not sql_message.is_mijing_enabled(send_group_id):  # 不在配置表内
        msg = f"本群尚未开启秘境功能,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    # 需要在秘境的用户
    is_type, msg = check_user_type(user_info['user_id'], 3)
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    # 获取秘境信息
    rift_info = sql_message.get_mijing_info()
    if not rift_info:
        msg = '野外秘境尚未生成，请道友耐心等待!'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    # 获取用户的冷却时间信息并检查类型
    user_cd_message = sql_message.get_user_cd(user_info['user_id'])
    if user_cd_message is not None and 'create_time' in user_cd_message:
        create_time = user_cd_message['create_time']

        # 检查 create_time 的类型
        if isinstance(create_time, str):
            try:
                work_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                msg = "\n上次探索时间无法识别。"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await complete_rift.finish()
        elif isinstance(create_time, datetime):
            work_time = create_time
        else:
            msg = "\n上次探索时间无法识别。"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await complete_rift.finish()
    else:
        msg = "\n没有记录到您的上次探索时间。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()

    exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
    time2 = rift_info["time"]

    if exp_time < time2:
        msg = f"进行中的：{rift_info['name']}探索，预计{time2 - exp_time}分钟后可结束"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await complete_rift.finish()
    else:
        sql_message.do_work(user_info['user_id'], 0)
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

    if not sql_message.is_mijing_enabled(send_group_id):  # 不在配置表内
        msg = f"本群尚未开启秘境功能,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()

    user_id = user_info['user_id']

    is_type, msg = check_user_type(user_id, 3)  # 需要在秘境的用户
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()
    else:
        mijing_name = sql_message.get_user_cd(user_id)['scheduled_time']
        sql_message.do_work(user_id, 0)
        msg = f"已终止{mijing_name}秘境的探索！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await break_rift.finish()
