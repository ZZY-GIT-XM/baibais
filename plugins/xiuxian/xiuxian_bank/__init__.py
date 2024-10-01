import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Tuple

from nonebot import on_regex
from nonebot.log import logger
from nonebot.params import RegexGroup
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GROUP,
    MessageSegment,
)
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage
from .bankconfig import get_config
from ..xiuxian_utils.utils import check_user, get_msg_pic
from ..xiuxian_config import XiuConfig

# 加载配置
config = get_config()
BANKLEVEL = config["BANKLEVEL"]
sql_message = XiuxianDateManage()  # 数据管理类实例
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"

# 定义银行命令处理器
bank = on_regex(
    r'^灵庄(存灵石|取灵石|升级会员|信息|结算)?(.*)?',
    priority=9,
    permission=GROUP,
    block=True
)

# 处理银行命令
@bank.handle(parameterless=[Cooldown(at_sender=False)])
async def bank_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    # 分配机器人和群组ID
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    # 检查用户是否已注册
    isUser, user_info, msg = check_user(event)
    if not isUser:
        # 如果用户未注册，则发送提示消息
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await bank.finish()

    # 解析命令模式和数值
    mode, num = args

    # 获取用户的银行信息
    user_id = user_info['user_id']
    try:
        bankinfo = readf(user_id)
    except Exception as e:
        logger.error(f"读取用户 {user_id} 的银行信息失败: {e}")
        bankinfo = {
            'savestone': 0,
            'savetime': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'banklevel': '1',
        }

    # 根据不同的模式执行相应的操作
    if mode == '存灵石':
        # 存灵石逻辑
        await deposit_stone(bot, send_group_id, user_info, bankinfo, num, user_id)
    elif mode == '取灵石':
        # 取灵石逻辑
        await withdraw_stone(bot, send_group_id, user_info, bankinfo, num, user_id)
    elif mode == '升级会员':
        # 升级会员逻辑
        await upgrade_membership(bot, send_group_id, user_info, bankinfo, user_id)
    elif mode == '信息':
        # 查询灵庄信息
        await show_bank_info(bot, send_group_id, user_info, bankinfo)
    elif mode == '结算':
        # 结算利息
        await settle_interest(bot, send_group_id, user_info, bankinfo, user_id)


# 存灵石逻辑
async def deposit_stone(bot, send_group_id, user_info, bankinfo, num, user_id):
    try:
        num = int(num)
        if num <= 0:
            raise ValueError("金额必须大于零")

        # 检查用户是否有足够的灵石
        if int(user_info['stone']) < num:
            await send_message(bot, send_group_id, f"道友所拥有的灵石为{user_info['stone']}枚，金额不足，请重新输入！")
            await bank.finish()

        # 扩展 BANKLEVEL
        extended_bank_level = extend_bank_level(user_info['poxian_num'])

        # 检查是否超过最大存储量
        max_storage = extended_bank_level[str(bankinfo['banklevel'])]['savemax']
        available_storage = max_storage - bankinfo['savestone']
        if num > available_storage:
            await send_message(bot, send_group_id,
                            f"{user_info['user_name']} 道友当前灵庄会员等级为{extended_bank_level[str(bankinfo['banklevel'])]['level']}，可存储的最大灵石为{max_storage}枚, 当前已存{bankinfo['savestone']}枚灵石，可以继续存{available_storage}枚灵石！")
            await bank.finish()

        # 更新银行信息和用户灵石数量
        bankinfo, give_stone, timedeff = get_give_stone(bankinfo)
        userinfonowstone = int(user_info['stone']) - num
        bankinfo['savestone'] += num
        sql_message.update_ls(user_id, num, 2)
        sql_message.update_ls(user_id, give_stone, 1)
        bankinfo['savetime'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        savef(user_id, bankinfo)

        # 发送结果消息
        await send_message(bot, send_group_id,
                        f"{user_info['user_name']} 道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚!\n道友存入灵石{num}枚，当前所拥有灵石{userinfonowstone + give_stone}枚，灵庄存有灵石{bankinfo['savestone']}枚")
        await bank.finish()
    except ValueError as e:
        await send_message(bot, send_group_id, f"请输入正确的金额！{str(e)}")
        await bank.finish()



# 取灵石逻辑
async def withdraw_stone(bot, send_group_id, user_info, bankinfo, num, user_id):
    try:
        num = int(num)
        if num <= 0:
            raise ValueError("金额必须大于零")

        # 检查是否有足够的灵石在银行
        if int(bankinfo['savestone']) < num:
            await send_message(bot, send_group_id,
                            f"{user_info['user_name']} 道友当前灵庄所存有的灵石为{bankinfo['savestone']}枚，金额不足，请重新输入！")
            await bank.finish()

        # 扩展 BANKLEVEL
        extended_bank_level = extend_bank_level(user_info['poxian_num'])

        # 结算利息
        bankinfo, give_stone, timedeff = get_give_stone(bankinfo)

        # 更新用户灵石数量和银行信息
        userinfonowstone = int(user_info['stone']) + num + give_stone
        bankinfo['savestone'] -= num
        sql_message.update_ls(user_id, num + give_stone, 1)
        savef(user_id, bankinfo)

        # 发送结果消息
        await send_message(bot, send_group_id,
                        f"{user_info['user_name']} 道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚!\n取出灵石{num}枚，当前所拥有灵石{userinfonowstone}枚，灵庄存有灵石{bankinfo['savestone']}枚!")
        await bank.finish()
    except ValueError as e:
        await send_message(bot, send_group_id, f"请输入正确的金额！{str(e)}")
        await bank.finish()



# 升级会员逻辑
async def upgrade_membership(bot, send_group_id, user_info, bankinfo, user_id):
    userlevel = bankinfo["banklevel"]
    user_poxian = user_info['poxian_num']  # 获取用户破限次数

    # 动态扩展 BANKLEVEL
    extend_bank_level(user_poxian)

    # 新增限制：破限次数为 n 时，只能升级到破限会员+n
    max_user_level = 7 + user_poxian  # 最大允许等级

    # 发送升级结果消息
    level_title = "会员"
    if user_poxian > 0:
        level_title = "贵宾"

    # 先检查是否已经破限前是最大会员
    if userlevel == str(len(BANKLEVEL)):
        if user_poxian == 0:
            await send_message(bot, send_group_id,
                            f"{user_info['user_name']} 道友已经是本灵庄最大的会员啦！破限后可升级为贵宾!")
        else:
            await send_message(bot, send_group_id,
                            f"{user_info['user_name']} 道友已经是破限贵宾+{user_poxian}啦！再次升级需要破限次数为{user_poxian + 1}")
        await bank.finish()

    # 检查是否已经达到破限会员+n
    if int(userlevel) >= max_user_level:
        if user_poxian == 0:
            await send_message(bot, send_group_id,
                            f"{user_info['user_name']} 道友已经是本灵庄最大的会员啦！破限后可升级为贵宾!")
        else:
            await send_message(bot, send_group_id,
                            f"{user_info['user_name']} 道友已经是破限贵宾+{user_poxian}啦！再次升级需要破限次数为{user_poxian + 1}")
        await bank.finish()

    # 检查是否有足够的灵石进行升级
    stonecost = BANKLEVEL[f"{int(userlevel)}"]['levelup']
    if int(user_info['stone']) < stonecost:
        await send_message(bot, send_group_id,
                        f"{user_info['user_name']} 道友所拥有的灵石为{user_info['stone']}枚，当前升级{level_title}等级需求灵石{stonecost}枚金额不足，请重新输入！")
        await bank.finish()

    # 执行升级操作
    sql_message.update_ls(user_id, stonecost, 2)
    # 确保不会超过最大允许等级
    bankinfo['banklevel'] = f"{min(int(userlevel) + 1, max_user_level)}"
    savef(user_id, bankinfo)

    await send_message(bot, send_group_id,
                    f"{user_info['user_name']} 道友成功升级灵庄{level_title}等级，消耗灵石{stonecost}枚，当前为：{BANKLEVEL[bankinfo['banklevel']]['level']}，灵庄可存有灵石上限{BANKLEVEL[bankinfo['banklevel']]['savemax']}枚")
    await bank.finish()


def extend_bank_level(user_poxian, bank_level_dict=BANKLEVEL):
    # 扩展 BANKLEVEL
    max_level = len(bank_level_dict)
    if isinstance(user_poxian, Decimal):
        user_poxian_int = int(user_poxian)
    else:
        user_poxian_int = int(user_poxian)
    if user_poxian_int > 0:
        for i in range(max_level + 1, max_level + 1 + user_poxian_int):
            prev_level = i - 1
            bank_level_dict[str(i)] = {
                "savemax": bank_level_dict[str(prev_level)]["savemax"] * 2,
                "levelup": bank_level_dict[str(prev_level)]["levelup"] * 2,
                "interest": bank_level_dict[str(prev_level)]["interest"] + 0.0002,
                "level": f"破限贵宾+{i - 7}"
            }
    return bank_level_dict


# 显示银行信息
async def show_bank_info(bot, send_group_id, user_info, bankinfo):
    # 扩展 BANKLEVEL
    extended_bank_level = extend_bank_level(user_info['poxian_num'])

    msg = f'''{user_info['user_name']} 道友的灵庄信息：
已存：{bankinfo['savestone']}灵石
存入时间：{bankinfo['savetime']}
灵庄会员等级：{extended_bank_level[str(bankinfo['banklevel'])]['level']}
当前拥有灵石：{user_info['stone']}
当前等级存储灵石上限：{extended_bank_level[str(bankinfo['banklevel'])]['savemax']}枚
'''
    await send_message(bot, send_group_id, msg)
    await bank.finish()



# 结算利息
async def settle_interest(bot, send_group_id, user_info, bankinfo, user_id):
    bankinfo, give_stone, timedeff = get_give_stone(bankinfo)
    sql_message.update_ls(user_id, give_stone, 1)
    savef(user_id, bankinfo)

    # 发送结算结果消息
    await send_message(bot, send_group_id,
                    f"{user_info['user_name']} 道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚！")
    await bank.finish()


# 获取利息
def get_give_stone(bankinfo):
    """计算并返回利息和更新后的银行信息"""
    savetime = bankinfo['savetime']  # 存款时间
    nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S') -
                      datetime.strptime(savetime, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)
    give_stone = int(bankinfo['savestone'] * timedeff * BANKLEVEL[bankinfo['banklevel']]['interest'])
    bankinfo['savetime'] = nowtime

    return bankinfo, give_stone, timedeff


# 读取用户银行文件
def readf(user_id):
    """读取用户的银行信息"""
    user_id = str(user_id)
    filepath = PLAYERSDATA / user_id / "bankinfo.json"
    with open(filepath, "r", encoding="UTF-8") as f:
        return json.load(f)


# 保存用户银行文件
def savef(user_id, data):
    """保存用户的银行信息到文件"""
    user_id = str(user_id)
    if not os.path.exists(PLAYERSDATA / user_id):
        logger.info(f"用户目录不存在，创建目录: {user_id}")
        os.makedirs(PLAYERSDATA / user_id)
    filepath = PLAYERSDATA / user_id / "bankinfo.json"
    data_json = json.dumps(data, ensure_ascii=False, indent=3)
    with open(filepath, "w", encoding="UTF-8") as f:
        f.write(data_json)
    return True


# 发送消息
async def send_message(bot, group_id, message):
    """发送消息到指定群组"""
    if XiuConfig().img:
        pic = await get_msg_pic(message)
        await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(group_id), message=message)
