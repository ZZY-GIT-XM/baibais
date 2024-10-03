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

sql_message = XiuxianDateManage()

kaiguan_xiuxian = on_command("启用修仙功能", aliases={'禁用修仙功能'},
                             permission=GROUP and (SUPERUSER or GROUP_ADMIN or GROUP_OWNER), priority=5, block=True)
kaiguan_paimai = on_command("群拍卖会", priority=4, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),
                            block=True)
kaiguan_boss = on_command("世界boss", aliases={"世界Boss", "世界BOSS"}, priority=13,
                            permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER), block=True)
kaiguan_mijing = on_command("群秘境", priority=4, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),
                            block=True)

@kaiguan_xiuxian.handle()
async def kaiguan_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """群修仙开关配置 启用/禁用修仙功能"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_msg = str(event.message)
    group_id = str(event.group_id)

    if "启用" in group_msg:
        if sql_message.is_xiuxian_enabled(group_id):
            msg = "当前群聊修仙模组已启用，请勿重复操作！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_xiuxian.finish()
        sql_message.enable_xiuxian(group_id)
        msg = "当前群聊修仙基础模组已启用，快发送 [我要修仙] 加入修仙世界吧！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await kaiguan_xiuxian.finish()

    elif "禁用" in group_msg:
        if not sql_message.is_xiuxian_enabled(group_id):
            msg = "当前群聊修仙模组已禁用，请勿重复操作！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_xiuxian.finish()
        sql_message.disable_xiuxian(group_id)
        msg = "当前群聊修仙基础模组已禁用！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await kaiguan_xiuxian.finish()
    else:
        msg = "指令错误，请输入：启用修仙功能/禁用修仙功能"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await kaiguan_xiuxian.finish()


@kaiguan_paimai.handle(parameterless=[Cooldown(at_sender=False)])
async def kaiguan_paimai_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """群拍卖会开关配置 启用/禁用群拍卖功能"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)

    if mode == '开启':
        if sql_message.is_auction_enabled(group_id):
            msg = "本群已开启群拍卖会，请勿重复开启!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_paimai.finish()
        else:
            sql_message.enable_auction(group_id)
            msg = "已开启群拍卖会"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_paimai.finish()

    elif mode == '关闭':
        if sql_message.is_auction_enabled(group_id):
            sql_message.disable_auction(group_id)
            msg = "已关闭本群拍卖会!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_paimai.finish()
        else:
            msg = "本群未开启群拍卖会!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_paimai.finish()


@kaiguan_boss.handle(parameterless=[Cooldown(at_sender=False)])
async def kaiguan_boss_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """群世界 Boss 功能开关配置 启用/禁用群世界 Boss 功能"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)

    if mode == '开启':
        if sql_message.is_boss_enabled(group_id):
            msg = "本群已开启世界 Boss 功能，请勿重复开启!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_boss.finish()
        else:
            sql_message.enable_boss(group_id)
            msg = "已开启世界 Boss 功能"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_boss.finish()

    elif mode == '关闭':
        if sql_message.is_boss_enabled(group_id):
            sql_message.disable_boss(group_id)
            msg = "已关闭本群世界 Boss 功能!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_boss.finish()
        else:
            msg = "本群未开启世界 Boss 功能!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_boss.finish()


@kaiguan_mijing.handle(parameterless=[Cooldown(at_sender=False)])
async def kaiguan_mijing_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """群秘境开启、关闭"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)

    if mode == '开启':
        if sql_message.is_mijing_enabled(group_id):
            msg = "本群秘境已开启，无需重复开启!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_mijing.finish()
        else:
            sql_message.enable_mijing(group_id)
            msg = "已开启本群秘境功能!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_mijing.finish()

    elif mode == '关闭':
        if sql_message.is_mijing_enabled(group_id):
            sql_message.disable_mijing(group_id)
            msg = "已关闭本群秘境功能!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_mijing.finish()
        else:
            msg = "本群秘境功能尚未开启!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await kaiguan_mijing.finish()

    else:
        msg = "请输入群秘境开启或关闭!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await kaiguan_mijing.finish()