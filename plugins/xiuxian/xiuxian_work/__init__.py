import os
from typing import Any, Tuple, Dict
from nonebot import on_regex, require, on_command
from nonebot.params import RegexGroup
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent,
    MessageSegment
)
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage, OtherSet
from .work_handle import workhandle
from datetime import datetime
from ..xiuxian_utils.xiuxian_opertion import do_is_work
from ..xiuxian_utils.utils import check_user, check_user_type, get_msg_pic
from .reward_data_source import PLAYERSDATA
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.item_database_handler import Items

# 定时任务
work = {}  # 悬赏令信息记录
refreshnum: Dict[str, int] = {}  # 用户悬赏令刷新次数记录
sql_message = XiuxianDateManage()  # sql类
items = Items()
lscost = 10000000000  # 刷新灵石消耗
count = 3  # 免费次数

last_work = on_command("最后的悬赏令", priority=15, block=True)
do_work = on_regex(
    r"^悬赏令(刷新|终止|结算|接取|帮助)?(\d+)?",
    priority=10,
    permission=GROUP,
    block=True
)


@last_work.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
async def last_work_(bot: Bot, event: GroupMessageEvent):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await last_work.finish()
    user_id = user_info['user_id']
    user_level = user_info['level']
    user_rank = Items().convert_rank(user_level)[0]
    is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
    if (is_type and user_rank <= 11) or (
            is_type and user_info['exp'] >= sql_message.get_level_power("金仙境圆满")) or (
            is_type and int(user_info['exp']) >= int(
        OtherSet().set_closing_type(user_level)) * XiuConfig().closing_exp_upper_limit
    ):
        user_cd_message = sql_message.get_user_cd(user_id)
        work_time = datetime.strptime(
            user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f"
        )
        exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
        time2 = workhandle().do_work(
            # key=1, name=user_cd_message.scheduled_time  修改点
            key=1, name=user_cd_message['scheduled_time'], level=user_level, exp=user_info['exp'],
            user_id=user_info['user_id']
        )
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await last_work.finish()
        else:
            msg, give_stone, s_o_f, item_id, big_suc = workhandle().do_work(
                2,
                work_list=user_cd_message['scheduled_time'],
                level=user_level,
                exp=user_info['exp'],
                user_id=user_info['user_id']
            )
            item_flag = False
            item_msg = None
            item_info = None
            if item_id != 0:
                item_flag = True
                item_info = items.get_data_by_item_id(item_id)
                item_msg = f"{item_info['level']}:{item_info['name']}"
            if big_suc:  # 大成功
                sql_message.update_ls(user_id, give_stone * 2, 1)
                sql_message.do_work(user_id, 0)
                msg = f"悬赏令结算，{msg}获得报酬{give_stone * 2}枚灵石"
                # todo 战利品结算sql
                if item_flag:
                    sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                    msg += f"，额外获得奖励：{item_msg}!"
                else:
                    msg += "!"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await last_work.finish()

            else:
                sql_message.update_ls(user_id, give_stone, 1)
                sql_message.do_work(user_id, 0)
                msg = f"悬赏令结算，{msg}获得报酬{give_stone}枚灵石"
                if s_o_f:  # 普通成功
                    if item_flag:
                        sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                        msg += f"，额外获得奖励：{item_msg}!"
                    else:
                        msg += "!"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await last_work.finish()

                else:  # 失败
                    msg += "!"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await last_work.finish()
    else:
        msg = "不满足使用条件！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await last_work.finish()


@do_work.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
async def do_work_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_level = "轮回境初期"
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    user_level_sx = user_info['level']
    user_id = user_info['user_id']
    user_rank = Items().convert_rank(user_info['level'])[0]
    sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    user_cd_message = sql_message.get_user_cd(user_id)
    if not os.path.exists(PLAYERSDATA / str(user_id) / "workinfo.json") and user_cd_message['type'] == 2:
        sql_message.do_work(user_id, 0)
        msg = "悬赏令已更新，已重置道友的状态！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    mode = args[0]  # 刷新、终止、结算、接取
    if user_rank <= Items().convert_rank('轮回境初期')[0] or user_info['exp'] >= sql_message.get_level_power(
            user_level):
        msg = "道友的境界已过创业的初期，悬赏令已经不能满足道友了！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    user_level = user_info['level']
    if int(user_info['exp']) >= int(OtherSet().set_closing_type(user_level)) * XiuConfig().closing_exp_upper_limit:
        # 获取下个境界需要的修为 * 1.5为闭关上限
        msg = "道友的修为已经到达上限，悬赏令已无法再获得经验！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    if user_cd_message['type'] == 1:
        msg = "已经在闭关中，请输入【出关】结束后才能获取悬赏令！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    if user_cd_message['type'] == 3:
        msg = "道友在秘境中，请等待结束后才能获取悬赏令！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    if user_cd_message['type'] == 4:
        now_time = datetime.now()
        in_closing_time = datetime.strptime(
            user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f"
        )  # 预计修炼结束的时间
        seconds_diff = (in_closing_time - now_time).total_seconds()
        remaining_seconds = int(seconds_diff)
        if remaining_seconds > 0:
            msg = f"道友正在修炼中，还剩 {remaining_seconds} 秒结束修炼！"
        else:
            # 如果修炼已经结束，更新状态
            sql_message.in_closing(user_id, 0)
            msg = "修炼已结束，请重新刷新悬赏令！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()

    if mode is None:  # 接取逻辑
        if (user_cd_message['scheduled_time'] is None) or (user_cd_message['type'] == 0):
            try:
                msg = work[user_id].msg
            except KeyError:
                msg = "没有查到你的悬赏令信息呢，请刷新！"
        elif user_cd_message['type'] == 2:
            create_time = user_cd_message['create_time']
            # 检查 create_time 是否为 datetime 类型
            if isinstance(create_time, datetime):
                # 如果是 datetime 类型，转换为字符串
                create_time_str = create_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            else:
                # 假设 create_time 已经是一个字符串
                create_time_str = create_time
            # 使用转换后的字符串进行解析
            work_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S.%f")
            exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
            time2 = workhandle().do_work(key=1, name=user_cd_message['scheduled_time'], user_id=user_info['user_id'])
            if exp_time < time2:
                msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
            else:
                msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，已结束，请输入【悬赏令结算】结算任务信息！"
        else:
            msg = "状态未知错误！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()

    if mode == "刷新":  # 刷新逻辑
        stone_use = 0  # 悬赏令刷新提示是否扣灵石
        if user_cd_message['type'] == 2:
            create_time = user_cd_message['create_time']
            # 检查 create_time 是否为 datetime 类型
            if isinstance(create_time, datetime):
                # 如果是 datetime 类型，转换为字符串
                create_time_str = create_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            else:
                # 假设 create_time 已经是一个字符串
                create_time_str = create_time
            # 使用转换后的字符串进行解析
            work_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S.%f")
            exp_time = (datetime.now() - work_time).seconds // 60
            time2 = workhandle().do_work(key=1, name=user_cd_message['scheduled_time'], user_id=user_info['user_id'])
            if exp_time < time2:
                msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
            else:
                msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，已结束，请输入【悬赏令结算】结算任务信息！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await do_work.finish()
        usernums = sql_message.get_work_num(user_id)

        isUser, user_info, msg = check_user(event)
        if not isUser:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await do_work.finish()

        freenum = count - usernums - 1
        if freenum < 0:
            freenum = 0
            if int(user_info['stone']) < int(lscost / Items().convert_rank(user_level_sx)[0]):
                msg = f"道友的灵石不足以刷新，下次刷新消耗灵石：{int(lscost / Items().convert_rank(user_level_sx)[0])}枚"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await do_work.finish()
            else:
                sql_message.update_ls(user_id, int(lscost / Items().convert_rank(user_level_sx)[0]), 2)
                stone_use = 1

        work_msg = workhandle().do_work(0, level=user_level, exp=user_info['exp'], user_id=user_id)
        n = 1
        work_list = []
        work_msg_f = f"☆------道友的个人悬赏令------☆\n"
        for i in work_msg:
            work_list.append([i[0], i[3]])
            work_msg_f += f"{n}、{get_work_msg(i)}"
            n += 1
        work_msg_f += f"(悬赏令每日免费刷新次数：{count}，超过{count}次后，下次刷新消耗灵石{int(lscost / Items().convert_rank(user_level_sx)[0])},今日可免费刷新次数：{freenum}次)"
        if int(stone_use) == 1:
            work_msg_f += f"\n道友消耗灵石{int(lscost / Items().convert_rank(user_level_sx)[0])}枚，成功刷新悬赏令"
        work[user_id] = do_is_work(user_id)
        work[user_id].msg = work_msg_f
        work[user_id].world = work_list
        sql_message.update_work_num(user_id, usernums + 1)
        msg = work[user_id].msg
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()

    elif mode == "终止":
        is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
        if is_type:
            stone = 4000000
            sql_message.update_ls(user_id, stone, 2)
            sql_message.do_work(user_id, 0)
            msg = f"道友不讲诚信，被打了一顿灵石减少{stone},悬赏令已终止！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await do_work.finish()
        else:
            msg = "没有查到你的悬赏令信息呢，请刷新！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await do_work.finish()

    elif mode == "结算":
        is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
        if is_type:
            user_cd_message = sql_message.get_user_cd(user_id)
            create_time = user_cd_message['create_time']
            # 检查 create_time 是否为 datetime 类型
            if isinstance(create_time, datetime):
                # 如果是 datetime 类型，转换为字符串
                create_time_str = create_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            else:
                # 假设 create_time 已经是一个字符串
                create_time_str = create_time
            # 使用转换后的字符串进行解析
            work_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S.%f")

            exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
            time2 = workhandle().do_work(
                key=1, name=user_cd_message['scheduled_time'], level=user_level, exp=user_info['exp'],
                user_id=user_info['user_id']
            )
            if exp_time < time2:
                msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await do_work.finish()
            else:
                msg, give_exp, s_o_f, item_id, big_suc = workhandle().do_work(2,
                                                                              work_list=user_cd_message[
                                                                                  'scheduled_time'],
                                                                              level=user_level,
                                                                              exp=user_info['exp'],
                                                                              user_id=user_info['user_id'])
                item_flag = False
                item_info = None
                item_msg = None
                if item_id != 0:
                    item_flag = True
                    item_info = items.get_data_by_item_id(item_id)
                    item_msg = f"{item_info['level']}:{item_info['name']}"
                if big_suc:  # 大成功
                    sql_message.update_exp(user_id, give_exp * 2)
                    sql_message.do_work(user_id, 0)
                    msg = f"悬赏令结算，{msg}增加修为{give_exp * 2}"
                    # todo 战利品结算sql
                    if item_flag:
                        sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                        msg += f"，额外获得奖励：{item_msg}!"
                    else:
                        msg += "!"

                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await do_work.finish()

                else:
                    sql_message.update_exp(user_id, give_exp)
                    sql_message.do_work(user_id, 0)
                    msg = f"悬赏令结算，{msg}增加修为{give_exp}"
                    if s_o_f:  # 普通成功
                        if item_flag:
                            sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                            msg += f"，额外获得奖励：{item_msg}!"
                        else:
                            msg += "!"
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await do_work.finish()

                    else:  # 失败
                        msg += "!"
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await do_work.finish()
        else:
            msg = "没有查到你的悬赏令信息呢，请刷新！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await do_work.finish()

    elif mode == "接取":
        num = args[1]
        is_type, msg = check_user_type(user_id, 0)  # 需要无状态的用户
        if is_type:  # 接取逻辑
            if num is None or str(num) not in ['1', '2', '3']:
                msg = '请输入正确的任务序号'
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await do_work.finish()
            work_num = 1
            try:
                if work[user_id]:
                    work_num = int(num)  # 任务序号
                try:
                    get_work = work[user_id].world[work_num - 1]
                    sql_message.do_work(user_id, 2, get_work[0])
                    del work[user_id]
                    msg = f"接取任务【{get_work[0]}】成功"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await do_work.finish()

                except IndexError:
                    msg = "没有这样的任务"
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await do_work.finish()

            except KeyError:
                msg = "没有查到你的悬赏令信息呢，请刷新！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await do_work.finish()
        else:
            msg = "没有查到你的悬赏令信息呢，请刷新！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await do_work.finish()


def get_work_msg(work_):
    msg = f"{work_[0]},完成机率{work_[1]},基础报酬{work_[2]}修为,预计需{work_[3]}分钟{work_[4]}\n"
    return msg
