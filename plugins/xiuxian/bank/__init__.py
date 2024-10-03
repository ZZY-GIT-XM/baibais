from datetime import datetime
from typing import Any, Tuple

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GROUP,
)
from nonebot.params import RegexGroup

from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.utils import check_user
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage

sql_message = XiuxianDateManage()  # 数据管理类实例

# 定义灵庄命令处理器
bank = on_regex(
    r'^灵庄(存灵石|取灵石|升级会员|信息|结算)?(.*)?',
    priority=9,
    permission=GROUP,
    block=True
)


@bank.handle(parameterless=[Cooldown(at_sender=False)])
async def bank_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    """处理灵庄命令"""
    # 分配机器人和群组ID
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    # 检查用户是否已注册
    isUser, user_info, msg = check_user(event)
    if not isUser:
        # 如果用户未注册，则发送提示消息
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await bank.finish()

    # 解析命令模式和数值
    mode, num = args

    # 获取用户的灵庄信息
    user_id = user_info['user_id']
    bankinfo = sql_message.get_bank_info(user_id)
    if not bankinfo:
        sql_message.insert_bank_info(user_id)
        bankinfo = sql_message.get_bank_info(user_id)

    # 根据不同的模式执行相应的操作
    if mode == '存灵石':
        # 存灵石逻辑
        await deposit_stone(bot, send_group_id, user_info, user_id, num)
    elif mode == '取灵石':
        # 取灵石逻辑
        await withdraw_stone(bot, send_group_id, user_info, user_id, num)
    elif mode == '升级会员':
        # 升级会员逻辑
        await upgrade_membership(bot, send_group_id, user_info, user_id)
    elif mode == '信息':
        # 查询灵庄信息
        await show_bank_info(bot, send_group_id, user_info, user_id)
    elif mode == '结算':
        # 结算利息
        await settle_interest(bot, send_group_id, user_info, user_id)


async def deposit_stone(bot, send_group_id, user_info, user_id, num):
    """存灵石逻辑"""
    try:
        num = int(num)
        if num <= 0:
            raise ValueError("金额必须大于零")

        # 检查用户是否有足够的灵石
        if int(user_info['stone']) < num:
            await send_message(bot, send_group_id, f"道友所拥有的灵石为{user_info['stone']}枚，金额不足，请重新输入！")
            await bank.finish()

        # 获取灵庄信息
        bankinfo = sql_message.get_bank_info(user_id)
        if not bankinfo:
            sql_message.insert_bank_info(user_id)
            bankinfo = sql_message.get_bank_info(user_id)

        # 获取当前等级信息
        current_level_info = sql_message.get_bank_level(bankinfo['banklevel'])

        # 检查是否超过最大存储量
        max_storage = current_level_info['save_max']
        available_storage = max_storage - bankinfo['savestone']
        if num > available_storage:
            await send_message(bot, send_group_id,
                               f'''{user_info['user_name']} 道友
当前灵庄会员等级为{current_level_info['level_name']}
可存储的最大灵石为{max_storage}枚
当前已存{bankinfo['savestone']}枚灵石
可以继续存{available_storage}枚灵石''')
            await bank.finish()

        # 计算利息
        bankinfo, give_stone, timedeff = get_give_stone(bankinfo, current_level_info['interest_rate'])

        # 更新灵庄信息和用户灵石数量
        sql_message.update_bank_info(user_id, savestone=bankinfo['savestone'] + num, savetime=datetime.now(),
                                     banklevel=bankinfo['banklevel'])
        sql_message.update_ls(user_id, num, 2)  # 减少用户灵石
        sql_message.update_ls(user_id, give_stone, 1)  # 增加用户灵石

        # 发送结果消息
        await send_message(bot, send_group_id,
                           f'''{user_info['user_name']} 道友
本次结息时间为：{timedeff}小时
获得灵石：{give_stone}枚
道友存入灵石{num}枚
当前所拥有灵石{int(user_info['stone']) + give_stone}枚
灵庄存有灵石{bankinfo['savestone'] + num}枚''')
        await bank.finish()
    except ValueError:
        await send_message(bot, send_group_id, f"请输入正确的金额")
        await bank.finish()


async def withdraw_stone(bot, send_group_id, user_info, user_id, num):
    """取灵石逻辑"""
    try:
        num = int(num)
        if num <= 0:
            raise ValueError("金额必须大于零")

        # 获取灵庄信息
        bankinfo = sql_message.get_bank_info(user_id)
        if not bankinfo:
            sql_message.insert_bank_info(user_id)
            bankinfo = sql_message.get_bank_info(user_id)

        # 检查是否有足够的灵石在灵庄
        if int(bankinfo['savestone']) < num:
            await send_message(bot, send_group_id,
                               f"{user_info['user_name']} 道友当前灵庄所存有的灵石为{bankinfo['savestone']}枚，金额不足，请重新输入！")
            await bank.finish()

        # 获取当前等级信息
        current_level_info = sql_message.get_bank_level(bankinfo['banklevel'])

        # 结算利息
        bankinfo, give_stone, timedeff = get_give_stone(bankinfo, current_level_info['interest_rate'])

        # 更新用户灵石数量和灵庄信息
        sql_message.update_bank_info(user_id, savestone=bankinfo['savestone'] - num, savetime=datetime.now(),
                                     banklevel=bankinfo['banklevel'])
        sql_message.update_ls(user_id, num + give_stone, 1)

        # 发送结果消息
        await send_message(bot, send_group_id,
                           f'''{user_info['user_name']} 道友
本次结息时间为：{timedeff}小时
获得灵石：{give_stone}枚
取出灵石{num}枚
当前所拥有灵石{int(user_info['stone']) + give_stone}枚
灵庄存有灵石{bankinfo['savestone'] - num}枚''')
        await bank.finish()
    except ValueError as e:
        await send_message(bot, send_group_id, f"请输入正确的金额！{str(e)}")
        await bank.finish()


async def upgrade_membership(bot, send_group_id, user_info, user_id):
    """升级会员逻辑"""
    # 获取用户当前的灵庄信息
    bankinfo = sql_message.get_bank_info(user_id)
    if not bankinfo:
        # 如果没有灵庄信息，插入默认信息
        sql_message.insert_bank_info(user_id)
        bankinfo = sql_message.get_bank_info(user_id)

    # 获取用户当前的等级信息
    userlevel = bankinfo['banklevel']
    current_level_info = sql_message.get_bank_level(userlevel)

    # 检查是否已经是最高级别
    max_level_info = sql_message.get_max_bank_level()
    if userlevel == max_level_info['level']:
        await send_message(bot, send_group_id, f"{user_info['user_name']} 道友已经是最高级别的会员！")
        await bank.finish()

    # 检查是否有足够的灵石进行升级
    stonecost = current_level_info['level_up_cost']
    if int(user_info['stone']) < stonecost:
        await send_message(bot, send_group_id,
                           f"{user_info['user_name']} 道友所拥有的灵石为{user_info['stone']}枚，当前升级等级需求灵石{stonecost}枚金额不足，请重新输入！")
        await bank.finish()

    # 执行升级操作
    sql_message.update_ls(user_id, stonecost, 2)  # 减少用户灵石
    new_level = int(userlevel) + 1
    sql_message.update_bank_info(user_id, banklevel=str(new_level))

    # 获取新的等级信息
    new_level_info = sql_message.get_bank_level(new_level)

    # 发送升级结果消息
    await send_message(bot, send_group_id,
                       f"{user_info['user_name']} 道友成功升级灵庄等级，消耗灵石{stonecost}枚，当前为：{new_level_info['level_name']}，灵庄可存有灵石上限{new_level_info['save_max']}枚")
    await bank.finish()


async def show_bank_info(bot, send_group_id, user_info, user_id):
    """显示灵庄信息"""
    # 获取灵庄信息
    bankinfo = sql_message.get_bank_info(user_id)
    if not bankinfo:
        sql_message.insert_bank_info(user_id)
        bankinfo = sql_message.get_bank_info(user_id)

    # 获取当前等级信息
    try:
        level = int(bankinfo['banklevel'])
        current_level_info = sql_message.get_bank_level(level)
    except ValueError as e:
        print(f"Error converting banklevel to integer: {e}")
        current_level_info = None

    if current_level_info is None:
        # 如果没有找到对应的等级信息，返回默认值
        current_level_info = {
            'level_name': f'未知会员等级',
            'save_max': 0,
            'level_up_cost': 0,
            'interest_rate': 0
        }
    formatted_savetime = bankinfo['savetime'].strftime('%Y-%m-%d %H:%M:%S')

    msg = f'''{user_info['user_name']} 道友的灵庄信息：
已存：{bankinfo['savestone']}灵石
存入时间：{formatted_savetime}
灵庄会员等级：{current_level_info['level_name']}
当前拥有灵石：{user_info['stone']}
当前等级存储灵石上限：{current_level_info['save_max']}枚
'''
    await send_message(bot, send_group_id, msg)
    await bank.finish()


async def settle_interest(bot, send_group_id, user_info, user_id):
    """结算利息"""
    bankinfo = sql_message.get_bank_info(user_id)
    if not bankinfo:
        sql_message.insert_bank_info(user_id)
        bankinfo = sql_message.get_bank_info(user_id)

    # 获取当前等级信息
    current_level_info = sql_message.get_bank_level(bankinfo['banklevel'])

    # 计算利息
    bankinfo, give_stone, timedeff = get_give_stone(bankinfo, current_level_info['interest_rate'])

    # 更新灵庄信息
    sql_message.update_bank_info(user_id, savetime=datetime.now(), banklevel=bankinfo['banklevel'])

    # 发送结算结果消息
    await send_message(bot, send_group_id,
                       f"{user_info['user_name']} 道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚！")
    await bank.finish()


def get_give_stone(bankinfo, interest_rate):
    """计算并返回利息和更新后的灵庄信息"""
    savetime = bankinfo['savetime'].strftime('%Y-%m-%d %H:%M:%S')  # 存款时间转换成字符串
    nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S') -
                      datetime.strptime(savetime, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)
    savestone_float = float(bankinfo['savestone'])
    interest_rate_float = float(interest_rate)
    give_stone = int(savestone_float * timedeff * interest_rate_float)
    # 更新灵庄信息中的存入时间
    bankinfo['savetime'] = datetime.now()
    return bankinfo, give_stone, timedeff


async def send_message(bot, group_id, message):
    """发送消息到指定群组"""
    await bot.send_group_msg(group_id=int(group_id), message=message)
