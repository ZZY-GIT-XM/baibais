import re
import json
import base64
import random
import asyncio
from datetime import datetime
from decimal import Decimal

from nonebot.typing import T_State

from ..xiuxian_back import get_item_msg_rank, check_equipment_can_use, get_use_equipment_sql, check_use_elixir, \
    get_use_jlq_msg
from ..xiuxian_utils.lay_out import assign_bot, Cooldown, assign_bot_group
from nonebot import require, on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GROUP_ADMIN,
    GROUP_OWNER,
    GroupMessageEvent,
    MessageSegment,
    ActionFailed
)
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot.params import CommandArg
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, XiuxianJsonDate, OtherSet,
    UserBuffDate, XIUXIAN_IMPART_BUFF, leave_harm_time
)
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.item_database_handler import Items
from ..xiuxian_utils.utils import (
    check_user,
    get_msg_pic, number_to,
    CommandObjectID,
    Txt2Img, send_msg_handler
)
from ..xiuxian_utils.qimingr import read_random_entry_from_file

items = Items()
sql_message = XiuxianDateManage()  # sql类

daily_qiandao = on_fullmatch("修仙签到", priority=13, permission=GROUP, block=True)
daily_xianyuan = on_command("仙途奇缘", permission=GROUP, priority=7, block=True)
daily_lianjin = on_command("炼金", priority=6, permission=GROUP, block=True)


@daily_lianjin.handle(parameterless=[Cooldown(at_sender=False)])
async def daily_lianjin_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """炼金"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()
    user_id = user_info['user_id']
    args = args.extract_plain_text().split()
    if not args:
        msg = f"{user_info['user_name']} 道友请输入要炼化的物品！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()
    goods_name = args[0]
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = f"{user_info['user_name']} 道友的背包空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    for back in back_msg:
        if goods_name == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_state = back['state']
            goods_num = back['goods_num']
            break
    if not in_flag:
        msg = f"{user_info['user_name']} 请检查该道具 {goods_name} 是否在背包内！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()

    if goods_type == "装备" and int(goods_state) == 1 and int(goods_num) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法炼金！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()

    if get_item_msg_rank(goods_id) == 520:
        msg = "此类物品不支持！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()
    try:
        if 1 <= int(args[1]) <= int(goods_num):
            num = int(args[1])
    except IndexError:
        num = 1
    price = int(6000000 - get_item_msg_rank(goods_id) * 100000) * num
    if price <= 0:
        msg = f"物品：{goods_name}炼金失败，凝聚{price}枚灵石，记得通知晓楠！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_lianjin.finish()

    sql_message.update_back_j(user_id, goods_id, num=num)
    sql_message.update_ls(user_id, price, 1)
    msg = f"物品：{goods_name} 数量：{num} 炼金成功，凝聚{price}枚灵石！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await daily_lianjin.finish()


@daily_xianyuan.handle(parameterless=[Cooldown(at_sender=False)])
async def daily_xianyuan_(bot: Bot, event: GroupMessageEvent, msg=None):
    """仙途奇缘"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    isUser, user_info, _ = check_user(event)
    user_msg = sql_message.get_user_info_with_id(user_id)
    user_root = user_msg['root_type']
    sect = user_info['sect_id']
    level = user_info['level']
    list_level_all = list(jsondata.level_data().keys())

    now_time = datetime.now()
    create_time_str = user_info['create_time'].strftime("%Y-%m-%d %H:%M:%S.%f")
    create_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S.%f")
    diff_time = now_time - create_time
    diff_days = diff_time.days  # 距离创建账号时间的天数

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_xianyuan.finish()

    sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    if sect != None and user_root == "伪灵根":
        msg = f"道友已有宗门庇佑，又何必来此寻求机缘呢？"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    elif user_root in {"轮回道果", "真·轮回道果"}:
        msg = f"道友已是轮回大能，又何必来此寻求机缘呢？"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    elif list_level_all.index(level) >= list_level_all.index(XiuConfig().beg_max_level):
        msg = f"道友已跻身于{user_info['level']}层次的修行之人，可徜徉于四海八荒，自寻机缘与造化矣。"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    elif diff_days > XiuConfig().beg_max_days:
        msg = f"道友已经过了新手期,不能再来此寻求机缘了。"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    else:
        stone = sql_message.get_beg(user_id)
        if stone is None:
            msg = '贪心的人是不会有好运的！'
        else:
            msg = random.choice(
                [
                    f"在一次深入古老森林的修炼旅程中，你意外地遇到了一位神秘的前辈高人。这位前辈不仅给予了你宝贵的修炼指导，还在临别时赠予了你 {stone} 枚灵石，以表达对你的认可和鼓励。",
                    f"某日，在一个清澈的小溪边，一只珍稀的灵兽突然出现在你面前。它似乎对你的气息感到亲切，竟然留下了 {stone} 枚灵石，好像是在对你展示它的友好和感激。",
                    f"在一次勇敢的探险中，你发现了一片被遗忘的灵石矿脉。通过采矿获得了 {stone} 枚灵石，这不仅是一次意外的惊喜，也是对你勇气和坚持的奖赏。",
                    f"在一个宁静的夜晚，你抬头夜观星象，突然一颗流星划破夜空，落在你的附近。你跟随流星落下的轨迹找到了 {stone} 枚灵石，就像是来自天际的礼物。",
                    f"在一次偶然的机会下，你在一座古老的山洞深处发现了一块充满灵气的巨大灵石，将它收入囊中并获得了 {stone} 枚灵石。这块灵石似乎蕴含着古老的力量，让你的修为有了不小的提升。",
                    f"在一次探索未知禁地时，你解开了一个古老的阵法，这个阵法守护着数世纪的秘密。当最后一个符文点亮时，阵法缓缓散开，露出了其中藏有的 {stone} 枚灵石。",
                    f"在一次河床淘金的经历中，你意外发现了一些隐藏在水流淤泥中的 {stone} 枚灵石。这些灵石对于修炼者来说极为珍贵，而你却在这样一个不经意的时刻发现了它们。这次发现让你更加相信，修炼之路上的每一次机缘都是命运的安排，值得你去珍惜和感激",
                    f"在一次偶然的机会下，你在一座古墓的深处发现了一个隐藏的宝藏，其中藏有 {stone} 枚灵石。这些灵石可能是古时某位大能为后人留下的财富，而你，正是那位幸运的发现者。这次发现不仅大大增加了你的修为，也让你对探索古墓和古老传说充满了无尽的好奇和兴趣。",
                    f"参加门派举办的比武大会，你凭借着出色的实力和智慧，一路过关斩将，但在最终对决中惜败萧炎。虽败犹荣，作为奖励，门派赠予了你 {stone} 枚灵石，这不仅是对你实力的认可，也是对你未来修炼的支持。",
                    f"在一次对古老遗迹的探索中，你解开了一道埋藏已久的谜题。随着最后一个谜题的解开，一个密室缓缓打开，里面藏有的 {stone} 枚灵石作为奖励呈现在你面前。这些灵石对你来说，不仅是物质上的奖励，更是对你智慧和毅力的肯定。",
                    f"修炼时，你意外地遇到了一次天降祥瑞的奇观，一朵灵花从天而降，化作了 {stone} 枚灵石落入你的背包中。这次祥瑞不仅让你的修为有了不小的提升，也让你深感天地之大，自己仍需不断努力，探索修炼的更高境界。",
                    f"在一次门派分配的任务中，你表现出色，解决了一个困扰门派多时的难题。作为对你贡献的认可，门派特别奖励了你 {stone} 枚灵石。",
                    f"一位神秘旅行者传授给你一张古老的地图，据说地图上标记的宝藏正是数量可观的灵石。经过一番冒险和探索，你终于找到了宝藏所在，获得了 {stone} 枚灵石!",
                    f"在你帮助一位受伤的异兽后，作为感谢，它送给了你 {stone} 枚灵石。随后踏云而去，修炼之路上的每一个生命都值得尊重和帮助，而善行和仁心，往往能收获意想不到的回报。",
                    f"在一次与妖兽的激战中胜出后，你发现了妖兽巢穴中藏有的 {stone} 枚灵石。这些灵石对你的修炼大有裨益，也让你对面对挑战时的勇气和决心有了更深的理解。",
                    f"你在一次随机的交易中获得了一个外表不起眼的神秘盒子。当你好奇心驱使下打开它时，发现里面竟是一枚装满灵石的纳戒，收获了 {stone} 枚灵石！",
                ]
            )
        await bot.send_group_msg(group_id=event.group_id, message=msg)


@daily_qiandao.handle(parameterless=[Cooldown(at_sender=False)])
async def daily_qiandao_(bot: Bot, event: GroupMessageEvent):
    """修仙签到"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_qiandao.finish()
    user_id = user_info['user_id']
    result = sql_message.get_sign(user_id)
    msg = result
    try:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await daily_qiandao.finish()
    except ActionFailed:
        await daily_qiandao.finish("修仙界网络堵塞，发送失败!", reply_message=True)
