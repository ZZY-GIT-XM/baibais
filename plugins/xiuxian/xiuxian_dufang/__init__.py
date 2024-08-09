import random
from re import I
from typing import Any, Tuple
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from nonebot import on_regex, on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    MessageEvent,
    GroupMessageEvent,
    MessageSegment
)
from nonebot.params import RegexGroup
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.utils import (
    check_user,
    get_msg_pic,
    CommandObjectID
)
cache_help = {}
sql_message = XiuxianDateManage()  # sql类

__dufang_help__ = f"""
天才培养，专门针对修仙界的天才修士进行早期培养，帮助他们克服修炼初期的困难，期待未来能获得丰厚的回报。
指令(最低境界要求【{XiuConfig().peiyang_min}】):
    培养66666
""".strip()


# 培养
dufang_help = on_command("天才培养帮助", permission=GROUP, priority=7, block=True)
dufang = on_regex(
    r"(培养)\s?(\d+)",
    flags=I,
    permission=GROUP,
    block=True
)

@dufang_help.handle(parameterless=[Cooldown(at_sender=False)])
async def dufang_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await dufang_help.finish()
    else:
        msg = __dufang_help__
        if XiuConfig().img:
            pic = await get_msg_pic(msg)
            cache_help[session_id] = pic
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await dufang_help.finish()


@dufang.handle(parameterless=[Cooldown(cd_time=XiuConfig().dufang_cd, at_sender=False)])
async def dufang_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    isUser, user_info, msg = check_user(event)
    user_id = user_info['user_id']
    if not isUser:
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await dufang.finish()

    user_message = sql_message.get_user_info_with_id(user_id)
    investment_amount = args[1]
    # full_investment_str = f"培养 {investment_amount}"

    if (user_info['level'] < XiuConfig().peiyang_min):
        msg = f"培养天才需要道友境界最低要求为{XiuConfig().peiyang_min}"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await dufang.finish()
    
    # 检查培养金额是否有效
    if int(investment_amount) <= 0:
        msg = "培养灵石不能为零或负数，培养失败！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await dufang.finish()

    # 判断灵石是否足够
    if int(user_message['stone']) < int(investment_amount):
        msg = "道友的灵石不足，请重新输入！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await dufang.finish()


    # 获取用户的连胜和连败次数
    consecutive_wins, consecutive_losses = sql_message.get_consecutive_wins_and_losses(user_id)

    # 根据培养金额调整胜率和五倍概率
    if int(investment_amount) <= 50000:
        win_rate = 60
        five_times_rate = 10
        lose_rate = 30
    elif 50001 <= int(investment_amount) <= 1000000:
        win_rate = 45
        five_times_rate = 3
        lose_rate = 52
    else:  # int(investment_amount) > 1000000
        win_rate = 40
        five_times_rate = 1
        lose_rate = 59

    # 根据连胜和连败次数调整概率
    if consecutive_wins > 5:
        lose_rate += 10
    elif consecutive_losses > 3:
        win_rate += 10
        lose_rate -= 10

    # 随机1~100的值
    value = random.randint(1, 100)

    # 判断结果
    if 1 <= value <= win_rate:  # 单倍胜率
        sql_message.update_ls(user_id, int(investment_amount), 1)
        msg = f"【{user_info['user_name']}】道友慧眼识珠，培养的天才茁壮成长，为您带来了丰厚的回报——{investment_amount}块灵石！"
        consecutive_wins += 1
        consecutive_losses = 0
    elif win_rate < value <= (win_rate + lose_rate):  # 输掉的概率
        sql_message.update_ls(user_id, int(investment_amount), 2)
        msg = f"虽然这次消耗{investment_amount}块灵石未能收获，但【{user_info['user_name']}】道友培养的天才正在努力成长，期待下一次的丰收吧！"
        consecutive_losses += 1
        consecutive_wins = 0
    else:  # 五倍概率
        sql_message.update_ls(user_id, int(investment_amount) * 5, 1)
        msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼，发现了绝世天才，此次收获灵石{int(investment_amount) * 5}块！"
        consecutive_wins += 1
        consecutive_losses = 0

    # 更新用户的连胜和连败次数
    sql_message.update_consecutive_wins_and_losses(user_id, consecutive_wins, consecutive_losses)

    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    await dufang.finish()