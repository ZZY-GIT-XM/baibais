from decimal import Decimal

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent,
    MessageSegment
)
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage, OtherSet, UserBuffDate
from ..xiuxian_utils.data_source import jsondata
from .draw_user_info import draw_user_info_img
from ..xiuxian_utils.utils import check_user, get_msg_pic, number_to
from ..xiuxian_config import XiuConfig
from .xiuxian_calculator import XiuxianCalculator

sql_message = XiuxianDateManage()  # sql类

xiuxian_message = on_command("我的修仙信息", aliases={"我的存档"}, priority=23, permission=GROUP, block=True)
xiuxian_message_img = on_command("图片版我的修仙信息", aliases={"图片版我的存档"}, priority=23, permission=GROUP, block=True)


@xiuxian_message_img.handle(parameterless=[Cooldown(at_sender=False)])
async def xiuxian_message_img_(bot: Bot, event: GroupMessageEvent):
    """我的修仙信息(图片版)"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await xiuxian_message_img.finish()
    user_id = user_info['user_id']
    user_info = sql_message.get_user_real_info(user_id)
    user_name = user_info['user_name']

    if user_name:
        pass
    else:
        user_name = f"无名氏(发送改名+道号更新)"

    calculator = XiuxianCalculator(user_info)
    calculated_info = calculator.calculate()

    DETAIL_MAP = {
        "道号": calculated_info['道号'],
        "性别": calculated_info['性别'],
        "境界": calculated_info['境界'],
        "修为": calculated_info['修为'],
        "灵石": calculated_info['灵石'],
        "战力": calculated_info['战力'],
        "灵根": calculated_info['灵根'],
        "破限增幅": calculated_info['破限增幅'],
        "突破状态": f"{calculated_info['突破状态']} 突破概率: {calculated_info['突破概率']}",
        "攻击力": f"{calculated_info['攻击力']}，攻修等级{calculated_info['攻修等级']}级",
        "所在宗门": calculated_info['所在宗门'],
        "宗门职位": calculated_info['宗门职位'],
        "主修功法": calculated_info['主修功法'],
        "辅修功法": calculated_info['辅修功法'],
        "副修神通": calculated_info['副修神通'],
        "法器": calculated_info['法器'],
        "防具": calculated_info['防具'],
        "注册位数": f"道友是踏入修仙世界的第{int(user_info['id'])}人",
        "修为排行": f"道友的修为排在第{int(calculated_info['修为排行'])}位",
        "灵石排行": f"道友的灵石排在第{int(calculated_info['灵石排行'])}位",
    }

    img_res = await draw_user_info_img(user_id, DETAIL_MAP)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(img_res))
    await xiuxian_message_img.finish()


@xiuxian_message.handle(parameterless=[Cooldown(at_sender=False)])
async def xiuxian_message_(bot: Bot, event: GroupMessageEvent):
    """我的修仙信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await xiuxian_message.finish()

    user_info = sql_message.get_user_real_info(user_info['user_id'])
    calculator = XiuxianCalculator(user_info)
    calculated_info = calculator.calculate()

    # 信息带有表情的ID集合
    id_set = {"232391978", "985955029", "325667774", "837850320", "553077843"}
    gender_emoji = {
        '男': '🧚‍♂️',  # 男性仙人
        '女': '🧚‍♀️',  # 女性仙人
        '其他': '🧍‍♂️'  # 其他性别
    }
    emoji = gender_emoji.get(user_info['user_sex'], '🧍‍♂️')  # 默认使用其他性别

    if user_info['poxian_num'] >= 100 or user_info['user_id'] in id_set:  # 破限次数大于等于100或ID在id_set中的用户
        msg = f""" 
🌟 道号: {calculated_info['道号']}
{emoji} 性别: {calculated_info['性别']}
🔢 ID: {calculated_info['ID']}
✨ 境界: {calculated_info['境界']}
⚡  修为: {calculated_info['修为']}
💎 灵石: {calculated_info['灵石']}
💥 战力: {calculated_info['战力']}
🌱 灵根: {calculated_info['灵根']}
🌈 破限增幅: {calculated_info['破限增幅']}
🔮 突破状态: {calculated_info['突破状态']} 突破概率: {calculated_info['突破概率']}
🔥 攻击力: {calculated_info['攻击力']}，攻修等级{calculated_info['攻修等级']}级
🏢 所在宗门: {calculated_info['所在宗门']}
👥 宗门职位: {calculated_info['宗门职位']}
📜 主修功法: {calculated_info['主修功法']}
📚 辅修功法: {calculated_info['辅修功法']}
🧙‍♂️ 副修神通: {calculated_info['副修神通']}
⚔️ 法器: {calculated_info['法器']}
🛡️ 防具: {calculated_info['防具']}
🔢 注册位数: 道友是踏入修仙世界的第{int(user_info['id'])}人
🏆 修为排行: 道友的修为排在第{int(calculated_info['修为排行'])}位
💎 灵石排行: 道友的灵石排在第{int(calculated_info['灵石排行'])}位
"""
    else:
        msg = f"""
道号: {calculated_info['道号']}
性别: {calculated_info['性别']}
ID: {calculated_info['ID']}
境界: {calculated_info['境界']}
修为: {calculated_info['修为']}
灵石: {calculated_info['灵石']}
战力: {calculated_info['战力']}
灵根: {calculated_info['灵根']}
破限增幅: {calculated_info['破限增幅']}
突破状态: {calculated_info['突破状态']} 突破概率: {calculated_info['突破概率']}
攻击力: {calculated_info['攻击力']}，攻修等级{calculated_info['攻修等级']}级
所在宗门: {calculated_info['所在宗门']}
宗门职位: {calculated_info['宗门职位']}
主修功法: {calculated_info['主修功法']}
辅修功法: {calculated_info['辅修功法']}
副修神通: {calculated_info['副修神通']}
法器: {calculated_info['法器']}
防具: {calculated_info['防具']}
注册位数: 道友是踏入修仙世界的第{int(user_info['id'])}人
修为排行: 道友的修为排在第{int(calculated_info['修为排行'])}位
灵石排行: 道友的灵石排在第{int(calculated_info['灵石排行'])}位
"""
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)