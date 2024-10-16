import asyncio
import random
import re
from decimal import Decimal

from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment
)
from nonebot.log import logger
from datetime import datetime
from nonebot import on_command, on_fullmatch, require
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, OtherSet, get_player_info,
    save_player_info, UserBuffDate, get_main_info_msg,
    get_user_buff, get_sec_msg, get_sub_info_msg,
    XIUXIAN_IMPART_BUFF
)
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.data_source import jsondata
from nonebot.params import CommandArg
from ..xiuxian_utils.player_fight import Player_fight
from ..xiuxian_utils.utils import (
    number_to, check_user, send_msg_handler,
    check_user_type, get_msg_pic, CommandObjectID
)
# from ..xiuxian_back.back_util import get_user_skill_back_msg
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from .two_exp_cd import two_exp_cd

cache_help = {}
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()
BLESSEDSPOTCOST = 3500000
two_exp_limit = 5  # 默认双修次数上限，修仙之人一天5次也不奇怪（

buffInfo = on_fullmatch("我的功法", priority=25, permission=GROUP, block=True)
out_closing = on_command("出关", aliases={"灵石出关"}, priority=5, permission=GROUP, block=True)
in_closing = on_fullmatch("闭关", priority=5, permission=GROUP, block=True)
cultivation_command = on_command("修炼", priority=5, permission=GROUP, block=True)
stone_exp = on_command("灵石修仙", aliases={"灵石修炼"}, priority=5, permission=GROUP, block=True)
two_exp = on_command("双修", priority=5, permission=GROUP, block=True)
mind_state = on_fullmatch("我的状态", priority=7, permission=GROUP, block=True)
qc = on_command("切磋", priority=6, permission=GROUP, block=True)
blessed_spot_creat = on_fullmatch("洞天福地购买", priority=10, permission=GROUP, block=True)
blessed_spot_info = on_fullmatch("洞天福地查看", priority=11, permission=GROUP, block=True)
blessed_spot_rename = on_command("洞天福地改名", priority=7, permission=GROUP, block=True)
ling_tian_up = on_fullmatch("灵田开垦", priority=5, permission=GROUP, block=True)
del_exp_decimal = on_fullmatch("抑制黑暗动乱", priority=9, permission=GROUP, block=True)
my_exp_num = on_fullmatch("我的双修次数", priority=9, permission=GROUP, block=True)


def generate_random_blessed_spot_name():
    """生成随机洞天福地名称"""
    names = ["幻月洞天", "幽影魔域", "九天玄界", "碧落仙源", "幽冥天", "万古冰原", "星河秘境", "云隐仙居",
             "翠影灵谷", "龙翔九天", "紫霄神境", "幽冥神殿", "天罡秘境", "碧落琼楼", "幽冥禁地", "万古药园",
             "星辰幻境", "仙灵福地", "幽冥深渊", "碧落天池", "九天仙境", "幽冥鬼谷", "万古神泉", "星河神域",
             "碧落灵界", "玄冰洞天", "幽冥绝域", "万古仙山", "星河灵域", "碧落瑶台", "幽冥鬼界", "万古灵墟",
             "星辰秘藏", "幽冥古洞", "碧落神渊", "九天云外", "幽冥雾海", "万古剑冢", "幽冥魔宫", "万古龙脉",
             "星辰宝殿", "幽冥鬼域", "碧落天宫", "九天玄霄", "幽冥鬼森", "万古冰魄", "星河秘府", "碧落神宫",
             "幽冥魔渊", "九天琼台", "幽冥炼狱", "万古仙域", "星河洞天", "九天云阙", "幽冥秘境", "万古仙潭",
             "星河幻境", "碧落瑶池", "九天神域", "幽冥魔窟", "万古神木", "星河灵泉", "碧落神坛", "幽冥鬼蜮",
             "九天灵霄", "幽冥古刹", "万古神坛", "碧落仙府", "烈焰火山口", "寒冰极地渊", "风雷谷秘境",
             "蓬莱仙岛域", "昆仑仙境地", "瑶姬天池畔", "幽影迷雾林", "星辰陨落谷", "金丹洞天府", "元婴秘境园",
             "化神天宫阙", "碧澜灵泉源", "幽冥魔域森", "万古仙灵域", "星辰瑶池境", "天罡神雷峰", "碧落云隐境",
             "幽冥影月潭", "万古冰魄谷", "星河轮回道", "碧落神霄殿", "幽冥夜魔岭", "万古剑意山", "星河幻梦泽",
             "碧落仙境源", "幽冥鬼雾林", "九天雷火域", "苍穹灵霄阁", "碧落瑶光池"]
    return random.choice(names)


@blessed_spot_creat.handle(parameterless=[Cooldown(at_sender=False)])
async def blessed_spot_creat_(bot: Bot, event: GroupMessageEvent):
    """洞天福地购买"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_creat.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) != 0:
        msg = f"{user_info['user_name']} 道友已经拥有洞天福地了，请发送洞天福地查看吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_creat.finish()

    if user_info['stone'] < BLESSEDSPOTCOST:
        msg = f"{user_info['user_name']} 道友的灵石不足{BLESSEDSPOTCOST}枚，无法购买洞天福地"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_creat.finish()

    else:
        sql_message.update_ls(user_id, BLESSEDSPOTCOST, 2)
        sql_message.update_user_blessed_spot_flag(user_id)
        mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
        mix_elixir_info['收取时间'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
        msg = f"恭喜{user_info['user_name']}道友拥有了自己的洞天福地，请收集聚灵旗来提升洞天福地的等级吧~\n"
        msg += f"默认名称为：{user_info['user_name']}道友的家"
        sql_message.update_user_blessed_spot_name(user_id, f"{user_info['user_name']}道友的家")
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_creat.finish()


@blessed_spot_info.handle(parameterless=[Cooldown(at_sender=False)])
async def blessed_spot_info_(bot: Bot, event: GroupMessageEvent):
    """洞天福地信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_info.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"{user_info['user_name']} 道友还没有洞天福地呢，请发送洞天福地购买来购买吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_info.finish()

    msg = f"\n道友的洞天福地:\n"
    user_buff_data = UserBuffDate(user_id).buffinfo
    if user_info['blessed_spot_name'] == 0:
        blessed_spot_name = "尚未命名"
    else:
        blessed_spot_name = user_info['blessed_spot_name']

    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    msg += f"名字：{blessed_spot_name}\n"
    msg += f"修炼速度：增加{int(user_buff_data['blessed_spot']) * 100}%\n"
    msg += f"灵田数量：{mix_elixir_info['灵田数量']}"

    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await blessed_spot_info.finish()


@ling_tian_up.handle(parameterless=[Cooldown(at_sender=False)])
async def ling_tian_up_(bot: Bot, event: GroupMessageEvent):
    """洞天福地灵田升级"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await ling_tian_up.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"{user_info['user_name']} 道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await ling_tian_up.finish()

    LINGTIANCONFIG = {
        "1": {
            "level_up_cost": 3500000
        },
        "2": {
            "level_up_cost": 5000000
        },
        "3": {
            "level_up_cost": 7000000
        },
        "4": {
            "level_up_cost": 10000000
        },
        "5": {
            "level_up_cost": 15000000
        }
    }

    # 获取用户的破限次数
    user_poxian = user_info['poxian_num']

    # 计算当前灵田的最大数量
    max_lingtian = len(LINGTIANCONFIG) + user_poxian + 1  # 初始等级为6级

    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_num = mix_elixir_info['灵田数量']

    if now_num >= max_lingtian:
        msg = f"{user_info['user_name']} 道友的灵田已全部开垦完毕，无法继续开垦了！"
    else:
        # 计算升级成本
        if now_num <= len(LINGTIANCONFIG):
            base_cost = LINGTIANCONFIG[str(now_num)]['level_up_cost']
        else:
            base_cost = LINGTIANCONFIG[str(len(LINGTIANCONFIG))]['level_up_cost'] * (
                    2 ** (now_num - len(LINGTIANCONFIG)))

        additional_cost = user_poxian * 5000000  # 每次破限增加5000000灵石
        cost = base_cost + additional_cost

        if int(user_info['stone']) < cost:
            msg = f"{user_info['user_name']} 本次开垦需要灵石：{cost}，道友的灵石不足！"
        else:
            msg = f"{user_info['user_name']} 道友成功消耗灵石：{cost}，灵田数量+1,目前数量:{now_num + 1}"
            mix_elixir_info['灵田数量'] = now_num + 1
            save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
            sql_message.update_ls(user_id, cost, 2)

    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await ling_tian_up.finish()


@blessed_spot_rename.handle(parameterless=[Cooldown(at_sender=False)])
async def blessed_spot_rename_(bot: Bot, event: GroupMessageEvent):
    """洞天福地改名"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_rename.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"{user_info['user_name']} 道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await blessed_spot_rename.finish()

    new_name = generate_random_blessed_spot_name()  # 生成随机名称
    sql_message.update_user_blessed_spot_name(user_id, new_name)  # 更新数据库中的洞天福地名称
    msg = f"{user_info['user_name']} 道友的洞天福地成功改名为：{new_name}"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await blessed_spot_rename.finish()


@qc.handle(parameterless=[Cooldown(stamina_cost=5, at_sender=False)])
async def qc_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """切磋，不会掉血"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await qc.finish()
    user_id = user_info['user_id']
    user1 = sql_message.get_user_real_info(user_id)

    give_qq = None  # 切磋后边的文字存到这里
    for arg in args:
        if arg.type == "text":  # 查找文本类型的参数
            give_qq = arg.data.get("text", "").strip()  # 获取并清理文本
            break

    if give_qq:
        # 查询数据库中是否有名字匹配的玩家
        user_2name = sql_message.get_user_info_with_name(give_qq)
        if user_2name is not None:
            user2 = sql_message.get_user_real_info(user_2name['user_id'])
            if user_2name['user_id'] == user_id:
                msg = "道友不会左右互搏之术！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await qc.finish()
        else:
            # 如果没有找到匹配的玩家名字
            msg = "未找到名字为 '{}' 的玩家，请确保名字正确。".format(give_qq)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await qc.finish()
    else:
        # 如果没有提供玩家名字
        msg = "请输入要切磋的玩家名字。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await qc.finish()

    if user1 and user2:
        player1 = {"user_id": None, "道号": None, "气血": None,
                   "攻击": None, "真元": None, '会心': None, '防御': 0, 'exp': 0}
        player2 = {"user_id": None, "道号": None, "气血": None,
                   "攻击": None, "真元": None, '会心': None, '防御': 0, 'exp': 0}

        # 添加破限增幅计算
        poxian_num1 = user1['poxian_num']
        poxian_num2 = user2['poxian_num']
        # 计算破限带来的总增幅百分比
        total_poxian_percent1 = 0
        if poxian_num1 <= 10:
            total_poxian_percent1 += poxian_num1 * 10
        else:
            total_poxian_percent1 += 10 * 10  # 前10次破限的总增幅
            total_poxian_percent1 += (poxian_num1 - 10) * 20  # 超过10次之后的增幅

        total_poxian_percent2 = 0
        if poxian_num2 <= 10:
            total_poxian_percent2 += poxian_num2 * 10
        else:
            total_poxian_percent2 += 10 * 10  # 前10次破限的总增幅
            total_poxian_percent2 += (poxian_num2 - 10) * 20  # 超过10次之后的增幅

        # 获取轮回点数
        user1_cultEff = user1['cultEff'] / 100
        user1_seclEff = user1['seclEff'] / 100
        user1_maxR = user1['maxR'] / 100
        user1_maxH = user1['maxH'] * 100000
        user1_maxM = user1['maxM'] * 100000
        user1_maxA = user1['maxA'] * 10000

        # 获取轮回点数
        user2_cultEff = user2['cultEff'] / 100
        user2_seclEff = user2['seclEff'] / 100
        user2_maxR = user2['maxR'] / 100
        user2_maxH = user2['maxH'] * 100000
        user2_maxM = user2['maxM'] * 100000
        user2_maxA = user2['maxA'] * 10000

        # 应用破限增幅到攻击力
        atk_with_poxian1 = (user1['atk'] + user1_maxA) * (1 + total_poxian_percent1 / 100)
        atk_with_poxian2 = (user2['atk'] + user2_maxA) * (1 + total_poxian_percent2 / 100)
        # 应用破限增幅到气血
        hp_with_poxian1 = (user1['hp'] + user1_maxH) * (1 + total_poxian_percent1 / 100)
        hp_with_poxian2 = (user2['hp'] + user2_maxH) * (1 + total_poxian_percent2 / 100)
        # 应用破限增幅到真元
        mp_with_poxian1 = (user1['mp'] + user1_maxM) * (1 + total_poxian_percent1 / 100)
        mp_with_poxian2 = (user2['mp'] + user2_maxM) * (1 + total_poxian_percent2 / 100)

        user1_weapon_data = UserBuffDate(user_id).get_user_weapon_data()
        user1_armor_crit_buff = UserBuffDate(user_id).get_user_armor_buff_data()
        user1_main_data = UserBuffDate(user_id).get_user_main_buff_data()  # 玩家1功法会心

        if user1_main_data is not None:  # 玩家1功法会心
            main_crit_buff = Decimal(user1_main_data['crit_buff']) * (1 + total_poxian_percent1 / 100)
        else:
            main_crit_buff = 0

        if user1_armor_crit_buff is not None:  # 玩家1防具会心
            armor_crit_buff = Decimal(user1_armor_crit_buff['crit_buff']) * Decimal(1 + Decimal(total_poxian_percent1) / 100)
        else:
            armor_crit_buff = 0

        if user1_weapon_data is not None:
            user1_weapon_data['crit_buff'] = Decimal(str(user1_weapon_data['crit_buff']))
            total_poxian_percent1 = Decimal(str(total_poxian_percent1))
            armor_crit_buff = Decimal(str(armor_crit_buff))
            main_crit_buff = Decimal(str(main_crit_buff))

            player1['会心'] = int(((Decimal(user1_weapon_data['crit_buff']) * (1 + total_poxian_percent1 / 100)) + (
                armor_crit_buff) + (main_crit_buff)) * 100)
        else:
            player1['会心'] = (armor_crit_buff + main_crit_buff) * 100

        user2_weapon_data = UserBuffDate(user2['user_id']).get_user_weapon_data()
        user2_armor_crit_buff = UserBuffDate(user_id).get_user_armor_buff_data()
        user2_main_data = UserBuffDate(user_id).get_user_main_buff_data()  # 玩家2功法会心

        if user2_main_data is not None:  # 玩家2功法会心
            main_crit_buff2 = Decimal(user2_main_data['crit_buff']) * (1 + total_poxian_percent2 / 100)
        else:
            main_crit_buff2 = 0

        if user2_armor_crit_buff is not None:  # 玩家2防具会心
            armor_crit_buff2 = Decimal(user2_armor_crit_buff['crit_buff']) * (1 + total_poxian_percent2 / 100)
        else:
            armor_crit_buff2 = 0

        if user2_weapon_data is not None:
            player2['会心'] = int(((Decimal(user2_weapon_data['crit_buff']) * (1 + total_poxian_percent2 / 100)) + (
                armor_crit_buff2) + (main_crit_buff2)) * 100)
        else:
            player2['会心'] = (armor_crit_buff2 + main_crit_buff2) * 100

        player1['user_id'] = user1['user_id']
        player1['道号'] = user1['user_name']
        player1['气血'] = hp_with_poxian1  # 使用破限增幅后的气血
        player1['攻击'] = atk_with_poxian1  # 使用破限增幅后的攻击力
        player1['真元'] = mp_with_poxian1  # 使用破限增幅后的真元
        player1['exp'] = user1['exp']

        player2['user_id'] = user2['user_id']
        player2['道号'] = user2['user_name']
        player2['气血'] = hp_with_poxian2  # 使用破限增幅后的气血
        player2['攻击'] = atk_with_poxian2  # 使用破限增幅后的攻击力
        player2['真元'] = mp_with_poxian2  # 使用破限增幅后的真元
        player2['exp'] = user2['exp']

        result, victor = Player_fight(player1, player2, 1, bot.self_id)
        # 将 result 转换为字符串
        if isinstance(result, list):
            result_str = "『战斗详情』\n"
            result_str += '\n'.join(node['data']['content'] for node in result if node['data']['content'])
        else:
            result_str = result
        # await send_msg_handler(bot, event, result)
        msg = f"{result_str}\n获胜的是{victor}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await qc.finish()
    else:
        msg = "修仙界没有对方的信息，快邀请对方加入修仙界吧！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await qc.finish()


@two_exp.handle(parameterless=[Cooldown(stamina_cost=10, at_sender=False)])
async def two_exp_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """双修"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    global two_exp_limit
    isUser, user_1, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await two_exp.finish()

    two_qq = None  # 双修后边的文字存到这里
    for arg in args:
        if arg.type == "text":  # 查找文本类型的参数
            two_qq = arg.data.get("text", "").strip()  # 获取并清理文本
            break

    if two_qq:
        # 查询数据库中是否有名字匹配的玩家
        user_2 = sql_message.get_user_info_with_name(two_qq)
    else:
        user_2 = None

    if user_1 and user_2:
        if two_qq is None:
            msg = "请at你的道侣,与其一起双修！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await two_exp.finish()

        if int(user_1['user_id']) == int(user_2['user_id']):
            msg = "道友无法与自己双修！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await two_exp.finish()
        if user_2:
            exp_1 = user_1['exp']
            exp_2 = user_2['exp']
            if exp_2 > exp_1:
                msg = "修仙大能看了看你，不屑一顾，扬长而去！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await two_exp.finish()
            else:

                limt_1 = two_exp_cd.find_user(user_1['user_id'])
                limt_2 = two_exp_cd.find_user(user_2['user_id'])
                sql_message.update_last_check_info_time(user_1['user_id'])  # 更新查看修仙信息时间
                # 加入传承
                impart_data_1 = xiuxian_impart.get_user_info_with_id(user_1['user_id'])
                impart_data_2 = xiuxian_impart.get_user_info_with_id(user_2['user_id'])
                impart_two_exp_1 = impart_data_1['impart_two_exp'] if impart_data_1 is not None else 0
                impart_two_exp_2 = impart_data_2['impart_two_exp'] if impart_data_2 is not None else 0

                main_two_data_1 = UserBuffDate(user_1['user_id']).get_user_main_buff_data()  # 功法双修次数提升
                main_two_data_2 = UserBuffDate(user_2['user_id']).get_user_main_buff_data()
                main_two_1 = main_two_data_1['two_buff'] if main_two_data_1 is not None else 0
                main_two_2 = main_two_data_2['two_buff'] if main_two_data_2 is not None else 0
                if Decimal(limt_1) >= Decimal(two_exp_limit) + Decimal(impart_two_exp_1) + Decimal(main_two_1):
                    msg = "道友今天双修次数已经到达上限！"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await two_exp.finish()
                if Decimal(limt_2) >= Decimal(two_exp_limit) + Decimal(impart_two_exp_2) + Decimal(main_two_2):
                    msg = "对方今天双修次数已经到达上限！"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await two_exp.finish()
                max_exp_1 = (
                        int(OtherSet().set_closing_type(user_1['level'])) * XiuConfig().closing_exp_upper_limit
                )  # 获取下个境界需要的修为 * 1.5为闭关上限
                max_exp_2 = (
                        int(OtherSet().set_closing_type(user_2['level'])) * XiuConfig().closing_exp_upper_limit
                )
                user_get_exp_max_1 = int(max_exp_1) - user_1['exp']
                user_get_exp_max_2 = int(max_exp_2) - user_2['exp']

                if user_get_exp_max_1 < 0:
                    user_get_exp_max_1 = 0
                if user_get_exp_max_2 < 0:
                    user_get_exp_max_2 = 0
                msg = ""
                msg += f"{user_1['user_name']}与{user_2['user_name']}情投意合，于某地一起修炼了一晚。"
                if random.randint(1, 100) in [13, 14, 52, 10, 66]:
                    exp = int((exp_1 + exp_2) * 0.0055)

                    if user_1['sect_position'] is None:
                        max_exp_limit = 4
                    else:
                        max_exp_limit = user_1['sect_position']
                    max_exp = 1000000000  # jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"] #双修上限罪魁祸首
                    if exp >= max_exp:
                        exp_limit_1 = max_exp
                    else:
                        exp_limit_1 = exp

                    if exp_limit_1 >= user_get_exp_max_1:
                        sql_message.update_exp(user_1['user_id'], user_get_exp_max_1)
                        msg += f"{user_1['user_name']}修为到达上限，增加修为{user_get_exp_max_1}。"
                    else:
                        sql_message.update_exp(user_1['user_id'], exp_limit_1)
                        msg += f"{user_1['user_name']}增加修为{exp_limit_1}。"
                    sql_message.update_power2(user_1['user_id'])

                    if user_2['sect_position'] is None:
                        max_exp_limit = 4
                    else:
                        max_exp_limit = user_2['sect_position']
                    max_exp = 1000000000  # jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"] #双修上限罪魁祸首
                    if exp >= max_exp:
                        exp_limit_2 = max_exp
                    else:
                        exp_limit_2 = exp

                    if exp_limit_2 >= user_get_exp_max_2:
                        sql_message.update_exp(user_2['user_id'], user_get_exp_max_2)
                        msg += f"{user_2['user_name']}修为到达上限，增加修为{user_get_exp_max_2}。"
                    else:
                        sql_message.update_exp(user_2['user_id'], exp_limit_2)
                        msg += f"{user_2['user_name']}增加修为{exp_limit_2}。"
                    sql_message.update_power2(user_2['user_id'])
                    sql_message.update_levelrate(user_1['user_id'], user_1['level_up_rate'] + 2)
                    sql_message.update_levelrate(user_2['user_id'], user_2['level_up_rate'] + 2)
                    two_exp_cd.add_user(user_1['user_id'])
                    two_exp_cd.add_user(user_2['user_id'])
                    msg += f"离开时双方互相留法宝为对方护道,双方各增加突破概率2%。"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await two_exp.finish()
                else:
                    exp = int((exp_1 + exp_2) * 0.0055)

                    if user_1['sect_position'] is None:
                        max_exp_limit = 4
                    else:
                        max_exp_limit = user_1['sect_position']
                    max_exp = 1000000000  # jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"] #双修上限罪魁祸首
                    if exp >= max_exp:
                        exp_limit_1 = max_exp
                    else:
                        exp_limit_1 = exp
                    if exp_limit_1 >= user_get_exp_max_1:
                        sql_message.update_exp(user_1['user_id'], user_get_exp_max_1)
                        msg += f"{user_1['user_name']}修为到达上限，增加修为{user_get_exp_max_1}。"
                    else:
                        sql_message.update_exp(user_1['user_id'], exp_limit_1)
                        msg += f"{user_1['user_name']}增加修为{exp_limit_1}。"
                    sql_message.update_power2(user_1['user_id'])

                    if user_2['sect_position'] is None:
                        max_exp_limit = 4
                    else:
                        max_exp_limit = user_2['sect_position']
                    max_exp = 1000000000  # jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"] #双修上限罪魁祸首
                    if exp >= max_exp:
                        exp_limit_2 = max_exp
                    else:
                        exp_limit_2 = exp
                    if exp_limit_2 >= user_get_exp_max_2:
                        sql_message.update_exp(user_2['user_id'], user_get_exp_max_2)
                        msg += f"{user_2['user_name']}修为到达上限，增加修为{user_get_exp_max_2}。"
                    else:
                        sql_message.update_exp(user_2['user_id'], exp_limit_2)
                        msg += f"{user_2['user_name']}增加修为{exp_limit_2}。"
                    sql_message.update_power2(user_2['user_id'])
                    two_exp_cd.add_user(user_1['user_id'])
                    two_exp_cd.add_user(user_2['user_id'])
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await two_exp.finish()
    else:
        msg = "修仙者应一心向道，务要留恋凡人！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await two_exp.finish()


@stone_exp.handle(parameterless=[Cooldown(at_sender=False)])
async def stone_exp_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """灵石修炼"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await stone_exp.finish()
    user_id = user_info['user_id']
    user_mes = sql_message.get_user_info_with_id(user_id)  # 获取用户信息
    level = user_mes['level']
    use_exp = user_mes['exp']
    use_stone = user_mes['stone']
    use_poxian = user_mes['poxian_num']  # 获取用户破限信息

    # 计算破限带来的总增幅百分比
    total_poxian_percent = 0
    if use_poxian <= 10:
        total_poxian_percent += use_poxian * 10
    else:
        total_poxian_percent += 10 * 10  # 前10次破限的总增幅
        total_poxian_percent += (use_poxian - 10) * 20  # 超过10次之后的增幅

    max_exp = (
            int(OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit
    )  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    msg = args.extract_plain_text().strip()
    stone_num = re.findall(r"\d+", msg)  # 灵石数

    if stone_num:
        pass
    else:
        msg = "请输入正确的灵石数量！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await stone_exp.finish()
    stone_num = int(stone_num[0])
    if use_stone <= stone_num:
        msg = "你的灵石还不够呢，快去赚点灵石吧！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await stone_exp.finish()

    exp = int(stone_num / 10) * (1 + total_poxian_percent / 100)  # 加入破限增幅部分
    if user_info['level'] == '祭道境圆满':
        sql_message.update_exp(user_id, exp)
        sql_message.update_power2(user_id)  # 更新战力
        msg = f"修炼结束，本次修炼共增加修为：{exp},消耗灵石：{stone_num}"
        sql_message.update_ls(user_id, int(stone_num), 2)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await stone_exp.finish()

    if exp >= user_get_exp_max:
        # 用户获取的修为到达上限
        sql_message.update_exp(user_id, user_get_exp_max)
        sql_message.update_power2(user_id)  # 更新战力
        msg = f"修炼结束，本次修炼到达上限，共增加修为：{user_get_exp_max},消耗灵石：{user_get_exp_max * 10}"
        sql_message.update_ls(user_id, int(user_get_exp_max * 10), 2)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await stone_exp.finish()
    else:
        sql_message.update_exp(user_id, exp)
        sql_message.update_power2(user_id)  # 更新战力
        msg = f"修炼结束，本次修炼共增加修为：{exp},消耗灵石：{stone_num}"
        sql_message.update_ls(user_id, int(stone_num), 2)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await stone_exp.finish()


@in_closing.handle(parameterless=[Cooldown(at_sender=False)])
async def in_closing_(bot: Bot, event: GroupMessageEvent):
    """闭关"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_type = 1  # 状态0为无事件
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await out_closing.finish()

    user_id = user_info['user_id']
    is_type, msg = check_user_type(user_id, 0)

    if user_info['root_type'] == '伪灵根':
        msg = "器师无法闭关！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await in_closing.finish()

    if is_type:  # 符合
        sql_message.in_closing(user_id, user_type)
        msg = "进入闭关状态，如需出关，发送【出关】！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await in_closing.finish()
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await in_closing.finish()


@out_closing.handle(parameterless=[Cooldown(at_sender=False)])
async def out_closing_(bot: Bot, event: GroupMessageEvent):
    """出关"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_type = 0  # 状态0为无事件
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await out_closing.finish()

    user_id = user_info['user_id']
    user_mes = sql_message.get_user_info_with_id(user_id)  # 获取用户信息
    level = user_mes['level']
    use_exp = user_mes['exp']
    use_poxian = user_mes['poxian_num']  # 获取用户破限信息

    # 获取轮回点数
    use_cultEff = user_mes['cultEff'] / 100
    use_seclEff = user_mes['seclEff'] / 100
    use_maxR = user_mes['maxR'] / 100
    use_maxH = user_mes['maxH'] * 100000
    use_maxM = user_mes['maxM'] * 100000
    use_maxA = user_mes['maxA'] * 10000

    # 计算破限带来的总增幅百分比
    total_poxian_percent = 0
    if use_poxian <= 10:
        total_poxian_percent += use_poxian * 10
    else:
        total_poxian_percent += 10 * 10  # 前10次破限的总增幅
        total_poxian_percent += (use_poxian - 10) * 20  # 超过10次之后的增幅

    hp_speed = 25
    mp_speed = 50

    max_exp = (
            int(OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit
    )  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    now_time = datetime.now()
    user_cd_message = sql_message.get_user_cd(user_id)
    is_type, msg = check_user_type(user_id, 1)

    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await out_closing.finish()
    else:
        # 获取当前时间
        now_time = datetime.now()
        # 确保 create_time 是字符串类型
        create_time_str = user_cd_message['create_time'].strftime("%Y-%m-%d %H:%M:%S.%f")
        # 解析字符串为 datetime 对象
        in_closing_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S.%f")
        # 计算时间差
        exp_time = (now_time - in_closing_time).total_seconds() // 60
        # 闭关时长计算(分钟) = second // 60
        level_rate = sql_message.get_root_rate(user_mes['root_type'])  # 灵根倍率
        realm_rate = jsondata.level_data()[level]["spend"]  # 境界倍率
        user_buff_data = UserBuffDate(user_id)
        mainbuffdata = user_buff_data.get_user_main_buff_data()
        mainbuffratebuff = mainbuffdata['ratebuff'] if mainbuffdata != None else 0  # 功法修炼倍率
        mainbuffcloexp = mainbuffdata['clo_exp'] if mainbuffdata != None else 0  # 功法闭关经验
        mainbuffclors = mainbuffdata['clo_rs'] if mainbuffdata != None else 0  # 功法闭关回复

        # 将所有数值转换为 Decimal 类型
        exp_time = Decimal(str(exp_time))
        closing_exp = Decimal(str(XiuConfig().closing_exp))
        level_rate = Decimal(str(level_rate))
        use_maxR = Decimal(str(use_maxR))
        realm_rate = Decimal(str(realm_rate))
        mainbuffratebuff = Decimal(str(mainbuffratebuff))
        mainbuffcloexp = Decimal(str(mainbuffcloexp))

        # 计算经验
        exp = int(
            (exp_time * closing_exp) * (
                ((level_rate + use_maxR) * realm_rate * (1 + mainbuffratebuff) * (1 + mainbuffcloexp))
            )
        )
        # 本次闭关获取的修为
        # 计算传承增益
        impart_data = xiuxian_impart.get_user_info_with_id(user_id)
        impart_exp_up = impart_data['impart_exp_up'] if impart_data is not None else 0
        exp = int(exp * (1 + impart_exp_up))
        if exp >= user_get_exp_max:
            # 用户获取的修为到达上限
            sql_message.in_closing(user_id, user_type)
            sql_message.update_exp(user_id, user_get_exp_max)
            sql_message.update_power2(user_id)  # 更新战力

            result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed * (1 + mainbuffclors)),
                                                             int(exp * mp_speed))
            sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1], int(result_hp_mp[2] / 10))
            msg = f"闭关结束，本次闭关到达上限，共增加修为：{user_get_exp_max}{result_msg[0]}{result_msg[1]}"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await out_closing.finish()
        else:
            # 用户获取的修为没有到达上限
            if str(event.message) == "灵石出关":
                user_stone = user_mes['stone']  # 用户灵石数
                if user_stone <= 0:
                    user_stone = 0
                if exp <= user_stone:
                    exp = exp * 2
                    exp_poxian = (exp * (1 + use_seclEff)) * (1 + total_poxian_percent / 100)  # 加入破限增幅部分
                    sql_message.in_closing(user_id, user_type)
                    sql_message.update_exp(user_id, exp_poxian)
                    sql_message.update_ls(user_id, int(exp / 2), 2)
                    sql_message.update_power2(user_id)  # 更新战力

                    result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed * (1 + mainbuffclors)),
                                                                     int(exp * mp_speed))
                    sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1],
                                                      int(result_hp_mp[2] / 10))
                    msg = f"闭关结束，共闭关{exp_time}分钟，本次闭关增加修为：{exp_poxian}，消耗灵石{int(exp / 2)}枚{result_msg[0]}{result_msg[1]}"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await out_closing.finish()
                else:
                    exp = ((exp + user_stone) * (1 + use_seclEff)) * (1 + total_poxian_percent / 100)  # 加入破限增幅部分
                    sql_message.in_closing(user_id, user_type)
                    sql_message.update_exp(user_id, exp)
                    sql_message.update_ls(user_id, user_stone, 2)
                    sql_message.update_power2(user_id)  # 更新战力
                    result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed * (1 + mainbuffclors)),
                                                                     int(exp * mp_speed))
                    sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1],
                                                      int(result_hp_mp[2] / 10))
                    msg = f"闭关结束，共闭关{exp_time}分钟，本次闭关增加修为：{exp}，消耗灵石{user_stone}枚{result_msg[0]}{result_msg[1]}"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await out_closing.finish()
            else:
                exp = exp * (1 + use_seclEff) * (1 + total_poxian_percent / 100)  # 加入破限增幅部分
                sql_message.in_closing(user_id, user_type)
                sql_message.update_exp(user_id, exp)
                sql_message.update_power2(user_id)  # 更新战力
                result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(Decimal(exp) * Decimal(hp_speed) * Decimal(1 + mainbuffclors)),
                                                                 int(Decimal(exp) * Decimal(mp_speed)))
                sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1], int(result_hp_mp[2] / 10))
                msg = f"闭关结束，共闭关{exp_time}分钟，本次闭关增加修为：{exp}{result_msg[0]}{result_msg[1]}"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await out_closing.finish()


@cultivation_command.handle()
async def start_cultivation(bot: Bot, event: GroupMessageEvent):
    """开始修炼"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    user_type = 0  # 状态0为无事件
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await cultivation_command.finish()

    user_id = user_info['user_id']
    user_mes = sql_message.get_user_info_with_id(user_id)  # 获取用户信息
    level = user_mes['level']
    use_exp = user_mes['exp']
    use_poxian = user_mes['poxian_num']  # 获取用户破限信息

    # 获取轮回点数
    use_cultEff = user_mes['cultEff'] / 100
    use_seclEff = user_mes['seclEff'] / 100
    use_maxR = user_mes['maxR'] / 100
    use_maxH = user_mes['maxH'] * 100000
    use_maxM = user_mes['maxM'] * 100000
    use_maxA = user_mes['maxA'] * 10000

    # 计算破限带来的总增幅百分比
    total_poxian_percent = 0
    if use_poxian <= 10:
        total_poxian_percent += use_poxian * 10
    else:
        total_poxian_percent += 10 * 10  # 前10次破限的总增幅
        total_poxian_percent += (use_poxian - 10) * 20  # 超过10次之后的增幅

    hp_speed = 25
    mp_speed = 50

    max_exp = (
            int(OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit
    )  # 获取下个境界需要的修为 即闭关上限

    if not (user_info['level'] == '祭道境圆满'):
        # 检查用户的经验是否已经达到了该等级的最大经验值
        if use_exp >= max_exp:
            msg = f"道友已临近突破，请先突破后再来修炼！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await cultivation_command.finish()

    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    now_time = datetime.now()
    user_cd_message = sql_message.get_user_cd(user_id)
    is_type, msg = check_user_type(user_id, 0)
    if not is_type:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await cultivation_command.finish()
    else:
        # 用户状态为0，可以开始修炼
        level_rate = sql_message.get_root_rate(user_mes['root_type'])  # 灵根倍率
        realm_rate = jsondata.level_data()[level]["spend"]  # 境界倍率
        user_buff_data = UserBuffDate(user_id)
        mainbuffdata = user_buff_data.get_user_main_buff_data()
        mainbuffratebuff = mainbuffdata['ratebuff'] if mainbuffdata is not None else 0  # 功法修炼倍率
        mainbuffcloexp = mainbuffdata['clo_exp'] if mainbuffdata is not None else 0  # 功法闭关经验
        mainbuffclors = mainbuffdata['clo_rs'] if mainbuffdata is not None else 0  # 功法闭关回复

        # 将所有数值转换为 Decimal 类型
        level_rate = Decimal(str(level_rate))
        use_maxR = Decimal(str(use_maxR))
        realm_rate = Decimal(str(realm_rate))
        mainbuffratebuff = Decimal(str(mainbuffratebuff))
        mainbuffcloexp = Decimal(str(mainbuffcloexp))

        # 获取配置值并转换为 Decimal 类型
        closing_exp = Decimal(str(XiuConfig().closing_exp))
        cultivation_exp = Decimal(str(XiuConfig().cultivation_exp))

        # 计算经验
        exp = int(
            (1 * closing_exp * cultivation_exp) * (
                ((level_rate + use_maxR) * realm_rate * (1 + mainbuffratebuff) * (1 + mainbuffcloexp)))
        )  # 本次闭关获取的修为
        # 计算传承增益
        impart_data = xiuxian_impart.get_user_info_with_id(user_id)
        impart_exp_up = impart_data['impart_exp_up'] if impart_data is not None else 0
        exp = int(exp * (1 + impart_exp_up) * (1 + use_cultEff) * (1 + total_poxian_percent / 100))

        # 如果修为达到上限或大于距离上限所需的值
        if exp > user_get_exp_max:
            exp = user_get_exp_max

        await bot.send_group_msg(group_id=int(send_group_id), message="进入修炼,1分钟后结束!")  # 回复消息 "进入修炼"
        sql_message.in_closing(user_id, 4)  # 设置用户状态为 "正在修炼"
        await asyncio.sleep(60)  # 开始倒计时 60 秒
        sql_message.update_power2(user_id)  # 更新用户战力
        sql_message.update_exp(user_id, exp)  # 更新用户经验值
        sql_message.in_closing(user_id, 0)  # 设置用户状态为 "结束修炼"
        # 回复消息 "@用户 修炼的收益"
        result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(Decimal(exp) * Decimal(hp_speed) * (
                    1 + Decimal(mainbuffclors))),
                                                         int(Decimal(exp) * Decimal(mp_speed)))
        sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1], int(result_hp_mp[2] / 10))
        msg = f"修炼结束，本次修炼增加修为：{exp} {result_msg[0]}{result_msg[1]}"

        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        # 结束处理
        await cultivation_command.finish()


@mind_state.handle(parameterless=[Cooldown(at_sender=False)])
async def mind_state_(bot: Bot, event: GroupMessageEvent):
    """我的状态 信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_msg, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mind_state.finish()
    user_id = user_msg['user_id']
    sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    if user_msg['hp'] is None or user_msg['hp'] == 0:
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_real_info(user_id)

    level_rate = sql_message.get_root_rate(user_msg['root_type'])  # 灵根倍率
    realm_rate = jsondata.level_data()[user_msg['level']]["spend"]  # 境界倍率
    user_buff_data = UserBuffDate(user_id)
    main_buff_data = user_buff_data.get_user_main_buff_data()
    user_armor_crit_data = user_buff_data.get_user_armor_buff_data()  # 我的状态防具会心
    user_weapon_data = UserBuffDate(user_id).get_user_weapon_data()  # 我的状态武器减伤
    user_main_crit_data = UserBuffDate(user_id).get_user_main_buff_data()  # 我的状态功法会心
    user_main_data = UserBuffDate(user_id).get_user_main_buff_data()  # 我的状态功法减伤
    user_poxian = user_msg['poxian_num']  # 新增破限次数

    # 计算破限带来的总增幅百分比
    total_poxian_percent = 0
    if user_poxian <= 10:
        total_poxian_percent += user_poxian * 10
    else:
        total_poxian_percent += 10 * 10  # 前10次破限的总增幅
        total_poxian_percent += (user_poxian - 10) * 20  # 超过10次之后的增幅

    # 获取轮回点数
    user_cultEff = user_msg['cultEff'] / 100
    user_seclEff = user_msg['seclEff'] / 100
    user_maxR = user_msg['maxR'] / 100
    user_maxH = user_msg['maxH'] * 100000
    user_maxM = user_msg['maxM'] * 100000
    user_maxA = user_msg['maxA'] * 10000

    if user_main_data is not None:
        main_def = user_main_data['def_buff'] * 100  # 我的状态功法减伤
    else:
        main_def = 0

    if user_armor_crit_data is not None:  # 我的状态防具会心
        armor_crit_buff = ((user_armor_crit_data['crit_buff']) * 100)
    else:
        armor_crit_buff = 0

    if user_weapon_data is not None:
        crit_buff = ((user_weapon_data['crit_buff']) * 100)
    else:
        crit_buff = 0

    user_armor_data = user_buff_data.get_user_armor_buff_data()
    if user_armor_data is not None:
        def_buff = int(user_armor_data['def_buff'] * 100)  # 我的状态防具减伤
    else:
        def_buff = 0

    # user_armor_data = user_buff_data.get_user_armor_buff_data()

    if user_weapon_data is not None:
        weapon_def = user_weapon_data['def_buff'] * 100  # 我的状态武器减伤
    else:
        weapon_def = 0

    if user_main_crit_data is not None:  # 我的状态功法会心
        main_crit_buff = ((user_main_crit_data['crit_buff']) * 100)
    else:
        main_crit_buff = 0

    list_all = len(OtherSet().level) - 1
    now_index = OtherSet().level.index(user_msg['level'])
    if list_all == now_index:
        exp_meg = f"位面至高"
    else:
        is_updata_level = OtherSet().level[now_index + 1]
        need_exp = sql_message.get_level_power(is_updata_level)
        get_exp = need_exp - user_msg['exp']
        if get_exp > 0:
            exp_meg = f"还需{number_to(get_exp)}修为可突破！"
        else:
            exp_meg = f"可突破！"

    main_buff_rate_buff = main_buff_data['ratebuff'] if main_buff_data is not None else 0
    main_hp_buff = main_buff_data['hpbuff'] if main_buff_data is not None else 0
    main_mp_buff = main_buff_data['mpbuff'] if main_buff_data is not None else 0
    impart_data = xiuxian_impart.get_user_info_with_id(user_id)
    impart_hp_per = impart_data['impart_hp_per'] if impart_data is not None else 0
    impart_mp_per = impart_data['impart_mp_per'] if impart_data is not None else 0
    impart_know_per = impart_data['impart_know_per'] if impart_data is not None else 0
    impart_burst_per = impart_data['impart_burst_per'] if impart_data is not None else 0
    boss_atk = impart_data['boss_atk'] if impart_data is not None else 0
    weapon_critatk_data = UserBuffDate(user_id).get_user_weapon_data()  # 我的状态武器会心伤害
    weapon_critatk = weapon_critatk_data['critatk'] if weapon_critatk_data is not None else 0  # 我的状态武器会心伤害
    user_main_critatk = UserBuffDate(user_id).get_user_main_buff_data()  # 我的状态功法会心伤害
    main_critatk = user_main_critatk['critatk'] if user_main_critatk is not None else 0  # 我的状态功法会心伤害
    # leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    # number = user_main_critatk["number"] if user_main_critatk is not None else 0

    level_rate = Decimal(str(level_rate))
    user_maxR = Decimal(str(user_maxR))
    realm_rate = Decimal(str(realm_rate))
    main_buff_rate_buff = Decimal(str(main_buff_rate_buff))
    total_poxian_percent = Decimal(str(total_poxian_percent))
    crit_buff = Decimal(str(crit_buff))
    impart_know_per = Decimal(str(impart_know_per))
    armor_crit_buff = Decimal(str(armor_crit_buff))
    main_crit_buff = Decimal(str(main_crit_buff))
    impart_burst_per = Decimal(str(impart_burst_per))
    weapon_critatk = Decimal(str(weapon_critatk))
    main_critatk = Decimal(str(main_critatk))
    main_hp_buff = Decimal(str(main_hp_buff))
    impart_hp_per = Decimal(str(impart_hp_per))
    main_mp_buff = Decimal(str(main_mp_buff))
    impart_mp_per = Decimal(str(impart_mp_per))
    user_hp = Decimal(user_msg['hp'])
    user_exp = Decimal(user_msg['exp'])
    user_maxH = Decimal(user_maxH)
    msg = f"""      
道号：{user_msg['user_name']}               
气血:{number_to(((user_hp * (1 + main_hp_buff + impart_hp_per)) + user_maxH) * (1 + total_poxian_percent / 100))}/{number_to(int(((user_exp / 2) * (1 + main_hp_buff + impart_hp_per) + user_maxH) * (1 + total_poxian_percent / 100)))}({((((user_hp * (1 + main_hp_buff + impart_hp_per)) + user_maxH) / (((user_exp / 2) * (1 + main_hp_buff + impart_hp_per)) + user_maxH))) * 100:.2f}%)
真元:{number_to(((user_msg['mp'] * (1 + main_mp_buff + impart_mp_per)) + user_maxM) * (1 + total_poxian_percent / 100))}/{number_to(((user_msg['exp'] * (1 + main_mp_buff + impart_mp_per)) + user_maxM) * (1 + total_poxian_percent / 100))}({((((user_msg['mp'] * (1 + main_mp_buff + impart_mp_per)) + user_maxM) / ((user_msg['exp'] * (1 + main_mp_buff + impart_mp_per)) + user_maxM)) * 100):.2f}%)
攻击:{number_to((user_msg['atk'] + user_maxA) * (1 + total_poxian_percent / 100))}
破限增幅: {total_poxian_percent}%
攻击修炼:{user_msg['atkpractice']}级(提升攻击力{user_msg['atkpractice'] * 4}%)
修炼效率:{int((((level_rate + user_maxR) * realm_rate) * (1 + main_buff_rate_buff)) * 100 * (1 + total_poxian_percent / 100))}%
会心:{round((crit_buff + impart_know_per * 100 + armor_crit_buff + main_crit_buff) * (1 + total_poxian_percent / 100), 1)}%
减伤率:{def_buff + weapon_def + main_def}%
boss战增益:{int(boss_atk * 100 * (1 + total_poxian_percent / 100))}%
会心伤害增益:{int((Decimal('1.5') + impart_burst_per + weapon_critatk + main_critatk) * 100 * (1 + total_poxian_percent / 100))}%
"""
    sql_message.update_last_check_info_time(user_id)
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await mind_state.finish()

@del_exp_decimal.handle(parameterless=[Cooldown(at_sender=False)])
async def del_exp_decimal_(bot: Bot, event: GroupMessageEvent):
    """清除修为浮点数"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await del_exp_decimal.finish()
    user_id = user_info['user_id']
    exp = user_info['exp']
    sql_message.del_exp_decimal(user_id, exp)
    msg = f"黑暗动乱暂时抑制成功！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await del_exp_decimal.finish()


@my_exp_num.handle(parameterless=[Cooldown(at_sender=False)])
async def my_exp_num_(bot: Bot, event: GroupMessageEvent):
    """我的双修次数"""
    global two_exp_limit
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await my_exp_num.finish()
    user_id = user_info['user_id']
    limt = two_exp_cd.find_user(user_id)
    impart_data = xiuxian_impart.get_user_info_with_id(user_id)
    impart_two_exp = impart_data['impart_two_exp'] if impart_data is not None else 0

    main_two_data = UserBuffDate(user_id).get_user_main_buff_data()
    main_two = main_two_data['two_buff'] if main_two_data is not None else 0

    num = (two_exp_limit + impart_two_exp + main_two) - limt
    if num <= 0:
        num = 0
    msg = f"道友剩余双修次数{num}次！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await my_exp_num.finish()
