import asyncio
import base64
import json
import random
from re import I
from typing import Any, Tuple

from nonebot import on_message
from nonebot import on_regex, on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    MessageEvent,
    GroupMessageEvent
)
from nonebot.log import logger
from nonebot.params import RegexGroup

from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.utils import (
    check_user
)
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage

cache_help = {}
sql_message = XiuxianDateManage()  # sql类

md = {"keyboard": {"id": "102125567_1726457673"}}
json1 = json.dumps(md)
bytes = json1.encode('utf-8')
data = base64.b64encode(bytes).decode('utf-8')
markdown_message = f"[CQ:markdown,data=base64://{data}]"

__peiyang_help__ = f"""
鉴定灵石帮助:
【鉴石秘技】
　　在修仙的世界里，灵石不仅是修行者们最宝贵的财富之一，更是通往更高境界的关键。然而，灵石之中往往蕴含着未知的秘密——有的灵石看似平凡无奇，却可能蕴藏着巨大的潜力；有的灵石外表华丽，实则一文不值。只有真正的鉴石大师才能洞察其中的奥秘。
　　当你使用「鉴石」指令时，将会尝试揭示灵石中的潜在能量。如果你的运气足够好，或许能发现那些隐藏在普通灵石中的惊人价值，甚至获得更多的灵石作为奖励。但若是运气不佳，也可能导致灵石失去原有的价值，甚至造成一定的损失。
　　指令(最低境界要求【{XiuConfig().peiyang_min}】):
　　　　鉴石 [灵石数量]
【注意事项】
- 鉴石是一项充满不确定性的活动，务必谨慎行事。
- 仅限达到一定境界的修行者方可尝试，以免因修为不足而遭受反噬。
- 鉴石过程中，可能会触发各种意外事件，增加鉴石的趣味性和挑战性。
""".strip()

# 培养
peiyang_help = on_command("鉴石帮助", permission=GROUP, priority=7, block=True)
peiyang = on_regex(
    r"(鉴石)\s?(\d+)",
    flags=I,
    permission=GROUP,
    block=True
)

# 创建一个监听器来监听消息
listen_for_reply = on_message(priority=1, block=False)

# 全局字典存储等待的事件和回调函数
waiting_callbacks = {}

@listen_for_reply.handle()
async def handle_reply(bot: Bot, event: MessageEvent):
    global waiting_callbacks
    # 获取当前等待回复的事件ID
    event_id = f"{event.get_user_id()}_{event.get_session_id()}"
    if event_id in waiting_callbacks:
        # 存储玩家的回复
        waiting_callbacks[event_id] = event.get_plaintext().strip().lower()
        # 取消监听器
        listen_for_reply.stop_propagation(event)


async def get_response(bot: Bot, event: MessageEvent, default_response='否') -> str:
    """
    获取玩家的回复。

    :param bot: Bot 对象
    :param event: Event 对象
    :param default_response: 超时后的默认回复
    :return: 玩家的回复或默认回复
    """
    global waiting_callbacks

    # 生成一个唯一的事件ID来标识等待的回复
    event_id = f"{event.get_user_id()}_{event.get_session_id()}"
    waiting_callbacks[event_id] = None  # 标记正在等待回复

    # 在一定时间内等待玩家的回复
    try:
        # 等待直到事件ID对应的回复出现或超时
        await asyncio.wait_for(asyncio.shield(check_reply(event_id)), timeout=30)  # 设置超时时间为30秒
    except asyncio.TimeoutError:
        logger.warning("等待玩家回复超时")
        return default_response

    # 返回玩家的回复
    return waiting_callbacks.pop(event_id, default_response)

async def check_reply(event_id):
    while True:
        if event_id in waiting_callbacks and waiting_callbacks[event_id] is not None:
            return
        await asyncio.sleep(0.1)

@peiyang_help.handle(parameterless=[Cooldown(at_sender=False)])
async def peiyang_help_(bot: Bot, event: GroupMessageEvent):
    """鉴定灵石帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __peiyang_help__
    await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+msg)
    await peiyang_help.finish()



@peiyang.handle(parameterless=[Cooldown(cd_time=XiuConfig().peiyang_cd, at_sender=False)])
async def peiyang_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    """鉴定灵石"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    isUser, user_info, msg = check_user(event)
    user_id = user_info['user_id']
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await peiyang.finish()

    user_message = sql_message.get_user_info_with_id(user_id)
    investment_amount = args[1]
    # 随机1~1000的值
    value = random.randint(1, 1000)

    level = user_info['level']
    list_level_all = list(jsondata.level_data().keys())

    if list_level_all.index(level) < list_level_all.index(XiuConfig().peiyang_min):
        msg = f"鉴定秘术需要道友境界至少为{XiuConfig().peiyang_min}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await peiyang.finish()

    if int(investment_amount) <= 0:
        msg = "鉴定灵石的数量不能为零或负数，鉴石失败！"
        await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+msg)
        await peiyang.finish()

    if int(user_message['stone']) < int(investment_amount):
        msg = "道友的灵石不足，请重新输入！"
        await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+msg)
        await peiyang.finish()

    consecutive_wins, consecutive_losses = sql_message.get_consecutive_wins_and_losses(user_id)

    # 计算基础概率
    base_lose_rate = 500
    base_single_rate = 435
    double_rate = 50
    quintuple_rate = 10
    decuple_rate = 5

    # 根据灵石数量调整概率
    if int(investment_amount) >= 100000000:
        base_lose_rate += 100
        base_single_rate -= 100
    elif int(investment_amount) >= 10000000:
        base_lose_rate += 50
        base_single_rate -= 50
    elif int(investment_amount) >= 1000000:
        base_lose_rate += 20
        base_single_rate -= 20

    # 根据连胜和连败调整概率
    if consecutive_wins > 0:
        base_lose_rate += consecutive_wins * 10
        base_single_rate -= consecutive_wins * 10
    if consecutive_losses > 0:
        base_single_rate += consecutive_losses * 10
        base_lose_rate -= consecutive_losses * 10

    # 确保总概率为1000
    total_rate = base_single_rate + double_rate + quintuple_rate + decuple_rate + base_lose_rate
    if total_rate != 1000:
        diff = 1000 - total_rate
        base_single_rate += diff

    # 生成特殊事件及权重
    special_events_weights = {
        'normal': 50,
        'mystery': 10,
        'crack': 10,
        'blessing_stone': 500,
        'shatter': 10,
        'purify': 10,
        'blessing': 10,
        'curse': 10,
        'resonance': 1,
        'strengthen': 10
    }

    def generate_special_event(weights=special_events_weights):
        total_weight = sum(weights.values())
        random_value = random.random() * total_weight
        current_weight = 0
        for event, weight in weights.items():
            current_weight += weight
            if random_value <= current_weight:
                return event

    special_event = generate_special_event()

    # 处理特殊事件
    event_msg = ""
    if special_event == 'mystery':
        double_rate += 10
        quintuple_rate += 10
        decuple_rate += 10
        event_msg = "在鉴定过程中，您发现了一块神秘灵石，收益概率略微提升！"

    elif special_event == 'crack':
        double_rate -= 10
        quintuple_rate -= 10
        decuple_rate -= 10
        event_msg = "在鉴定过程中，灵石突然出现了裂缝，收益概率略微减低！"

    elif special_event == 'blessing_stone':
        sql_message.update_ls(user_id, 500000, 1)
        event_msg = f"在鉴定过程中，您发现了一块天赐神石！恭喜【{user_info['user_name']}】道友！您获得了天赐神石，直接获得500000块灵石！\n现有灵石：{int(user_message['stone']) + 500000}块"
        await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+event_msg)
        await peiyang.finish()

    elif special_event == 'shatter':
        sql_message.update_ls(user_id, int(investment_amount), 2)
        event_msg = f"在鉴定过程中，灵石突然完全破碎！道友此次鉴石，灵石完全破碎，损失所有投资的灵石。\n现有灵石：{int(user_message['stone']) - int(investment_amount)}块"
        await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+event_msg)
        await peiyang.finish()

    elif special_event == 'purify':
        consecutive_wins = 0
        consecutive_losses = 0
        event_msg = "在鉴定过程中，灵石得到了净化，收益概率略微提升！"

    elif special_event == 'blessing':
        double_rate += 10
        quintuple_rate += 10
        decuple_rate += 10
        event_msg = "在鉴定过程中，您得到了灵石祝福，收益概率略微提升！"

    elif special_event == 'curse':
        double_rate -= 10
        quintuple_rate -= 10
        decuple_rate -= 10
        event_msg = "在鉴定过程中，您受到了灵石诅咒，收益概率略微下降！"

    elif special_event == 'resonance':
        response = await get_response(bot, event)
        if response == '是':
            user_id = int(event.user_id)
            other_user_id = sql_message.get_random_user_id()
            other_user_info = sql_message.get_user_info_with_id(other_user_id)
            other_user_info_name = other_user_info['user_name']

            if other_user_id == user_id:
                msg = "您随机选中了自己！本次胜利则获得双倍，失败则损失双倍。"
                await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+msg)
                await peiyang.finish()
            else:
                event_msg = f"您随机到了与{other_user_info_name}道友共享收益或损失。"
        else:
            event_msg = "您选择了不与其他道友共享收益或损失。"

    # 判断结果并更新灵石数量
    if 1 <= value <= base_single_rate:  # 单倍收获
        new_stone_count = int(investment_amount)
        if special_event == 'resonance' and response == '是':
            if other_user_id == user_id:
                new_stone_count *= 2
                sql_message.update_ls(user_id, new_stone_count, 1)
                msg = f"道友慧眼识珠，鉴石之时，灵光闪耀，天降祥瑞！\n您获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
            else:
                sql_message.update_ls(user_id, new_stone_count, 1)
                sql_message.update_ls(other_user_id, new_stone_count, 1)
                msg = f"道友慧眼识珠，鉴石之时，灵光闪耀，天降祥瑞！\n您和{other_user_info_name}道友各获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        else:
            sql_message.update_ls(user_id, new_stone_count, 1)
            msg = f"道友慧眼识珠，鉴石之时，灵光闪耀，天降祥瑞！\n您发现了潜藏在灵石之中的巨大潜力，为您带来了丰厚的回报。\n收获{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        consecutive_wins += 1
        consecutive_losses = 0
    elif base_single_rate < value <= (base_single_rate + double_rate):  # 双倍收获
        new_stone_count = int(investment_amount) * 2
        if special_event == 'resonance' and response == '是':
            if other_user_id == user_id:
                new_stone_count *= 2
                sql_message.update_ls(user_id, new_stone_count, 1)
                msg = f"道友独具慧眼！灵石之中蕴含着强大的力量，为您带来了意外的收获。\n您获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
            else:
                sql_message.update_ls(user_id, new_stone_count, 1)
                sql_message.update_ls(other_user_id, new_stone_count, 1)
                msg = f"道友独具慧眼！灵石之中蕴含着强大的力量，为您和{other_user_info_name}道友带来了意外的收获。\n您和其他玩家各获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        else:
            sql_message.update_ls(user_id, new_stone_count, 1)
            msg = f"道友独具慧眼！灵石之中蕴含着强大的力量，为您带来了意外的收获。\n收获{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        consecutive_wins += 1
        consecutive_losses = 0
    elif (base_single_rate + double_rate) < value <= (base_single_rate + double_rate + quintuple_rate):  # 五倍收获
        new_stone_count = int(investment_amount) * 5
        if special_event == 'resonance' and response == '是':
            if other_user_id == user_id:
                new_stone_count *= 2
                sql_message.update_ls(user_id, new_stone_count, 1)
                msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼！\n灵石之中竟然蕴含着惊人的力量，为您带来了意想不到的巨大收获。\n您获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
            else:
                sql_message.update_ls(user_id, new_stone_count, 1)
                sql_message.update_ls(other_user_id, new_stone_count, 1)
                msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼！\n灵石之中竟然蕴含着惊人的力量，为您和{other_user_info_name}道友带来了意想不到的巨大收获。\n您和其他玩家各获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        else:
            sql_message.update_ls(user_id, new_stone_count, 1)
            msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼！\n灵石之中竟然蕴含着惊人的力量，为您带来了意想不到的巨大收获。\n收获{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        consecutive_wins += 1
        consecutive_losses = 0
    elif (base_single_rate + double_rate + quintuple_rate) < value <= (base_single_rate + double_rate + quintuple_rate + decuple_rate):  # 十倍收获
        new_stone_count = int(investment_amount) * 10
        if special_event == 'resonance' and response == '是':
            if other_user_id == user_id:
                new_stone_count *= 2
                sql_message.update_ls(user_id, new_stone_count, 1)
                msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼！\n灵石之中竟然蕴含着惊人的力量，为您带来了意想不到的巨大收获。\n您获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
            else:
                sql_message.update_ls(user_id, new_stone_count, 1)
                sql_message.update_ls(other_user_id, new_stone_count, 1)
                msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼！\n灵石之中竟然蕴含着惊人的力量，为您和{other_user_info_name}道友带来了意想不到的巨大收获。\n您和其他玩家各获得了{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        else:
            sql_message.update_ls(user_id, new_stone_count, 1)
            msg = f"恭喜【{user_info['user_name']}】道友！您独具慧眼！\n灵石之中竟然蕴含着惊人的力量，为您带来了意想不到的巨大收获。\n收获{new_stone_count}块灵石！\n现有灵石：{int(user_message['stone']) + new_stone_count}块"
        consecutive_wins += 1
        consecutive_losses = 0
    else:  # 损失当前灵石
        loss_amount = int(investment_amount)
        if special_event == 'resonance' and response == '是':
            if other_user_id == user_id:
                loss_amount *= 2
                sql_message.update_ls(user_id, loss_amount, 2)
                msg = f"道友此次鉴石，未能洞察灵石中的秘密，灵石似乎失去了原有的光芒。\n您损失了{loss_amount}块灵石！\n现有灵石：{int(user_message['stone']) - loss_amount}块"
            else:
                sql_message.update_ls(user_id, loss_amount, 2)
                sql_message.update_ls(other_user_id, loss_amount, 2)
                msg = f"道友此次鉴石，未能洞察灵石中的秘密，灵石似乎失去了原有的光芒。\n您和{other_user_info_name}道友各损失了{loss_amount}块灵石！\n现有灵石：{int(user_message['stone']) - loss_amount}块"
        else:
            sql_message.update_ls(user_id, loss_amount, 2)
            msg = f"道友此次鉴石，未能洞察灵石中的秘密，灵石似乎失去了原有的光芒。\n消耗{loss_amount}块灵石未能收获，期待下一次的丰收吧！\n现有灵石：{int(user_message['stone']) - loss_amount}块"
        consecutive_losses += 1
        consecutive_wins = 0

    # 合并事件消息和收获消息
    final_msg = f"{event_msg}\n{msg}" if event_msg else msg
    await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message+final_msg)

    # 更新用户的连胜和连败次数
    sql_message.update_consecutive_wins_and_losses(user_id, consecutive_wins, consecutive_losses)