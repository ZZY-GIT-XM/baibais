import re

from nonebot import on_command, on_fullmatch, on_regex
from nonebot.params import CommandArg, RegexGroup
from typing import Any, Tuple
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_utils.data_source import jsondata
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent,
    MessageSegment,
    Message
)
from ..xiuxian_utils.utils import (
    check_user, get_msg_pic,
    CommandObjectID
)

__warring_help__ = """
轮回重修帮助：
- 详情：
  - 散尽修为，轮回重修，将万世的道果凝聚为极致天赋。
  - 修为、功法、神通将被清空！
  - 进入千世轮回：获得轮回灵根，增加破限次数，破限10次可进入万世轮回，可定制极品仙器（在做）。
  - 进入万世轮回：获得真轮回灵根，可定制无上仙器（在做）。
  - 重入修仙：字面意思，仅搬血境可用。
- 使用方法：
  - 输入「进入千世轮回/进入万世轮回」开始轮回重修。
  - 输入「重入修仙」将重新开始。
  - 输入「轮回加点 查询」查看当前状态和剩余破限次数。
- 注意事项：
  - 轮回重修后，修为、功法、神通将被清空。
  - 千世轮回每次获得最终增幅10%(真元/血量/灵根/闭关收益/修炼收益)
  - 万世轮回每次获得最终增幅20%(真元/血量/灵根/闭关收益/修炼收益)
  - 重入修仙仅在搬血境可用。
""".strip()

__rebirth_help__ = """
轮回加点帮助：
- 使用方法：
  - 输入「轮回加点 属性名称 数字」分配轮回点数到特定属性。
    - 示例：「轮回加点 修炼 10」将10点轮回点数分配给修炼效率。
  - 属性名称对应如下：
    - 修炼：增加修炼效率（每点增加修炼效率1%）
    - 闭关：增加闭关效率（每点增加闭关效率1%）
    - 灵根：增加灵根效率（每点增加灵根效率1%）
    - 血量：增加血量上限（每点增加血量100000）
    - 真元：增加真元上限（每点增加真元100000）
    - 攻击：增加攻击上限（每点增加攻击10000）
  - 输入「轮回加点 重置」重置所有已分配的轮回点数。
  - 输入「轮回加点 查询」查看当前已分配的属性点数和剩余未分配的轮回点数。
- 注意事项：
  - 分配的点数不能超过当前拥有的轮回点数。
  - 重置会将所有已分配的点数返回到轮回点数池中。
  - 查询功能可以帮助你了解当前属性点数分配情况及剩余轮回点数。
  - 千世轮回每次可得20轮回点,万世轮回每次可得50轮回点。
""".strip()


cache_help_fk = {}
sql_message = XiuxianDateManage()  # sql类

warring_help = on_fullmatch("轮回重修帮助", priority=12, permission=GROUP, block=True)
lunhui = on_command('进入千世轮回', priority=15, permission=GROUP,block=True)
twolun = on_command('进入万世轮回', priority=15, permission=GROUP,block=True)
resetting = on_command('重入修仙', priority=15, permission=GROUP,block=True)
rebirth_help = on_command('轮回加点帮助', priority=15, permission=GROUP, block=True)
lunhui_jiadian = on_regex(r'^轮回加点\s*(.*?)\s*(\d*)$', flags=re.IGNORECASE, priority=15, permission=GROUP, block=True)


@warring_help.handle(parameterless=[Cooldown(at_sender=False)])
async def warring_help_(bot: Bot, event: GroupMessageEvent):
    """轮回重修帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __warring_help__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await warring_help.finish()


@rebirth_help.handle(parameterless=[Cooldown(at_sender=False)])
async def rebirth_help_(bot: Bot, event: GroupMessageEvent):
    """轮回加点帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __rebirth_help__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await rebirth_help.finish()


@lunhui.handle(parameterless=[Cooldown(at_sender=False)])
async def lunhui_(bot: Bot, event: GroupMessageEvent):
    """进入千世轮回"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui.finish()
        
    user_id = user_info['user_id']
    user_msg = sql_message.get_user_info_with_id(user_id) 
    user_name = user_msg['user_name']
    user_root = user_msg['root_type']
    user_poxian = user_msg['poxian_num']
    list_level_all = list(jsondata.level_data().keys())
    level = user_info['level']
    
    if user_root == '轮回道果' and user_poxian >= 10:
        msg = "道友已是千世轮回之身,且已破限10次及以上，请前往万世轮回！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui.finish()
    
    if user_root == '真·轮回道果' and user_poxian >= 10:
        msg = "道友需渡万世轮回！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui.finish()
        
    if list_level_all.index(level) >= list_level_all.index(XiuConfig().lunhui_min_level):
        # 获取当前用户的 type_speeds
        current_type_speeds = jsondata.root_data()[user_root]['type_speeds']

        # 获取“真·轮回道果”的 type_speeds
        zhen_twolun_speeds = jsondata.root_data()['轮回道果']['type_speeds']

        # 判断是否需要更换灵根
        if current_type_speeds < zhen_twolun_speeds:
            sql_message.update_root(user_id, 6)  # 更换轮回灵根为“轮回道果”
            new_root = '轮回道果'
        else:
            new_root = user_root  # 保持原灵根
        exp = user_msg['exp']
        now_exp = exp - 100
        sql_message.updata_level(user_id, '江湖好手') #重置用户境界
        sql_message.update_levelrate(user_id, 0) #重置突破成功率
        sql_message.update_stone(user_id, 0) #重置用户灵石
        sql_message.update_j_exp(user_id, now_exp) #重置用户修为
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        sql_message.updata_user_main_buff(user_id, 0) #重置用户主功法
        sql_message.updata_user_sub_buff(user_id, 0) #重置用户辅修功法
        sql_message.updata_user_sec_buff(user_id, 0) #重置用户神通
        sql_message.update_user_atkpractice(user_id, 0) #重置用户攻修等级
        sql_message.update_poxian_num(user_id) #更新用户打破极限的次数
        sql_message.add_rebirth_points(user_id,20) #获得轮回点数
        msg = f"千世轮回磨不灭，重回绝颠谁能敌，恭喜大能{user_name}轮回成功！当前破限次数为{user_poxian + 1}!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui.finish()
    else:
        msg = f"道友境界未达要求，进入千世轮回的最低境界为{XiuConfig().lunhui_min_level}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui.finish()


@twolun.handle(parameterless=[Cooldown(at_sender=False)])
async def twolun_(bot: Bot, event: GroupMessageEvent):
    """进入万世轮回"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await twolun.finish()
        
    user_id = user_info['user_id']
    user_msg = sql_message.get_user_info_with_id(user_id) 
    user_name = user_msg['user_name']
    user_root = user_msg['root_type']
    user_poxian = user_msg['poxian_num']
    list_level_all = list(jsondata.level_data().keys())
    level = user_info['level']
        
    if user_root != '轮回道果' and user_poxian < 10:
        msg = "道友还未渡过千世轮回，请先进入千世轮回！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await twolun.finish() 
    
    if list_level_all.index(level) >= list_level_all.index(XiuConfig().twolun_min_level) and user_poxian >= 10:
        # 获取当前用户的 type_speeds
        current_type_speeds = jsondata.root_data()[user_root]['type_speeds']

        # 获取“真·轮回道果”的 type_speeds
        zhen_twolun_speeds = jsondata.root_data()['真·轮回道果']['type_speeds']

        # 判断是否需要更换灵根
        if current_type_speeds < zhen_twolun_speeds:
            sql_message.update_root(user_id, 7)  # 更换轮回灵根为“真·轮回道果”
            new_root = '真·轮回道果'
        else:
            new_root = user_root  # 保持原灵根
        exp = user_msg['exp']
        now_exp = exp - 100
        sql_message.updata_level(user_id, '江湖好手') #重置用户境界
        sql_message.update_levelrate(user_id, 0) #重置突破成功率
        sql_message.update_stone(user_id, 0) #重置用户灵石
        sql_message.update_j_exp(user_id, now_exp) #重置用户修为
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        sql_message.update_poxian_num(user_id) #更新用户打破极限的次数
        sql_message.add_rebirth_points(user_id,50) #获得轮回点数
        msg = f"万世道果集一身，脱出凡道入仙道，恭喜大能{user_name}万世轮回成功！当前破限次数为{user_poxian + 1}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await twolun.finish()
    else:
        msg = f"道友境界未达要求，万世轮回的最低境界为{XiuConfig().twolun_min_level}，最低破限次数为10次！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await twolun.finish()


@resetting.handle(parameterless=[Cooldown(at_sender=False)])
async def resetting_(bot: Bot, event: GroupMessageEvent):
    """重入修仙"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await resetting.finish()
        
    user_id = user_info['user_id']
    user_msg = sql_message.get_user_info_with_id(user_id) 
    user_name = user_msg['user_name']
        
    if user_msg['level'] in ['搬血境初期', '搬血境中期', '搬血境圆满'] and user_msg['poxian_num'] == 0:
        exp = user_msg['exp']
        now_exp = exp
        sql_message.updata_level(user_id, '江湖好手') #重置用户境界
        sql_message.update_levelrate(user_id, 0) #重置突破成功率
        sql_message.update_j_exp(user_id, now_exp) #重置用户修为
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        sql_message.update_user_random_gender(user_id) #重置用户性别
        msg = f"{user_name}现在是一介凡人了！！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await resetting.finish()
    else:
        msg = f"道友境界未达要求，自废修为的最低境界为搬血境！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await resetting.finish()


# 定义属性映射
ATTRIBUTE_MAP = {
    '修炼': 'cultEff',
    '闭关': 'seclEff',
    '灵根': 'maxR',
    '血量': 'maxH',
    '真元': 'maxM',
    '攻击': 'maxA'
}

ATTRIBUTE_DESCRIPTIONS = {
    '修炼': '（每点增加修炼效率1%）',
    '闭关': '（每点增加闭关效率1%）',
    '灵根': '（每点增加灵根效率1%）',
    '血量': '（每点增加血量100000）',
    '真元': '（每点增加真元100000）',
    '攻击': '（每点增加攻击10000）'
}

@lunhui_jiadian.handle(parameterless=[Cooldown(at_sender=False)])
async def add_rebirth_points(bot: Bot, event: GroupMessageEvent, args: Tuple[str, str] = RegexGroup()):
    # 获取消息事件中的群组ID
    send_group_id = str(event.group_id)

    # 检查用户是否存在
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui_jiadian.finish()

    # 获取用户的ID和轮回点数
    user_id = user_info['user_id']
    user_msg = sql_message.get_user_info_with_id(user_id)
    rbPts = user_msg['rbPts']

    # 获取用户输入的纯文本
    input_attr, points_str = args

    # 如果输入为空，则发送帮助信息
    if not input_attr or input_attr == "轮回加点":
        await bot.send_group_msg(group_id=int(send_group_id), message=__rebirth_help__)
        await lunhui_jiadian.finish()

    # 处理查询情况
    if input_attr == "查询":
        await query_rebirth_points(bot, send_group_id, user_msg)
        await lunhui_jiadian.finish()

    # 处理重置情况
    if input_attr == "重置":
        await reset_rebirth_points(bot, send_group_id, user_id, user_msg)
        await lunhui_jiadian.finish()

    # 如果轮回点数小于等于0，直接提示用户
    if rbPts <= 0:
        msg = "您当前没有可用的轮回点数，请先获得轮回点数后再尝试加点。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui_jiadian.finish()

    # 检查属性名称是否有效，并转换为小写
    attribute_key = input_attr.strip().lower()
    if attribute_key not in ATTRIBUTE_MAP:
        msg = "无效的属性文字，请输入 修炼、闭关、灵根、血量、真元 或 攻击。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui_jiadian.finish()

    # 将字符串转换为整数
    if not points_str.isdigit():
        msg = "请输入正确的指令！例如：轮回加点 文字 数字 或 轮回加点 重置"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui_jiadian.finish()

    points = int(points_str)

    # 检查是否有足够的轮回点数
    if points > user_msg['rbPts']:
        msg = f"轮回点不足，您只有 {user_msg['rbPts']} 点可用，但您尝试分配 {points} 点。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui_jiadian.finish()

    # 更新用户数据
    new_rbPts = user_msg['rbPts'] - points
    attribute_name = ATTRIBUTE_MAP[attribute_key]
    new_attribute_value = user_msg[attribute_name] + points

    # 更新数据库中的用户信息
    try:
        sql_message.update_user_info(user_id, {'rbPts': new_rbPts, attribute_name: new_attribute_value})
    except Exception as e:
        msg = f"更新数据库失败：{str(e)}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await lunhui_jiadian.finish()

    # 输出结果
    msg = (
        f"成功分配轮回点 {attribute_key}：+{points} 点\n"
        f"{attribute_key} 现已分配轮回点：{new_attribute_value}\n"
        f"剩余未分配轮回点数：{new_rbPts}"
    )
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await lunhui_jiadian.finish()


async def query_rebirth_points(bot: Bot, send_group_id: int, user_msg: dict):
    # 构建查询结果
    query_result = "当前已分配的属性点和剩余未分配属性点：\n"
    for attr_name, db_field in ATTRIBUTE_MAP.items():
        desc = ATTRIBUTE_DESCRIPTIONS.get(attr_name, '')
        query_result += f"{attr_name}：{user_msg[db_field]} {desc}\n"

    query_result += f"剩余未分配轮回点数：{user_msg['rbPts']}"

    # 发送查询结果
    await bot.send_group_msg(group_id=int(send_group_id), message=query_result)


async def reset_rebirth_points(bot: Bot, send_group_id: int, user_id: int, user_msg: dict):
    # 计算所有已分配的属性点数
    allocated_points = sum([user_msg[attr] for attr in ATTRIBUTE_MAP.values()])
    # 清空所有已分配的属性点
    reset_data = {attr: 0 for attr in ATTRIBUTE_MAP.values()}
    # 更新数据库中的用户信息，只更新需要重置的属性
    try:
        sql_message.update_user_info(user_id, reset_data)
    except Exception as e:
        msg = f"更新数据失败：{str(e)}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        return
    # 更新 rbPts，只加上已分配的属性点数
    try:
        sql_message.add_rebirth_points(user_id, allocated_points)
    except Exception as e:
        msg = f"新增数据失败：{str(e)}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        return
    # 输出结果
    msg = f"成功重置所有轮回点。\n当前未分配轮回点数：{user_msg['rbPts'] + allocated_points}"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)