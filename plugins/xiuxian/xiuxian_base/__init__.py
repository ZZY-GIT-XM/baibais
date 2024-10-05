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

run_xiuxian = on_fullmatch("我要修仙", priority=8, permission=GROUP, block=True)
restart = on_fullmatch("洗髓伐骨", permission=GROUP, priority=7, block=True)
rank = on_command("排行榜",
                  aliases={"排行榜列表", "灵石排行榜", "战力排行榜", "境界排行榜", "宗门排行榜", "轮回排行榜"},
                  priority=7, permission=GROUP, block=True)
remaname = on_command("改名", priority=5, permission=GROUP, block=True)
level_up = on_fullmatch("突破", priority=6, permission=GROUP, block=True)
level_up_dr = on_fullmatch("渡厄突破", priority=7, permission=GROUP, block=True)
level_up_drjd = on_command("渡厄金丹突破", aliases={"金丹突破"}, priority=7, permission=GROUP, block=True)
level_up_zj = on_command("直接突破", aliases={"破"}, priority=7, permission=GROUP, block=True)
give_stone = on_command("送灵石", priority=5, permission=GROUP, block=True)
steal_stone = on_command("偷灵石", aliases={"飞龙探云手"}, priority=4, permission=GROUP, block=True)
rob_stone = on_command("抢劫", aliases={"抢灵石", "拿来吧你"}, priority=5, permission=GROUP, block=True)
user_leveluprate = on_command('我的突破概率', aliases={'突破概率'}, priority=5, permission=GROUP, block=True)


@run_xiuxian.handle(parameterless=[Cooldown(at_sender=False)])
async def run_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """我要修仙 加入修仙"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    # 生成随机名字和性别
    user_name, user_sex = read_random_entry_from_file()
    root, root_type = XiuxianJsonDate().linggen_get()  # 获取灵根，灵根类型
    rate = sql_message.get_root_rate(root_type)  # 灵根倍率
    power = 100 * float(rate)  # 战力=境界的power字段 * 灵根的rate字段
    create_time = str(datetime.now())  # 正确地获取当前时间
    is_new_user, msg = sql_message.create_user(
        user_id, root, root_type, int(power), create_time, user_name
    )
    sql_message.update_user_gender(user_id, user_sex)  # 更新用户性别
    try:
        if is_new_user:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            isUser, user_msg, _ = check_user(event)
            if user_msg and ('hp' in user_msg) and (user_msg['hp'] is None or user_msg['hp'] == 0):
                sql_message.update_user_hp(user_id)
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    except ActionFailed:
        await run_xiuxian.finish("修仙界网络堵塞，发送失败！", reply_message=True)


@restart.handle(parameterless=[Cooldown(at_sender=False)])
async def restart_(bot: Bot, event: GroupMessageEvent, state: T_State):
    """洗髓伐骨 刷新灵根信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    # 限制灵根集合
    unique_linggens = {"轮回道果", "真·轮回道果"}
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await restart.finish()

    if user_info['stone'] < XiuConfig().remake:
        await bot.send_group_msg(group_id=int(send_group_id), message="你的灵石还不够呢，快去赚点灵石吧！")
        await restart.finish()

    state["user_id"] = user_info['user_id']

    # 检查当前灵根是否为绝世灵根
    current_root_type = user_info.get('root_type', '')  # 假设 user_info 中有 'root_type' 字段
    if current_root_type in unique_linggens:
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"您的灵根已为当世无上灵根之一：{current_root_type}，无法更换。")
        await restart.finish()
    # 随机获得一个灵根
    name, root_type = XiuxianJsonDate().linggen_get()
    msg = f"@{event.sender.nickname}\n逆天之行，重获新生，新的灵根为: {name}，类型为：{root_type}"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)


@rank.handle(parameterless=[Cooldown(at_sender=False)])
async def rank_(bot: Bot, event: GroupMessageEvent):
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
        await rank.finish()

    elif message == "灵石排行榜":
        a_rank = sql_message.stone_top()
        msg = f"✨位面灵石排行榜TOP50✨\n"
        num = 0
        for i in a_rank:
            num += 1
            msg += f"第{num}位  {i[0]}  灵石：{number_to(i[1])}枚\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await rank.finish()

    elif message == "战力排行榜":
        c_rank = sql_message.power_top()
        msg = f"✨位面战力排行榜TOP50✨\n"
        num = 0
        for i in c_rank:
            num += 1
            msg += f"第{num}位  {i[0]}  战力：{number_to(i[1])}\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await rank.finish()

    elif message == "轮回排行榜":
        c_rank = sql_message.poxian_top()
        msg = f"✨位面轮回排行榜TOP50✨\n"
        num = 0
        for i in c_rank:
            num += 1
            msg += f"第{num}位  {i[0]}  轮回：{i[1]}次\n"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await rank.finish()

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
        await rank.finish()


@remaname.handle(parameterless=[Cooldown(at_sender=False)])
async def remaname_(bot: Bot, event: GroupMessageEvent):
    """改名 修改道号"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await remaname.finish()

    user_id = user_info['user_id']
    user_sex = user_info['user_sex']  # 假设 user_info 字典包含用户的性别信息

    try:
        user_name, _ = read_random_entry_from_file(sex=user_sex)  # 生成随机名字
        msg = sql_message.update_user_name(user_id, user_name)  # 更新数据库中的名字记录
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await remaname.finish()
    except ValueError as e:
        await bot.send_group_msg(group_id=int(send_group_id), message=str(e))
        await remaname.finish()


@level_up.handle(parameterless=[Cooldown(stamina_cost=12, at_sender=False)])
async def level_up_(bot: Bot, event: GroupMessageEvent):
    """突破"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up.finish()

    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    user_leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    level_cd = user_msg['level_up_cd']

    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
            sql_message.update_user_stamina(user_id, 12, 1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await level_up.finish()

    level_name = user_msg['level']  # 用户境界
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    items = Items()
    pause_flag = False
    elixir_name = None
    elixir_desc = None

    if user_backs is not None:
        for back in user_backs:
            if int(back['goods_id']) == 1999:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back['goods_name']
                elixir_desc = items.get_data_by_item_id(1999)['desc']
                break

    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    number = main_rate_buff['number'] if main_rate_buff is not None else 0

    if pause_flag:
        msg = f"由于检测到背包有丹药：{elixir_name}，效果：{elixir_desc}，突破已经准备就绪\n请发送 ，【渡厄突破】 或 【直接突破】来选择是否使用丹药突破！\n本次突破概率为：{level_rate + user_leveluprate + number}% "
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up.finish()
    else:
        msg = f"由于检测到背包没有【渡厄丹】，突破已经准备就绪\n请发送，【直接突破】来突破！请注意，本次突破失败将会损失部分修为！\n本次突破概率为：{level_rate + user_leveluprate + number}% "
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up.finish()


@level_up_zj.handle(parameterless=[Cooldown(stamina_cost=6, at_sender=False)])
async def level_up_zj_(bot: Bot, event: GroupMessageEvent):
    """直接突破"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_zj.finish()

    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
            sql_message.update_user_stamina(user_id, 6, 1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await level_up_zj.finish()

    level_name = user_msg['level']  # 用户境界
    exp = user_msg['exp']  # 用户修为
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    main_exp_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破扣修为减少
    exp_buff = main_exp_buff['exp_buff'] if main_exp_buff is not None else 0
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    le = OtherSet().get_type(exp, level_rate + leveluprate + number, level_name)

    if le == "失败":
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        # 失败惩罚，随机扣减修为
        percentage = random.randint(XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit)
        now_exp = Decimal(str(int(exp) * ((percentage / 100) * (1 - exp_buff))))  # 功法突破扣修为减少
        # 更新用户修为
        sql_message.update_j_exp(user_id, now_exp)
        # 将所有数值转换为 Decimal 类型
        user_msg['hp'] = Decimal(str(user_msg['hp']))
        user_msg['mp'] = Decimal(str(user_msg['mp']))
        now_exp = Decimal(str(now_exp))
        # 更新 HP
        nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else Decimal('1')
        # 更新 MP
        nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else Decimal('1')
        sql_message.update_user_hp_mp(user_id, nowhp, nowmp)  # 修为掉了，血量、真元也要掉
        update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
            level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
        sql_message.update_levelrate(user_id, leveluprate + update_rate)
        msg = f"道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_zj.finish()

    elif type(le) == list:
        # 突破成功
        sql_message.updata_level(user_id, le[0])  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        msg = f"恭喜道友突破{le[0]}成功！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_zj.finish()

    else:
        # 最高境界
        msg = le
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_zj.finish()


@level_up_drjd.handle(parameterless=[Cooldown(stamina_cost=4, at_sender=False)])
async def level_up_drjd_(bot: Bot, event: GroupMessageEvent):
    """渡厄 金丹 突破"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_drjd.finish()

    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
            sql_message.update_user_stamina(user_id, 4, 1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await level_up_drjd.finish()

    elixir_name = "渡厄金丹"
    level_name = user_msg['level']  # 用户境界
    exp = user_msg['exp']  # 用户修为
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    le = OtherSet().get_type(exp, level_rate + user_leveluprate + number, level_name)
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    pause_flag = False
    if user_backs is not None:
        for back in user_backs:
            if int(back['goods_id']) == 1998:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back['goods_name']
                break

    if not pause_flag:
        msg = f"道友突破需要使用{elixir_name}，但您的背包中没有该丹药！"
        sql_message.update_user_stamina(user_id, 4, 1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_drjd.finish()

    if le == "失败":
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        if pause_flag:
            # 使用丹药减少的sql
            sql_message.update_back_j(user_id, 1998, use_key=1)
            now_exp = int(int(exp) * 0.1)
            sql_message.update_exp(user_id, now_exp)  # 渡厄金丹增加用户修为
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"道友突破失败，但是使用了丹药{elixir_name}，本次突破失败不扣除修为反而增加了一成，下次突破成功率增加{update_rate}%！！"
        else:
            # 失败惩罚，随机扣减修为
            percentage = random.randint(
                XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit
            )
            main_exp_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破扣修为减少
            exp_buff = main_exp_buff['exp_buff'] if main_exp_buff is not None else 0
            now_exp = int(int(exp) * ((percentage / 100) * exp_buff))
            sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
            nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else 1
            nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else 1
            sql_message.update_user_hp_mp(user_id, nowhp, nowmp)  # 修为掉了，血量、真元也要掉
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"没有检测到{elixir_name}，道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_drjd.finish()

    elif type(le) == list:
        # 突破成功
        sql_message.updata_level(user_id, le[0])  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        now_exp = int(int(exp) * 0.1)
        sql_message.update_exp(user_id, now_exp)  # 渡厄金丹增加用户修为
        msg = f"恭喜道友突破{le[0]}成功，因为使用了渡厄金丹，修为也增加了一成！！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_drjd.finish()

    else:
        # 最高境界
        msg = le
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_drjd.finish()


@level_up_dr.handle(parameterless=[Cooldown(stamina_cost=8, at_sender=False)])
async def level_up_dr_(bot: Bot, event: GroupMessageEvent):
    """渡厄 突破"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_dr.finish()

    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
            sql_message.update_user_stamina(user_id, 8, 1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await level_up_dr.finish()

    elixir_name = "渡厄丹"
    level_name = user_msg['level']  # 用户境界
    exp = user_msg['exp']  # 用户修为
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    le = OtherSet().get_type(exp, level_rate + user_leveluprate + number, level_name)
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    pause_flag = False
    if user_backs is not None:
        for back in user_backs:
            if int(back['goods_id']) == 1999:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back['goods_name']
                break

    if not pause_flag:
        msg = f"道友突破需要使用{elixir_name}，但您的背包中没有该丹药！"
        sql_message.update_user_stamina(user_id, 8, 1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_dr.finish()

    if le == "失败":
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        if pause_flag:
            # todu，丹药减少的sql
            sql_message.update_back_j(user_id, 1999, use_key=1)
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"道友突破失败，但是使用了丹药{elixir_name}，本次突破失败不扣除修为下次突破成功率增加{update_rate}%，道友不要放弃！"
        else:
            # 失败惩罚，随机扣减修为
            percentage = random.randint(
                XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit
            )
            main_exp_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破扣修为减少
            exp_buff = main_exp_buff['exp_buff'] if main_exp_buff is not None else 0
            now_exp = int(int(exp) * ((percentage / 100) * (1 - exp_buff)))
            sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
            nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else 1
            nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else 1
            sql_message.update_user_hp_mp(user_id, nowhp, nowmp)  # 修为掉了，血量、真元也要掉
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"没有检测到{elixir_name}，道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_dr.finish()

    elif type(le) == list:
        # 突破成功
        sql_message.updata_level(user_id, le[0])  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        msg = f"恭喜道友突破{le[0]}成功"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_dr.finish()

    else:
        # 最高境界
        msg = le
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_dr.finish()


@user_leveluprate.handle(parameterless=[Cooldown(at_sender=False)])
async def user_leveluprate_(bot: Bot, event: GroupMessageEvent):
    """我的突破概率"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await user_leveluprate.finish()

    user_id = user_info['user_id']
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    level_name = user_msg['level']  # 用户境界
    level_rate = jsondata.level_rate_data()[level_name]  #
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()  # 功法突破概率提升
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    msg = f"道友下一次突破成功概率为{level_rate + leveluprate + number}%"

    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await user_leveluprate.finish()


@give_stone.handle(parameterless=[Cooldown(at_sender=False)])
async def give_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """送灵石"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await give_stone.finish()

    user_id = user_info['user_id']
    user_stone_num = user_info['stone']
    msg = args.extract_plain_text().strip()
    stone_num = re.findall(r"\d+", msg)  # 灵石数
    nick_name = re.findall(r"\D+", msg)  # 道号

    if not stone_num:
        msg = f"请输入正确的灵石数量！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await give_stone.finish()

    give_stone_num = stone_num[0]
    if int(give_stone_num) > int(user_stone_num):
        msg = f"道友的灵石不够，请重新输入！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await give_stone.finish()

    if nick_name:
        give_message = sql_message.get_user_info_with_name(nick_name[0].strip())
        if give_message:
            if give_message['user_name'] == user_info['user_name']:
                msg = f"请不要送灵石给自己！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await give_stone.finish()
            else:
                sql_message.update_ls(user_id, give_stone_num, 2)  # 减少用户灵石
                give_stone_num2 = int(give_stone_num) * 0.1
                num = int(give_stone_num) - int(give_stone_num2)
                sql_message.update_ls(give_message['user_id'], num, 1)  # 增加用户灵石
                msg = f"{user_info['user_name']} 共赠送{number_to(int(give_stone_num))}枚灵石给{give_message['user_name']}道友！收取手续费{int(give_stone_num2)}枚"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await give_stone.finish()
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await give_stone.finish()

    else:
        msg = f"未获取到对方信息，请输入正确的道号！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await give_stone.finish()


@steal_stone.handle(parameterless=[Cooldown(stamina_cost=10, at_sender=False)])
async def steal_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """偷灵石"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await steal_stone.finish()

    user_id = user_info['user_id']
    user_stone_num = user_info['stone']
    coststone_num = XiuConfig().tou
    if int(coststone_num) > int(user_stone_num):
        msg = f"道友的偷窃准备(灵石)不足，请打工之后再切格瓦拉！"
        sql_message.update_user_stamina(user_id, 10, 1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await steal_stone.finish()

    # 从命令参数中提取道号
    msg = args.extract_plain_text().strip()
    nick_name = re.findall(r"\D+", msg)

    if nick_name:
        steal_user = sql_message.get_user_info_with_name(nick_name[0].strip())
        if steal_user:
            steal_user_id = steal_user['user_id']
            steal_user_stone = steal_user['stone']

            if steal_user_id == user_id:
                msg = f"{user_info['user_name']} 请不要偷自己刷成就！"
                sql_message.update_user_stamina(user_id, 10, 1)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await steal_stone.finish()

            steal_success = random.randint(0, 100)
            result = OtherSet().get_power_rate(user_info['power'], steal_user['power'])

            if isinstance(result, int):
                if int(steal_success) > result:
                    sql_message.update_ls(user_id, coststone_num, 2)  # 减少手续费
                    sql_message.update_ls(steal_user_id, coststone_num, 1)  # 增加被偷的人的灵石
                    msg = f"{user_info['user_name']} 道友偷窃失手了，被对方发现并被派去华哥厕所义务劳工！赔款{coststone_num}灵石"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await steal_stone.finish()

                get_stone = random.randint(int(XiuConfig().tou_lower_limit * steal_user_stone),
                                           int(XiuConfig().tou_upper_limit * steal_user_stone))
                if int(get_stone) > int(steal_user_stone):
                    sql_message.update_ls(user_id, steal_user_stone, 1)  # 增加偷到的灵石
                    sql_message.update_ls(steal_user_id, steal_user_stone, 2)  # 减少被偷的人的灵石
                    msg = f"{steal_user['user_name']}道友已经被榨干了~"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await steal_stone.finish()
                else:
                    sql_message.update_ls(user_id, get_stone, 1)  # 增加偷到的灵石
                    sql_message.update_ls(steal_user_id, get_stone, 2)  # 减少被偷的人的灵石
                    msg = f"共偷取{steal_user['user_name']}道友{number_to(get_stone)}枚灵石！"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await steal_stone.finish()
            else:
                msg = result
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await steal_stone.finish()
        else:
            msg = f"对方未踏入修仙界，不要对杂修出手！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await steal_stone.finish()
    else:
        msg = f"未获取到对方信息，请输入正确的道号！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await steal_stone.finish()


@rob_stone.handle(parameterless=[Cooldown(stamina_cost=15, at_sender=False)])
async def rob_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """抢灵石"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await rob_stone.finish()

    user_id = user_info["user_id"]
    user_mes = sql_message.get_user_info_with_id(user_id)

    # 获取命令参数
    args_str = args.extract_plain_text().strip()
    give_name = None  # 用于存储用户名称

    # 检查是否有用户名称输入
    if args_str:
        give_name = args_str.split()[0]

    player1 = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None, '爆伤': None,
               '防御': 0}
    player2 = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None, '爆伤': None,
               '防御': 0}

    user_2 = sql_message.get_user_info_with_name(give_name) if give_name else None
    if user_mes and user_2:
        if user_info['root'] == "器师":
            msg = f"目前职业无法抢劫！"
            sql_message.update_user_stamina(user_id, 15, 1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await rob_stone.finish()

        if give_name:
            if str(user_2['user_id']) == str(user_id):
                msg = f"请不要抢自己刷成就！"
                sql_message.update_user_stamina(user_id, 15, 1)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            if user_2['root'] == "器师":
                msg = f"对方职业无法被抢劫！"
                sql_message.update_user_stamina(user_id, 15, 1)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            if Items().convert_rank(user_2['level'])[0] - Items().convert_rank(user_info['level'])[0] >= 12:
                msg = f"道友抢劫小辈，可耻！"
                sql_message.update_user_stamina(user_id, 15, 1)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            if user_2['hp'] <= user_2['exp'] / 10:
                time_2 = leave_harm_time(user_2['user_id'])
                msg = f"对方重伤藏匿了，无法抢劫！距离对方脱离生命危险还需要{time_2}分钟！"
                sql_message.update_user_stamina(user_id, 15, 1)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            if user_info['hp'] <= user_info['exp'] / 10:
                time_msg = leave_harm_time(user_id)
                msg = f"重伤未愈，动弹不得！距离脱离生命危险还需要{time_msg}分钟！"
                msg += f"请道友进行闭关，或者使用药品恢复气血，不要干等，没有自动回血！！！"
                sql_message.update_user_stamina(user_id, 15, 1)
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            # 破限增幅计算
            poxian_num1 = user_info['poxian_num']
            poxian_num2 = user_2['poxian_num']

            total_poxian_percent1 = min(poxian_num1 * 10, 10 * 10 + (poxian_num1 - 10) * 20)
            total_poxian_percent2 = min(poxian_num2 * 10, 10 * 10 + (poxian_num2 - 10) * 20)

            # 获取轮回点数
            user1_cultEff = user_info['cultEff'] / 100
            user1_seclEff = user_info['seclEff'] / 100
            user1_maxR = user_info['maxR'] / 100
            user1_maxH = user_info['maxH'] * 100000
            user1_maxM = user_info['maxM'] * 100000
            user1_maxA = user_info['maxA'] * 10000

            # 获取轮回点数
            user2_cultEff = user_2['cultEff'] / 100
            user2_seclEff = user_2['seclEff'] / 100
            user2_maxR = user_2['maxR'] / 100
            user2_maxH = user_2['maxH'] * 100000
            user2_maxM = user_2['maxM'] * 100000
            user2_maxA = user_2['maxA'] * 10000

            # 应用破限增幅
            atk_with_poxian1 = (user_info['atk'] + user1_maxA) * (1 + total_poxian_percent1 / 100)
            atk_with_poxian2 = (user_2['atk'] + user2_maxA) * (1 + total_poxian_percent2 / 100)
            hp_with_poxian1 = (user_info['hp'] + user1_maxH) * (1 + total_poxian_percent1 / 100)
            hp_with_poxian2 = (user_2['hp'] + user2_maxH) * (1 + total_poxian_percent2 / 100)
            mp_with_poxian1 = (user_info['mp'] + user1_maxM) * (1 + total_poxian_percent1 / 100)
            mp_with_poxian2 = (user_2['mp'] + user2_maxM) * (1 + total_poxian_percent2 / 100)

            # 设置玩家数据
            player1['user_id'] = user_info['user_id']
            player1['道号'] = user_info['user_name']
            player1['气血'] = hp_with_poxian1
            player1['攻击'] = atk_with_poxian1
            player1['真元'] = mp_with_poxian1
            player1['会心'] = int((0.01 + (xiuxian_impart.get_user_info_with_id(user_id)[
                                               'impart_know_per'] if xiuxian_impart.get_user_info_with_id(
                user_id) is not None else 0)) * 100 * (1 + total_poxian_percent1 / 100))
            player1['爆伤'] = int((1.5 + (xiuxian_impart.get_user_info_with_id(user_id)[
                                              'impart_burst_per'] if xiuxian_impart.get_user_info_with_id(
                user_id) is not None else 0)) * (1 + total_poxian_percent1 / 100))
            user_buff_data = UserBuffDate(user_id)
            user_armor_data = user_buff_data.get_user_armor_buff_data()
            if user_armor_data is not None:
                def_buff = int(user_armor_data['def_buff'])
            else:
                def_buff = 0
            player1['防御'] = def_buff * (1 + total_poxian_percent1 / 100)

            player2['user_id'] = user_2['user_id']
            player2['道号'] = user_2['user_name']
            player2['气血'] = hp_with_poxian2
            player2['攻击'] = atk_with_poxian2
            player2['真元'] = mp_with_poxian2
            player2['会心'] = int((0.01 + (xiuxian_impart.get_user_info_with_id(user_2['user_id'])[
                                               'impart_know_per'] if xiuxian_impart.get_user_info_with_id(
                user_2['user_id']) is not None else 0)) * 100 * (1 + total_poxian_percent2 / 100))
            player2['爆伤'] = int((1.5 + (xiuxian_impart.get_user_info_with_id(user_2['user_id'])[
                                              'impart_burst_per'] if xiuxian_impart.get_user_info_with_id(
                user_2['user_id']) is not None else 0)) * (1 + total_poxian_percent2 / 100))
            user_buff_data = UserBuffDate(user_2['user_id'])
            user_armor_data = user_buff_data.get_user_armor_buff_data()
            if user_armor_data is not None:
                def_buff = int(user_armor_data['def_buff'])
            else:
                def_buff = 0
            player2['防御'] = def_buff * (1 + total_poxian_percent2 / 100)

            result, victor = OtherSet().player_fight(player1, player2)
            await send_msg_handler(bot, event, '决斗场', bot.self_id, result)
            if victor == player1['道号']:
                foe_stone = user_2['stone']
                if foe_stone > 0:
                    sql_message.update_ls(user_id, int(foe_stone * 0.1), 1)
                    sql_message.update_ls(user_2['user_id'], int(foe_stone * 0.1), 2)
                    exps = int(user_2['exp'] * 0.005)
                    sql_message.update_exp(user_id, exps)
                    sql_message.update_j_exp(user_2['user_id'], exps / 2)
                    msg = f"大战一番，战胜对手，获取灵石{number_to(foe_stone * 0.1)}枚，修为增加{number_to(exps)}，对手修为减少{number_to(exps / 2)}"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()
                else:
                    exps = int(user_2['exp'] * 0.005)
                    sql_message.update_exp(user_id, exps)
                    sql_message.update_j_exp(user_2['user_id'], exps / 2)
                    msg = f"大战一番，战胜对手，结果对方是个穷光蛋，修为增加{number_to(exps)}，对手修为减少{number_to(exps / 2)}"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()

            elif victor == player2['道号']:
                mind_stone = user_info['stone']
                if mind_stone > 0:
                    sql_message.update_ls(user_id, int(mind_stone * 0.1), 2)
                    sql_message.update_ls(user_2['user_id'], int(mind_stone * 0.1), 1)
                    exps = int(user_info['exp'] * 0.005)
                    sql_message.update_j_exp(user_id, exps)
                    sql_message.update_exp(user_2['user_id'], exps / 2)
                    msg = f"大战一番，被对手反杀，损失灵石{number_to(mind_stone * 0.1)}枚，修为减少{number_to(exps)}，对手获取灵石{number_to(mind_stone * 0.1)}枚，修为增加{number_to(exps / 2)}"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()
                else:
                    exps = int(user_info['exp'] * 0.005)
                    sql_message.update_j_exp(user_id, exps)
                    sql_message.update_exp(user_2['user_id'], exps / 2)
                    msg = f"大战一番，被对手反杀，修为减少{number_to(exps)}，对手修为增加{number_to(exps / 2)}"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()

            else:
                msg = f"发生错误，请检查后台！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

    else:
        msg = f"对方未踏入修仙界，不可抢劫！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await rob_stone.finish()


