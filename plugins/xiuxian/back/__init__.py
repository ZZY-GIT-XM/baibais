import re
import json
import base64
import random
import asyncio
from datetime import datetime
from decimal import Decimal

from nonebot.typing import T_State

from ..xiuxian_back import get_item_msg_rank, check_equipment_can_use, get_use_equipment_sql, check_use_elixir, \
    get_use_jlq_msg, get_no_use_equipment_sql, get_user_main_back_msg, get_user_skill_back_msg
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

back_shiyong = on_command("使用", priority=15, permission=GROUP, block=True)
back_xiezai_zhuangbei = on_command("换装", priority=5, permission=GROUP, block=True)
back_main = on_command('我的背包', aliases={'我的物品'}, priority=10, permission=GROUP, block=True)


@back_main.handle(parameterless=[Cooldown(cd_time=10, at_sender=False)])
async def back_main_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """我的背包
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_main.finish()

    user_id = user_info['user_id']

    # 检查背包是否为空
    msg = get_user_main_back_msg(user_id)
    if not msg:
        await bot.send_group_msg(group_id=int(send_group_id), message="您的背包为空！")
        await back_main.finish()

    # 尝试获取页码
    try:
        page = int(args.extract_plain_text().strip())
    except ValueError:
        page = 1  # 如果没有提供页码或格式不正确，默认为第一页

    # 定义分页大小
    PAGE_SIZE = 100
    skill_msg = get_user_skill_back_msg(user_id)
    # 将药材背包数据转化为列表，便于分页
    data_list = [item for item in msg] + skill_msg

    # 计算总页数
    total_items = len(data_list)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整

    # 检查当前页码是否有效
    if page < 1 or page > total_pages:
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"无效的页码。请输入有效的页码范围：1-{total_pages}")
        await back_main.finish()

    # 获取当前页的数据
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_items)
    page_data = data_list[start_idx:end_idx]

    # 合并所有消息为一个字符串
    header = f"{user_info['user_name']}的背包，持有灵石：{number_to(user_info['stone'])}枚\n"
    full_msg = header + "\n".join(page_data)

    # 添加翻页提示
    full_msg += f"\n\n第 {page}/{total_pages} 页\n使用命令 '我的背包 {page + 1}' 查看下一页" if page < total_pages else "\n\n这是最后一页。"

    try:
        # 将所有消息作为一条消息发送
        await bot.send_group_msg(group_id=int(send_group_id), message=full_msg)
    except ActionFailed:
        await back_main.finish("查看背包失败!", reply_message=True)
    await back_main.finish()

@back_xiezai_zhuangbei.handle(parameterless=[Cooldown(at_sender=False)])
async def back_xiezai_zhuangbei_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """卸载物品（只支持装备）
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_xiezai_zhuangbei.finish()
    user_id = user_info['user_id']
    arg = args.extract_plain_text().strip()

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息, list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_xiezai_zhuangbei.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    for back in back_msg:
        if arg == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            break
    if not in_flag:
        msg = f"请检查道具 {arg} 是否在背包内！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_xiezai_zhuangbei.finish()

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            sql_str, item_type = get_no_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, 0)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, 0)
            msg = f"成功卸载装备{arg}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await back_xiezai_zhuangbei.finish()
        else:
            msg = "装备没有被使用，无法卸载！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await back_xiezai_zhuangbei.finish()
    else:
        msg = "目前只支持卸载装备！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_xiezai_zhuangbei.finish()


@back_shiyong.handle(parameterless=[Cooldown(at_sender=False)])
async def back_shiyong_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """使用物品
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
    user_id = user_info['user_id']
    args = args.extract_plain_text().split()
    arg = args[0]  #
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,dict
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_num = None
    for back in back_msg:
        if arg == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_num = back['goods_num']
            break
    if not in_flag:
        msg = f"请检查该道具 {arg} 是否在背包内！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            msg = "该装备已被装备，请勿重复装备！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await back_shiyong.finish()
        else:  # 可以装备
            sql_str, item_type = get_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, goods_id)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, goods_id)
            msg = f"成功装备{arg}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await back_shiyong.finish()
    elif goods_type == "技能":
        user_buff_info = UserBuffDate(user_id).buffinfo
        skill_info = items.get_data_by_item_id(goods_id)
        skill_type = skill_info['item_type']
        if skill_type == "神通":
            if int(user_buff_info['sec_buff']) == int(goods_id):
                msg = f"道友已学会该神通：{skill_info['name']}，请勿重复学习！"
            else:  # 学习sql
                sql_message.update_back_j(user_id, goods_id)
                sql_message.updata_user_sec_buff(user_id, goods_id)
                msg = f"恭喜道友学会神通：{skill_info['name']}！"
        elif skill_type == "功法":
            if int(user_buff_info['main_buff']) == int(goods_id):
                msg = f"道友已学会该功法：{skill_info['name']}，请勿重复学习！"
            else:  # 学习sql
                sql_message.update_back_j(user_id, goods_id)
                sql_message.updata_user_main_buff(user_id, goods_id)
                msg = f"恭喜道友学会功法：{skill_info['name']}！"
        elif skill_type == "辅修功法":  # 辅修功法1
            if int(user_buff_info['sub_buff']) == int(goods_id):
                msg = f"道友已学会该辅修功法：{skill_info['name']}，请勿重复学习！"
            else:  # 学习sql
                sql_message.update_back_j(user_id, goods_id)
                sql_message.updata_user_sub_buff(user_id, goods_id)
                msg = f"恭喜道友学会辅修功法：{skill_info['name']}！"
        else:
            msg = "发生未知错误！"

        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
    elif goods_type == "丹药":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await back_shiyong.finish()
        except ValueError:
            num = 1
        msg = check_use_elixir(user_id, goods_id, num)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
    elif goods_type == "神物":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await back_shiyong.finish()
        except ValueError:
            num = 1
        goods_info = items.get_data_by_item_id(goods_id)
        user_info = sql_message.get_user_info_with_id(user_id)
        user_rank = Items().convert_rank(user_info['level'])[0]
        goods_rank = goods_info['rank']
        goods_name = goods_info['name']
        if goods_rank < user_rank:  # 使用限制
            msg = f"神物：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            exp = goods_info['buff'] * num
            user_hp = int(user_info['hp'] + (exp / 2))
            user_mp = int(user_info['mp'] + exp)
            user_atk = int(user_info['atk'] + (exp / 10))
            sql_message.update_exp(user_id, exp)
            sql_message.update_power2(user_id)  # 更新战力
            sql_message.update_user_attribute(user_id, user_hp, user_mp, user_atk)  # 这种事情要放在update_exp方法里
            sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
            msg = f"道友成功使用神物：{goods_name} {num}个 ,修为增加{exp}点！"

        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()

    elif goods_type == "礼包":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await back_shiyong.finish()
        except ValueError:
            num = 1
        goods_info = items.get_data_by_item_id(goods_id)
        user_info = sql_message.get_user_info_with_id(user_id)
        user_rank = Items().convert_rank(user_info['level'])[0]
        goods_name = goods_info['name']
        goods_id1 = goods_info['buff_1']
        goods_id2 = goods_info['buff_2']
        goods_id3 = goods_info['buff_3']
        goods_name1 = goods_info['name_1']
        goods_name2 = goods_info['name_2']
        goods_name3 = goods_info['name_3']
        goods_type1 = goods_info['type_1']
        goods_type2 = goods_info['type_2']
        goods_type3 = goods_info['type_3']

        sql_message.send_back(user_id, goods_id1, goods_name1, goods_type1, 1 * num, 1)  # 增加用户道具
        sql_message.send_back(user_id, goods_id2, goods_name2, goods_type2, 2 * num, 1)
        sql_message.send_back(user_id, goods_id3, goods_name3, goods_type3, 2 * num, 1)
        sql_message.update_back_j(user_id, goods_id, num, 0)
        msg = f"道友打开了{num}个{goods_name},里面居然是{goods_name1}{int(1 * num)}个、{goods_name2}{int(2 * num)}个、{goods_name3}{int(2 * num)}个"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
    elif goods_type == "聚灵旗":
        msg = get_use_jlq_msg(user_id, goods_id)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
    else:
        msg = '该类型物品调试中，未开启！'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await back_shiyong.finish()
