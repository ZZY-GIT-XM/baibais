import asyncio
import random
from datetime import datetime
from nonebot import on_command, require, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment,
    GROUP_ADMIN,
    GROUP_OWNER,
    ActionFailed
)
from ..xiuxian_utils.lay_out import assign_bot, assign_bot_group, Cooldown, CooldownIsolateLevel
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from .back_util import (
    get_user_main_back_msg, check_equipment_can_use,
    get_use_equipment_sql, get_shop_data, save_shop,
    get_item_msg, get_item_msg_rank, check_use_elixir,
    get_use_jlq_msg, get_no_use_equipment_sql, get_user_skill_back_msg
)
from .backconfig import get_auction_config, savef_auction, remove_auction_item
# from ..xiuxian_utils.item_json import Items
from ..xiuxian_utils.item_database_handler import Items
from ..xiuxian_utils.utils import (
    check_user, get_msg_pic,
    send_msg_handler, CommandObjectID,
    Txt2Img, number_to
)
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, get_weapon_info_msg, get_armor_info_msg,
    get_sec_msg, get_main_info_msg, get_sub_info_msg, UserBuffDate
)

items = Items()
config = get_auction_config()
groups = config['open']  # list，群交流会使用
auction = {}
PAGE_SIZE = 5  # 每页显示的物品数量
auction_time_config = config['拍卖会定时参数']  # 定时配置
sql_message = XiuxianDateManage()  # sql类

shop = on_command("坊市查看", aliases={"查看坊市"}, priority=8, permission=GROUP, block=True)
shop_added = on_command("坊市上架", priority=10, permission=GROUP, block=True)
shop_added_by_admin = on_command("系统坊市上架", priority=5, permission=SUPERUSER, block=True)
shop_off = on_command("坊市下架", priority=5, permission=GROUP, block=True)
buy = on_command("坊市购买", priority=5, block=True)
shop_off_all = on_fullmatch("清空坊市", priority=3, permission=SUPERUSER, block=True)

buy_lock = asyncio.Lock()

@buy.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def buy_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """坊市购买"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    async with buy_lock:
        isUser, user_info, msg = check_user(event)
        if not isUser:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()
        user_id = user_info['user_id']
        group_id = str(666)
        shop_data = get_shop_data(group_id)

        if shop_data[group_id] == {}:
            msg = "坊市目前空空如也！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()
        input_args = args.extract_plain_text().strip().split()
        if len(input_args) < 1:
            # 没有输入任何参数
            msg = "请输入正确指令！例如：坊市购买 物品编号 数量"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()

        try:
            arg = int(input_args[0])
            if len(input_args) == 0:
                msg = "请输入正确指令！例如：坊市购买 物品编号 数量"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await buy.finish()

            goods_info = shop_data[group_id].get(str(arg))
            if not goods_info:
                raise ValueError("编号对应的商品不存在！")

            purchase_quantity = int(input_args[1]) if len(input_args) > 1 else 1
            if purchase_quantity <= 0:
                raise ValueError("购买数量必须是正数！")

            if 'stock' in goods_info and purchase_quantity > goods_info['stock']:
                raise ValueError("购买数量超过库存限制！")
        except ValueError as e:
            msg = f"{str(e)}"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()
        shop_user_id = shop_data[group_id][str(arg)]['user_id']
        goods_price = goods_info['price'] * purchase_quantity
        goods_stock = goods_info.get('stock', 1)
        if user_info['stone'] < goods_price:
            msg = '没钱还敢来买东西！！'
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()
        elif int(user_id) == int(shop_data[group_id][str(arg)]['user_id']):
            msg = "道友自己的东西就不要自己购买啦！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()
        elif purchase_quantity > goods_stock and shop_user_id != 0:
            msg = "库存不足，无法购买所需数量！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        else:
            shop_goods_name = shop_data[group_id][str(arg)]['goods_name']
            shop_user_name = shop_data[group_id][str(arg)]['user_name']
            shop_goods_id = shop_data[group_id][str(arg)]['goods_id']
            shop_goods_type = shop_data[group_id][str(arg)]['goods_type']
            sql_message.update_ls(user_id, goods_price, 2)
            sql_message.send_back(user_id, shop_goods_id, shop_goods_name, shop_goods_type, purchase_quantity)
            save_shop(shop_data)

            if shop_user_id == 0:  # 0为系统
                msg = f"道友成功购买{purchase_quantity}个{shop_goods_name}，消耗灵石{goods_price}枚！"
            else:
                goods_info['stock'] -= purchase_quantity
                if goods_info['stock'] <= 0:
                    del shop_data[group_id][str(arg)]  # 库存为0，移除物品
                else:
                    shop_data[group_id][str(arg)] = goods_info
                service_charge = int(goods_price * 0.1)  # 手续费10%
                give_stone = goods_price - service_charge
                msg = f"道友成功购买{purchase_quantity}个{shop_user_name}道友寄售的{shop_goods_name}，消耗灵石{goods_price}枚,坊市收取手续费：{service_charge}枚灵石！"
                sql_message.update_ls(shop_user_id, give_stone, 1)
            shop_data[group_id] = reset_dict_num(shop_data[group_id])
            save_shop(shop_data)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await buy.finish()


@shop.handle(parameterless=[Cooldown(at_sender=False)])
async def shop_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """坊市查看，添加翻页功能"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    # 如果用户未注册，直接发送文字消息
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop.finish()

    group_id = str(666)
    shop_data = get_shop_data(group_id)

    # 如果坊市数据为空，发送纯文字提示
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop.finish()

    # 尝试获取页码
    try:
        page = int(args.extract_plain_text().strip())
    except ValueError:
        page = 1  # 如果没有提供页码或格式不正确，默认为第一页

    # 将坊市数据转化为列表，便于分页
    data_list = []
    for k, v in shop_data[group_id].items():
        msg = f"编号：{k}\n"
        msg += f"{v['desc']}"
        msg += f"\n价格：{v['price']}枚灵石\n"
        if v['user_id'] != 0:
            msg += f"拥有人：{v['user_name']}道友\n"
            msg += f"数量：{v['stock']}\n"
        else:
            msg += f"系统出售\n"
            msg += f"数量：无限\n"
        data_list.append(msg)

    # 计算总页数
    total_items = len(data_list)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整

    # 检查当前页码是否有效
    if page < 1 or page > total_pages:
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"无效的页码。请输入有效的页码范围：1-{total_pages}")
        await shop.finish()

    # 获取当前页的数据
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_items)
    page_data = data_list[start_idx:end_idx]

    # 组装并发送当前页的数据
    final_msg = f"坊市列表 \n" + "\n\n".join(page_data)
    final_msg += f"\n\n第 {page}/{total_pages} 页\n使用命令 '坊市查看 {page + 1}' 查看下一页" if page < total_pages else "\n\n这是最后一页。"

    await bot.send_group_msg(group_id=int(send_group_id), message=final_msg)

    await shop.finish()


@shop_added_by_admin.handle(
    parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_added_by_admin_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """系统上架坊市"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    args = args.extract_plain_text().split()
    if not args:
        msg = "请输入正确指令！例如：系统坊市上架 物品 金额"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    goods_name = args[0]
    goods_id = -1
    for k, v in items.items.items():
        if goods_name == v['name']:
            goods_id = k
            break
    if goods_id == -1:
        msg = f"不存在物品：{goods_name}的信息，请检查名字是否输入正确！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    price = None
    try:
        price = int(args[1])
        if price < 0:
            msg = "请不要设置负数！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_added_by_admin.finish()
    except (IndexError, ValueError):
        msg = "请输入正确的金额！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()

    try:
        var = args[2]
        msg = "请输入正确指令！例如：系统坊市上架 物品 金额"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    except IndexError:
        pass

    group_id = str(666)
    shop_data = get_shop_data(group_id)
    if shop_data == {}:
        shop_data[group_id] = {}
    goods_info = items.get_data_by_item_id(goods_id)

    id_ = len(shop_data[group_id]) + 1
    shop_data[group_id][id_] = {
        'user_id': 0,
        'goods_name': goods_name,
        'goods_id': goods_id,
        'goods_type': goods_info['type'],
        'desc': get_item_msg(goods_id),
        'price': price,
        'user_name': '系统'
    }
    save_shop(shop_data)
    msg = f"物品：{goods_name}成功上架坊市，金额：{price}枚灵石！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await shop_added_by_admin.finish()


@shop_added.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def shop_added_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """用户上架坊市"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    user_id = user_info['user_id']
    args = args.extract_plain_text().split()
    goods_name = args[0] if len(args) > 0 else None
    price_str = args[1] if len(args) > 1 else "500000"  # 默认为500000
    quantity_str = args[2] if len(args) > 2 else "1"  # 默认为1
    if len(args) == 0:
        msg = f"{user_info['user_name']} 道友请输入正确指令！例如：坊市上架 物品 可选参数为(金额 数量)"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    elif len(args) == 1:
        goods_name, price_str = args[0], "500000"
        quantity_str = "1"
    elif len(args) == 2:
        goods_name, price_str = args[0], args[1]
        quantity_str = "1"
    else:
        goods_name, price_str, quantity_str = args[0], args[1], args[2]

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,dict
    if back_msg is None:
        msg = f"{user_info['user_name']} 道友的背包空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    goods_bind_num = None
    for back in back_msg:
        if goods_name == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_state = back['state']
            goods_num = back['goods_num']
            goods_bind_num = back['bind_num']
            break
    if not in_flag:
        msg = f"{user_info['user_name']} 道友请检查该道具 {goods_name} 是否在背包内！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    price = None

    # 解析价格
    try:
        price = int(price_str)
        if price <= 0:
            raise ValueError("价格必须为正数！")
    except ValueError as e:
        msg = f"请输入正确的金额: {str(e)}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    # 解析数量
    try:
        quantity = int(quantity_str)
        if quantity <= 0 or quantity > goods_num:  # 检查指定的数量是否合法
            raise ValueError("数量必须为正数或者小于等于你拥有的物品数!")
    except ValueError as e:
        msg = f"请输入正确的数量: {str(e)}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    price = max(price, 500000)  # 最低价格为50w
    if goods_type == "装备" and int(goods_state) == 1 and int(goods_num) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法上架！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()

    if int(goods_num) <= int(goods_bind_num):
        msg = "该物品是绑定物品，无法上架！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()
    if goods_type == "聚灵旗" or goods_type == "炼丹炉":
        if user_info['root'] == "器师":
            pass
        else:
            msg = "道友职业无法上架！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_added.finish()

    group_id = str(666)
    shop_data = get_shop_data(group_id)

    num = 0
    for k, v in shop_data[group_id].items():
        if str(v['user_id']) == str(user_info['user_id']):
            num += 1
        else:
            pass
    if num >= 10:
        msg = "每人只可上架十个物品！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added.finish()

    if shop_data == {}:
        shop_data[group_id] = {}
    id_ = len(shop_data[group_id]) + 1
    shop_data[group_id][id_] = {
        'user_id': user_id,
        'goods_name': goods_name,
        'goods_id': goods_id,
        'goods_type': goods_type,
        'desc': get_item_msg(goods_id),
        'price': price,
        'user_name': user_info['user_name'],
        'stock': quantity,  # 物品数量
    }
    sql_message.update_back_j(user_id, goods_id, num=quantity)
    save_shop(shop_data)
    msg = f"{user_info['user_name']} 道友物品：{goods_name}成功上架坊市，金额：{price}枚灵石，数量{quantity}！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await shop_added.finish()


@shop_off.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_off_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """坊市下架商品"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off.finish()
    user_id = user_info['user_id']
    group_id = str(666)
    shop_data = get_shop_data(group_id)
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off.finish()

    arg = args.extract_plain_text().strip()
    try:
        arg = int(arg)
        if arg <= 0 or arg > len(shop_data[group_id]):
            msg = "请输入正确的编号！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_off.finish()
    except ValueError:
        msg = "请输入正确的编号！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off.finish()

    if str(arg) not in shop_data[group_id]:
        msg = "输入的编号不存在！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off.finish()

    shop_user_name = shop_data[group_id][str(arg)]['user_name']

    if shop_data[group_id][str(arg)]['user_id'] == user_id:
        sql_message.send_back(user_id, shop_data[group_id][str(arg)]['goods_id'],
                              shop_data[group_id][str(arg)]['goods_name'], shop_data[group_id][str(arg)]['goods_type'],
                              shop_data[group_id][str(arg)]['stock'])
        msg = f"{user_info['user_name']} 道友成功下架物品：{shop_data[group_id][str(arg)]['goods_name']}！"
        del shop_data[group_id][str(arg)]
        shop_data[group_id] = reset_dict_num(shop_data[group_id])
        save_shop(shop_data)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off.finish()

    elif event.sender.role == "admin" or event.sender.role == "owner" or event.get_user_id() in bot.config.superusers:
        if shop_data[group_id][str(arg)]['user_id'] == 0:  # 这么写为了防止bot.send发送失败，不结算
            msg = f"{user_info['user_name']} 道友成功下架物品：{shop_data[group_id][str(arg)]['goods_name']}！"
            del shop_data[group_id][str(arg)]
            shop_data[group_id] = reset_dict_num(shop_data[group_id])
            save_shop(shop_data)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_off.finish()
        else:
            sql_message.send_back(shop_data[group_id][str(arg)]['user_id'], shop_data[group_id][str(arg)]['goods_id'],
                                  shop_data[group_id][str(arg)]['goods_name'],
                                  shop_data[group_id][str(arg)]['goods_type'], shop_data[group_id][str(arg)]['stock'])
            msg1 = f"{user_info['user_name']} 道友上架的{shop_data[group_id][str(arg)]['stock']}个{shop_data[group_id][str(arg)]['goods_name']}已被管理员{user_info['user_name']}下架！"
            del shop_data[group_id][str(arg)]
            shop_data[group_id] = reset_dict_num(shop_data[group_id])
            save_shop(shop_data)
            try:
                await bot.send(event=event, message=msg1)
            except ActionFailed:
                pass

    else:
        msg = f"{user_info['user_name']} 道友这东西不是你的！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off.finish()


@shop_off_all.handle(parameterless=[Cooldown(60, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_off_all_(bot: Bot, event: GroupMessageEvent):
    """坊市清空"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off_all.finish()
    group_id = str(666)
    shop_data = get_shop_data(group_id)
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off_all.finish()

    msg = "正在清空,稍等！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    list_msg = []
    msg = ""
    num = len(shop_data[group_id])
    for x in range(num):
        x = num - x
        if shop_data[group_id][str(x)]['user_id'] == 0:  # 这么写为了防止bot.send发送失败，不结算
            msg += f"成功下架系统物品：{shop_data[group_id][str(x)]['goods_name']}!\n"
            del shop_data[group_id][str(x)]
            save_shop(shop_data)
        else:
            sql_message.send_back(shop_data[group_id][str(x)]['user_id'], shop_data[group_id][str(x)]['goods_id'],
                                  shop_data[group_id][str(x)]['goods_name'],
                                  shop_data[group_id][str(x)]['goods_type'], shop_data[group_id][str(x)]['stock'])
            msg += f"成功下架{shop_data[group_id][str(x)]['user_name']}的{shop_data[group_id][str(x)]['stock']}个{shop_data[group_id][str(x)]['goods_name']}!\n"
            del shop_data[group_id][str(x)]
            save_shop(shop_data)
    shop_data[group_id] = reset_dict_num(shop_data[group_id])
    save_shop(shop_data)

    try:
        await send_msg_handler(bot, event, [{"type": "text", "data": {"content": msg}}])
    except ActionFailed:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await shop_off_all.finish()


def reset_dict_num(dict_):
    i = 1
    temp_dict = {}
    for k, v in dict_.items():
        temp_dict[i] = v
        temp_dict[i]['编号'] = i
        i += 1
    return temp_dict


def get_user_auction_id_list():
    user_auctions = config['user_auctions']
    user_auction_id_list = []
    for auction in user_auctions:
        for k, v in auction.items():
            user_auction_id_list.append(v['id'])
    return user_auction_id_list


def get_auction_id_list():
    auctions = config['auctions']
    auction_id_list = []
    for k, v in auctions.items():
        auction_id_list.append(v['id'])
    return auction_id_list


def get_user_auction_price_by_id(id):
    user_auctions = config['user_auctions']
    user_auction_info = None
    for auction in user_auctions:
        for k, v in auction.items():
            if int(v['id']) == int(id):
                user_auction_info = v
                break
        if user_auction_info:
            break
    return user_auction_info


def get_auction_price_by_id(id):
    auctions = config['auctions']
    auction_info = None
    for k, v in auctions.items():
        if int(v['id']) == int(id):
            auction_info = v
            break
    return auction_info


def get_auction_msg(auction_id):
    item_info = items.get_data_by_item_id(auction_id)
    _type = item_info['type']
    msg = None
    if _type == "装备":
        if item_info['item_type'] == "防具":
            msg = get_armor_info_msg(auction_id, item_info)
        if item_info['item_type'] == '法器':
            msg = get_weapon_info_msg(auction_id, item_info)

    if _type == "技能":
        if item_info['item_type'] == '神通':
            msg = f"{item_info['level']}-{item_info['name']}:\n"
            msg += f"效果：{get_sec_msg(item_info)}"
        if item_info['item_type'] == '功法':
            msg = f"{item_info['level']}-{item_info['name']}\n"
            msg += f"效果：{get_main_info_msg(auction_id)[1]}"
        if item_info['item_type'] == '辅修功法':  # 辅修功法10
            msg = f"{item_info['level']}-{item_info['name']}\n"
            msg += f"效果：{get_sub_info_msg(auction_id)[1]}"

    if _type == "神物":
        msg = f"{item_info['name']}\n"
        msg += f"效果：{item_info['description']}"

    if _type == "丹药":
        msg = f"{item_info['name']}\n"
        msg += f"效果：{item_info['description']}"

    return msg
