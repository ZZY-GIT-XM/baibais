import re
import json
import base64
import random
import asyncio
from datetime import datetime
from decimal import Decimal

from nonebot.typing import T_State
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

# 定时任务
cache_help = {}
cache_level_help = {}
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()

list_rankking = on_command("排行榜",
                           aliases={"排行榜列表", "灵石排行榜", "战力排行榜", "境界排行榜", "宗门排行榜", "轮回排行榜"},
                           priority=7, permission=GROUP, block=True)
list_wupin = on_command("查看修仙界物品", priority=25, permission=GROUP, block=True)


@list_wupin.handle(parameterless=[Cooldown(at_sender=False)])
async def list_wupin_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看修仙界所有物品列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    args = args.extract_plain_text().strip()
    list_tp = []
    if args not in ["功法", "辅修功法", "神通", "丹药", "合成丹药", "法器", "防具"]:
        msg = "请输入正确类型【功法|辅修功法|神通|丹药|合成丹药|法器|防具】！！！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_wupin.finish()
    else:
        if args == "功法":
            gf_data = items.get_data_by_item_type(['功法'])
            for x in gf_data:
                name = gf_data[x]['name']
                rank = gf_data[x]['level']
                msg = f"※{rank}:{name}"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "辅修功法":
            gf_data = items.get_data_by_item_type(['辅修功法'])
            for x in gf_data:
                name = gf_data[x]['name']
                rank = gf_data[x]['level']
                msg = f"※{rank}:{name}"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "神通":
            st_data = items.get_data_by_item_type(['神通'])
            for x in st_data:
                name = st_data[x]['name']
                rank = st_data[x]['level']
                msg = f"※{rank}:{name}"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "丹药":
            dy_data = items.get_data_by_item_type(['丹药'])
            for x in dy_data:
                name = dy_data[x]['name']
                rank = dy_data[x]['境界']
                desc = dy_data[x]['desc']
                msg = f"※{rank}丹药:{name}，效果：{desc}\n"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "合成丹药":
            hcdy_data = items.get_data_by_item_type(['合成丹药'])
            for x in hcdy_data:
                name = hcdy_data[x]['name']
                rank = hcdy_data[x]['境界']
                desc = hcdy_data[x]['desc']
                msg = f"※{rank}丹药:{name}，效果：{desc}\n\n"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "法器":
            fq_data = items.get_data_by_item_type(['法器'])
            for x in fq_data:
                name = fq_data[x]['name']
                rank = fq_data[x]['level']
                msg = f"※{rank}:{name}"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "防具":
            fj_data = items.get_data_by_item_type(['防具'])
            for x in fj_data:
                name = fj_data[x]['name']
                rank = fj_data[x]['level']
                msg = f"※{rank}:{name}"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        try:
            await send_msg_handler(bot, event, list_tp)
        except ActionFailed:
            msg = "未知原因，查看失败!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_wupin.finish()


@list_rankking.handle(parameterless=[Cooldown(at_sender=False)])
async def list_rankking_(bot: Bot, event: GroupMessageEvent):
    """排行榜"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    message = str(event.message)
    rank_msg = r'[\u4e00-\u9fa5]+'
    message = re.findall(rank_msg, message)
    if message:
        message = message[0]

    if message in ["排行榜", "修仙排行榜", "境界排行榜", "修为排行榜"]:
        p_rank = sql_message.realm_top()
        msg = f"✨位面境界排行榜TOP50✨\n"
        num = 0
        for i in p_rank:
            num += 1
            msg += f"第{num}位 {i[0]} {i[1]}, 修为{number_to(i[2])}\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_rankking.finish()

    elif message == "灵石排行榜":
        a_rank = sql_message.stone_top()
        msg = f"✨位面灵石排行榜TOP50✨\n"
        num = 0
        for i in a_rank:
            num += 1
            msg += f"第{num}位  {i[0]}  灵石：{number_to(i[1])}枚\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_rankking.finish()

    elif message == "战力排行榜":
        c_rank = sql_message.power_top()
        msg = f"✨位面战力排行榜TOP50✨\n"
        num = 0
        for i in c_rank:
            num += 1
            msg += f"第{num}位  {i[0]}  战力：{number_to(i[1])}\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_rankking.finish()

    elif message == "轮回排行榜":
        c_rank = sql_message.poxian_top()
        msg = f"✨位面轮回排行榜TOP50✨\n"
        num = 0
        for i in c_rank:
            num += 1
            msg += f"第{num}位  {i[0]}  轮回：{i[1]}次\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_rankking.finish()

    elif message in ["宗门排行榜", "宗门建设度排行榜"]:
        s_rank = sql_message.scale_top()
        msg = f"✨位面宗门建设排行榜TOP50✨\n"
        num = 0
        for i in s_rank:
            num += 1
            msg += f"第{num}位  {i[1]}  建设度：{number_to(i[2])}\n"
            if num == 50:
                break
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await list_rankking.finish()
