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

xiuxian_message = on_command("我的修仙信息", aliases={"我的存档"}, priority=23, permission=GROUP, block=True)
xiuxian_message_img = on_command("图片版我的修仙信息", aliases={"图片版我的存档"}, priority=23, permission=GROUP, block=True)
sql_message = XiuxianDateManage()  # sql类


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

    user_num = user_info['id']
    rank = sql_message.get_exp_rank(user_id)
    user_rank = int(rank[0])
    stone = sql_message.get_stone_rank(user_id)
    user_stone = int(stone[0])

    if user_name:
        pass
    else:
        user_name = f"无名氏(发送改名+道号更新)"

    level_rate = sql_message.get_root_rate(user_info['root_type'])  # 灵根倍率
    realm_rate = jsondata.level_data()[user_info['level']]["spend"]  # 境界倍率
    sect_id = user_info['sect_id']
    if sect_id:
        sect_info = sql_message.get_sect_info(sect_id)
        sectmsg = sect_info['sect_name']
        sectzw = jsondata.sect_config_data()[f"{user_info['sect_position']}"]["title"]
    else:
        sectmsg = f"无宗门"
        sectzw = f"无"

    # 判断突破的修为
    list_all = len(OtherSet().level) - 1
    now_index = OtherSet().level.index(user_info['level'])
    if list_all == now_index:
        exp_meg = f"位面至高"
    else:
        is_updata_level = OtherSet().level[now_index + 1]
        need_exp = sql_message.get_level_power(is_updata_level)
        get_exp = need_exp - user_info['exp']
        if get_exp > 0:
            exp_meg = f"还需{number_to(get_exp)}修为可突破！"
        else:
            exp_meg = f"可突破！"

    user_buff_data = UserBuffDate(user_id)
    user_main_buff_date = user_buff_data.get_user_main_buff_data()
    user_sub_buff_date = user_buff_data.get_user_sub_buff_data()
    user_sec_buff_date = user_buff_data.get_user_sec_buff_data()
    user_weapon_data = user_buff_data.get_user_weapon_data()
    user_armor_data = user_buff_data.get_user_armor_buff_data()

    user_poxian = user_info['poxian_num']  # 获取用户破限次数

    # 计算破限带来的总增幅百分比
    total_poxian_percent = 0
    if user_poxian <= 10:
        total_poxian_percent += user_poxian * 10
    else:
        total_poxian_percent += 10 * 10  # 前10次破限的总增幅
        total_poxian_percent += (user_poxian - 10) * 20  # 超过10次之后的增幅


    # 获取轮回点数
    user_cultEff = user_info['cultEff']
    user_seclEff = user_info['seclEff']
    user_maxR = user_info['maxR']
    user_maxH = user_info['maxH']
    user_maxM = user_info['maxM']
    user_maxA = user_info['maxA']

    # 应用破限增幅到战力和攻击力 轮回点的增幅为加算
    level_rate_decimal = Decimal(str(level_rate))
    user_maxR_decimal = Decimal(str(user_maxR))
    user_info_atk_decimal = Decimal(str(user_info['atk']))
    user_maxA_decimal = Decimal(str(user_maxA))

    level_rate_with_poxian = (level_rate_decimal + (user_maxR_decimal / Decimal('100'))) * (
                1 + total_poxian_percent / Decimal('100'))
    atk_with_poxian = (user_info_atk_decimal + (user_maxA_decimal * Decimal('10000'))) * (
                1 + total_poxian_percent / Decimal('100'))

    main_buff_name = f"无"
    sub_buff_name = f"无"
    sec_buff_name = f"无"
    weapon_name = f"无"
    armor_name = f"无"
    if user_main_buff_date is not None:
        main_buff_name = f"{user_main_buff_date['name']}({user_main_buff_date['level']})"
    if user_sub_buff_date != None:
        sub_buff_name = f"{user_sub_buff_date['name']}({user_sub_buff_date['level']})"
    if user_sec_buff_date is not None:
        sec_buff_name = f"{user_sec_buff_date['name']}({user_sec_buff_date['level']})"
    if user_weapon_data is not None:
        weapon_name = f"{user_weapon_data['name']}({user_weapon_data['level']})"
    if user_armor_data is not None:
        armor_name = f"{user_armor_data['name']}({user_armor_data['level']})"
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    leveluprate = int(user_info['level_up_rate'])  # 用户失败次数加成
    number = main_rate_buff["number"] if main_rate_buff is not None else 0
    level_rate_with_poxian = Decimal(str(level_rate_with_poxian))
    realm_rate = Decimal(str(realm_rate))
    DETAIL_MAP = {
        "道号": f"{user_name}",
        "性别": f"{user_info['user_sex']}",
        "境界": f"{user_info['level']}",
        "修为": f"{number_to(user_info['exp'])}",
        "灵石": f"{number_to(user_info['stone'])}",
        "战力": f"{number_to(int(user_info['exp'] * level_rate_with_poxian * realm_rate))}",
        "灵根": f"{user_info['root']}({user_info['root_type']}+{int(level_rate_with_poxian * 100)}%)",
        "破限增幅": f"{total_poxian_percent}%",
        "突破状态": f"{exp_meg}概率：{jsondata.level_rate_data()[user_info['level']] + leveluprate + number}%",
        "攻击力": f"{number_to(int(atk_with_poxian))}，攻修等级{user_info['atkpractice']}级",
        "所在宗门": sectmsg,
        "宗门职位": sectzw,
        "主修功法": main_buff_name,
        "辅修功法": sub_buff_name,
        "副修神通": sec_buff_name,
        "法器": weapon_name,
        "防具": armor_name,
        "注册位数": f"道友是踏入修仙世界的第{int(user_num)}人",
        "修为排行": f"道友的修为排在第{int(user_rank)}位",
        "灵石排行": f"道友的灵石排在第{int(user_stone)}位",
    }

    if XiuConfig().user_info_image:
        img_res = await draw_user_info_img(user_id, DETAIL_MAP)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(img_res))
        await xiuxian_message_img.finish()
    else:
        msg = f"""{user_name}道友的信息
灵根为：{user_info['root']}({user_info['root_type']}+{int(level_rate_with_poxian * 100)}%)
当前境界：{user_info['level']}(境界+{int(realm_rate * 100)}%)
当前灵石：{user_info['stone']}
当前修为：{user_info['exp']}(修炼效率+{int((level_rate_with_poxian * realm_rate) * 100)}%)
突破状态：{exp_meg}
你的战力为：{int(user_info['exp'] * level_rate_with_poxian * realm_rate)}"""
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)


@xiuxian_message.handle(parameterless=[Cooldown(at_sender=False)])
async def xiuxian_message_(bot: Bot, event: GroupMessageEvent):
    """我的修仙信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await xiuxian_message.finish()
    user_id = user_info['user_id']
    user_info = sql_message.get_user_real_info(user_id)
    user_name = user_info['user_name']

    user_num = user_info['id']
    rank = sql_message.get_exp_rank(user_id)
    user_rank = int(rank[0])
    stone = sql_message.get_stone_rank(user_id)
    user_stone = int(stone[0])

    if user_name:
        pass
    else:
        user_name = f"无名氏(发送改名+道号更新)"

    level_rate = sql_message.get_root_rate(user_info['root_type'])  # 灵根倍率
    realm_rate = jsondata.level_data()[user_info['level']]["spend"]  # 境界倍率
    sect_id = user_info['sect_id']
    if sect_id:
        sect_info = sql_message.get_sect_info(sect_id)
        sectmsg = sect_info['sect_name']
        sectzw = jsondata.sect_config_data()[f"{user_info['sect_position']}"]["title"]
    else:
        sectmsg = f"无宗门"
        sectzw = f"无"

    # 判断突破的修为
    list_all = len(OtherSet().level) - 1
    now_index = OtherSet().level.index(user_info['level'])
    if list_all == now_index:
        exp_meg = f"位面至高"
    else:
        is_updata_level = OtherSet().level[now_index + 1]
        need_exp = sql_message.get_level_power(is_updata_level)
        get_exp = need_exp - user_info['exp']
        if get_exp > 0:
            exp_meg = f"还需{number_to(get_exp)}修为可突破！"
        else:
            exp_meg = f"可突破！"

    user_buff_data = UserBuffDate(user_id)
    user_main_buff_date = user_buff_data.get_user_main_buff_data()
    user_sub_buff_date = user_buff_data.get_user_sub_buff_data()
    user_sec_buff_date = user_buff_data.get_user_sec_buff_data()
    user_weapon_data = user_buff_data.get_user_weapon_data()
    user_armor_data = user_buff_data.get_user_armor_buff_data()

    user_poxian = user_info['poxian_num']  # 获取用户破限次数

    # 计算破限带来的总增幅百分比
    total_poxian_percent = 0
    if user_poxian <= 10:
        total_poxian_percent += user_poxian * 10
    else:
        total_poxian_percent += 10 * 10  # 前10次破限的总增幅
        total_poxian_percent += (user_poxian - 10) * 20  # 超过10次之后的增幅


    # 获取轮回点数
    user_cultEff = user_info['cultEff']
    user_seclEff = user_info['seclEff']
    user_maxR = user_info['maxR']
    user_maxH = user_info['maxH']
    user_maxM = user_info['maxM']
    user_maxA = user_info['maxA']

    # 应用破限增幅到战力和攻击力 轮回点的增幅为加算
    level_rate_decimal = Decimal(str(level_rate))
    user_maxR_decimal = Decimal(str(user_maxR))
    user_info_atk_decimal = Decimal(str(user_info['atk']))
    user_maxA_decimal = Decimal(str(user_maxA))
    total_poxian_percent_decimal = Decimal(str(total_poxian_percent))

    level_rate_with_poxian = (level_rate_decimal + (user_maxR_decimal / Decimal('100'))) * (
                1 + total_poxian_percent_decimal / Decimal('100'))
    atk_with_poxian = (user_info_atk_decimal + (user_maxA_decimal * Decimal('10000'))) * (
                1 + total_poxian_percent_decimal / Decimal('100'))

    main_buff_name = f"无"
    sub_buff_name = f"无"
    sec_buff_name = f"无"
    weapon_name = f"无"
    armor_name = f"无"
    if user_main_buff_date is not None:
        main_buff_name = f"{user_main_buff_date['name']}({user_main_buff_date['level']})"
    if user_sub_buff_date != None:
        sub_buff_name = f"{user_sub_buff_date['name']}({user_sub_buff_date['level']})"
    if user_sec_buff_date is not None:
        sec_buff_name = f"{user_sec_buff_date['name']}({user_sec_buff_date['level']})"
    if user_weapon_data is not None:
        weapon_name = f"{user_weapon_data['name']}({user_weapon_data['level']})"
    if user_armor_data is not None:
        armor_name = f"{user_armor_data['name']}({user_armor_data['level']})"
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    leveluprate = int(user_info['level_up_rate'])  # 用户失败次数加成
    number = main_rate_buff["number"] if main_rate_buff is not None else 0

    # 信息带有表情的ID集合
    id_set = {"232391978", "985955029", "325667774", "837850320", "553077843"}
    gender_emoji = {
        '男': '🧚‍♂️',  # 男性仙人
        '女': '🧚‍♀️',  # 女性仙人
        '其他': '🧍‍♂️'  # 其他性别
    }
    emoji = gender_emoji.get(user_info['user_sex'], '🧍‍♂️')  # 默认使用思考脸

    level_rate_with_poxian = Decimal(str(level_rate_with_poxian))
    realm_rate = Decimal(str(realm_rate))

    if user_poxian >= 100 or user_id in id_set:
        msg = f""" 
🌟 道号: {user_name}
{emoji} 性别: {user_info['user_sex']}
🔢 ID: {user_id}
✨ 境界: {user_info['level']}
⚡  修为: {number_to(user_info['exp'])}
💎 灵石: {number_to(user_info['stone'])}
💥 战力: {number_to(int(user_info['exp'] * level_rate_with_poxian * realm_rate))}
🌱 灵根: {user_info['root']}({user_info['root_type']}+{int(level_rate_with_poxian * 100)}%)
🌈 破限增幅: {total_poxian_percent}%
🔮 突破状态: {exp_meg}概率：{jsondata.level_rate_data()[user_info['level']] + leveluprate + number}%
🔥 攻击力: {number_to(int(atk_with_poxian))}，攻修等级{user_info['atkpractice']}级
🏢 所在宗门: {sectmsg}
👥 宗门职位: {sectzw}
📜 主修功法: {main_buff_name}
📚 辅修功法: {sub_buff_name}
🧙‍♂️ 副修神通: {sec_buff_name}
⚔️ 法器: {weapon_name}
🛡️ 防具: {armor_name}
🔢 注册位数: 道友是踏入修仙世界的第{int(user_num)}人
🏆 修为排行: 道友的修为排在第{int(user_rank)}位
💎 灵石排行: 道友的灵石排在第{int(user_stone)}位
"""
    else:
        msg = f"""
道号: {user_name}
性别: {user_info['user_sex']}
ID: {user_id}
境界: {user_info['level']}
修为: {number_to(user_info['exp'])}
灵石: {number_to(user_info['stone'])}
战力: {number_to(int(user_info['exp'] * level_rate_with_poxian * realm_rate))}
灵根: {user_info['root']}({user_info['root_type']}+{int(level_rate_with_poxian * 100)}%)
破限增幅: {total_poxian_percent}%
突破状态: {exp_meg}概率：{jsondata.level_rate_data()[user_info['level']] + leveluprate + number}%
攻击力: {number_to(int(atk_with_poxian))}，攻修等级{user_info['atkpractice']}级
所在宗门: {sectmsg}
宗门职位: {sectzw}
主修功法: {main_buff_name}
辅修功法: {sub_buff_name}
副修神通: {sec_buff_name}
法器: {weapon_name}
防具: {armor_name}
注册位数: 道友是踏入修仙世界的第{int(user_num)}人
修为排行: 道友的修为排在第{int(user_rank)}位
灵石排行: 道友的灵石排在第{int(user_stone)}位
"""
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)