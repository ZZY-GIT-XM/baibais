import re

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    GroupMessageEvent,
    ActionFailed
)
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from ..xiuxian_utils.item_database_handler import Items
from ..xiuxian_utils.lay_out import assign_bot, Cooldown, assign_bot_group
from ..xiuxian_utils.utils import (
    number_to, check_user
)
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, XIUXIAN_IMPART_BUFF
)

items = Items()

# 定时任务
cache_help = {}
cache_level_help = {}
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()

admin_add_lingshi = on_command("神秘力量", permission=SUPERUSER, priority=10, block=True)
admin_add_jiejing = on_command("天外力量", permission=SUPERUSER, priority=10, block=True)
admin_update_linggen = on_command("轮回力量", permission=SUPERUSER, priority=10, block=True)
admin_add_wupin = on_command('创造力量', permission=SUPERUSER, priority=15, block=True)
admin_clear_back = on_command('毁灭力量', permission=SUPERUSER, priority=15, block=True)
admin_restate_user = on_command("重置状态", permission=SUPERUSER, priority=12, block=True)
admin_recover_stamina = on_command("恢复体力", permission=SUPERUSER, priority=12, block=True)

@admin_clear_back.handle(parameterless=[Cooldown(at_sender=False)])
async def admin_clear_back_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """毁灭力量 清空指定用户的背包数据"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip()

    if not msg:
        msg = f"请输入正确指令！例如：清空背包 [user_id]"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_clear_back.finish()

    user_id = msg.strip()

    if not user_id.isdigit():
        msg = f"用户ID必须为数字！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_clear_back.finish()

    user_id = int(user_id)
    user_info = sql_message.get_user_info_with_id(user_id)
    if not user_info:
        msg = f"用户ID {user_id} 不存在！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_clear_back.finish()

    result = sql_message.delete_back_by_user_id(user_id)
    if result:
        msg = f"用户ID {user_id} 的背包已成功清空！"
    else:
        msg = f"清空用户ID {user_id} 的背包时发生错误，请检查日志。"

    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await admin_clear_back.finish()


@admin_recover_stamina.handle(parameterless=[CommandArg()])
async def admin_recover_stamina_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """恢复用户体力。
    单用户：恢复体力 [用户名]
    多用户：恢复体力 [未做]"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_recover_stamina.finish()

    # 从命令参数中提取名称
    msg = args.extract_plain_text().strip()
    input_name = re.findall(r"\D+", msg)[0] if msg else ""

    # 根据名称匹配用户
    give_user = sql_message.get_user_info_with_name(input_name)
    if give_user:
        give_qq = give_user['user_id']
        sql_message.update_user_stamina(give_qq, 1000, 1)
        msg = f"用户 {input_name} 体力已恢复！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_recover_stamina.finish()
    else:
        msg = f"未找到用户 {input_name}！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_recover_stamina.finish()


@admin_restate_user.handle(parameterless=[Cooldown(at_sender=False)])
async def admin_restate_user_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """重置用户状态。
    单用户：重置状态 [用户名]
    多用户：重置状态"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_restate_user.finish()

    # 从命令参数中提取名称
    msg = args.extract_plain_text().strip()
    input_name = re.findall(r"\D+", msg)[0] if msg else ""

    if input_name:
        # 根据名称匹配用户
        give_user = sql_message.get_user_info_with_name(input_name)
        if give_user:
            give_qq = give_user['user_id']
            sql_message.restate(give_qq)
            msg = f"用户 {input_name} 信息重置成功！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_restate_user.finish()
        else:
            msg = f"未找到用户 {input_name}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_restate_user.finish()
    else:
        sql_message.restate()
        msg = f"所有用户信息重置成功！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_restate_user.finish()


@admin_add_lingshi.handle(parameterless=[Cooldown(at_sender=False)])
async def admin_add_lingshi_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """GM权限 给用户添加灵石 神秘力量"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    stone_num_match = re.findall(r"\d+", msg_text)  # 提取数字
    nick_name = re.findall(r"\D+", msg_text)  # 道号
    give_stone_num = int(stone_num_match[0]) if stone_num_match else 0  # 默认灵石数为0，如果有提取到数字，则使用提取到的第一个数字

    if nick_name:
        give_user = sql_message.get_user_info_with_name(nick_name[0].strip())
        if give_user:
            sql_message.update_ls(give_user['user_id'], give_stone_num, 1)  # 增加用户灵石
            msg = f"共赠送{number_to(give_stone_num)}枚灵石给{give_user['user_name']}道友！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_add_lingshi.finish()
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_add_lingshi.finish()
    # else:
    #     sql_message.update_ls_all(give_stone_num)
    #     msg = f"全服通告：赠送所有用户{number_to(give_stone_num)}灵石,请注意查收！"
    #     enabled_groups = sql_message.get_enabled_groups()
    #
    #     for group_id in enabled_groups:
    #         bot = await assign_bot_group(group_id=group_id)
    #         try:
    #             await bot.send_group_msg(group_id=int(group_id), message=msg)
    #         except ActionFailed:  # 发送群消息失败
    #             continue
    await admin_add_lingshi.finish()


@admin_add_jiejing.handle(parameterless=[Cooldown(at_sender=False)])
async def admin_add_jiejing_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """GM权限 给用户添加结晶 天外力量 """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    match = re.match(r"(\D+)?(\d+)?", msg_text)
    if match:
        nick_name, crystal_num_str = match.groups()
        give_crystal_num = int(crystal_num_str) if crystal_num_str else 0  # 默认结晶数为0，如果有提取到数字，则使用提取到的第一个数字

        if nick_name:
            give_user = sql_message.get_user_info_with_name(nick_name.strip())
            if give_user:
                xiuxian_impart.update_stone_num(give_crystal_num, give_user['user_id'], 1)  # 增加用户结晶
                msg = f"共赠送{number_to(give_crystal_num)}个结晶给{give_user['user_name']}道友！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await admin_add_jiejing.finish()
            else:
                msg = f"对方未踏入修仙界，不可赠送！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await admin_add_jiejing.finish()
        else:
            msg = f"请提供要赠送结晶的道号和数量！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_add_jiejing.finish()
    else:
        msg = f"请提供要赠送结晶的道号和数量！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_add_jiejing.finish()


@admin_add_wupin.handle(parameterless=[Cooldown(at_sender=False)])
async def admin_add_wupin_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """GM权限 添加物品给用户 创造力量 不输入道号 默认送给所有人 例如：创造力量 物品 数量 道号"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip().split()

    if not args:
        msg = f"请输入正确指令！例如：创造力量 物品 数量"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_add_wupin.finish()

    if len(msg) < 2:
        msg = f"请输入正确的物品名称和数量！例如：创造力量 物品 数量"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_add_wupin.finish()

    goods_name = msg[0]
    goods_id = -1
    goods_type = None

    for k, v in items.items.items():
        if goods_name == v['name']:
            goods_id = k
            goods_type = v['type']
            break

    if goods_id == -1:
        msg = f"找不到物品 {goods_name}，请检查物品名称是否正确！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_add_wupin.finish()

    goods_num = int(msg[1]) if msg[1].isdigit() else 1

    if len(msg) > 2:
        nick_name = ' '.join(msg[2:])
        give_user = sql_message.get_user_info_with_name(nick_name.strip())
        if give_user:
            sql_message.send_back(give_user['user_id'], goods_id, goods_name, goods_type, goods_num, 1)
            msg = f"{give_user['user_name']}道友获得了系统赠送的{goods_name}个{goods_num}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_add_wupin.finish()
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await admin_add_wupin.finish()
    # else:
    #     all_users = sql_message.get_all_user_id()
    #     for user_id in all_users:
    #         sql_message.send_back(user_id, goods_id, goods_name, goods_type, goods_num, 1)  # 给每个用户发送物品
    #
    #     msg = f"全服通告：赠送所有用户{goods_name}个{goods_num},请注意查收！"
    #     enabled_groups = sql_message.get_enabled_groups()
    #     for group_id in enabled_groups:
    #         bot = await assign_bot_group(group_id=group_id)
    #         try:
    #             await bot.send_group_msg(group_id=int(group_id), message=msg)
    #         except ActionFailed:  # 发送群消息失败
    #             continue
    await admin_add_wupin.finish()


@admin_update_linggen.handle(parameterless=[Cooldown(at_sender=False)])
async def admin_update_linggen_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """GM权限 改用户灵根 轮回力量"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip().split()

    if not args:
        msg = "请输入正确指令！例如：轮回力量 用户名称 x(1为混沌,2为融合,3为超,4为龙,5为天,6为千世,7为万世)"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_update_linggen.finish()

    if len(msg) < 2:
        msg = "请输入正确的用户名称和灵根编号！例如：轮回力量 用户名称 1"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_update_linggen.finish()

    nick_name = msg[0]
    root_type = msg[1]

    give_user = sql_message.get_user_info_with_name(nick_name.strip())
    if give_user:
        root_name = sql_message.update_root(give_user['user_id'], root_type)
        sql_message.update_power2(give_user['user_id'])
        msg = f"{give_user['user_name']}道友的灵根已变更为{root_name}！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_update_linggen.finish()
    else:
        msg = "对方未踏入修仙界，不可修改！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await admin_update_linggen.finish()
