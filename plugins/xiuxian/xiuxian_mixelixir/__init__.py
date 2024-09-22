import json
import random
import asyncio
import re
from pathlib import Path
from nonebot import on_command, on_fullmatch, on_regex
from nonebot.params import EventPlainText
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment,
    ActionFailed
)
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, get_player_info, save_player_info,
    UserBuffDate, XIUXIAN_IMPART_BUFF
)
from ..xiuxian_utils.utils import (
    check_user, send_msg_handler,
    get_msg_pic, CommandObjectID
)
from nonebot.params import CommandArg
from ..xiuxian_utils.item_json import Items
from .mixelixirutil import get_mix_elixir_msg, tiaohe, check_mix, make_dict
from ..xiuxian_config import convert_rank, XiuConfig
from datetime import datetime, timedelta
from .mix_elixir_config import MIXELIXIRCONFIG
from ..xiuxian_back.back_util import get_user_elixir_back_msg, get_user_yaocai_back_msg

sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()
items = Items()
cache_help = {}
PAGE_SIZE = 6  # 每页显示的物品数量
DANFANG_PATH = Path(__file__).parent / "danfang_info.json"# 丹方存储路径
CACHE_TIMEOUT = timedelta(minutes=5) # 丹方缓存超时时间为5分钟

mix_elixir = on_fullmatch("炼丹", priority=17, permission=GROUP, block=True)
mix_make = on_command("配方", priority=5, permission=GROUP, block=True)
elixir_help = on_fullmatch("炼丹帮助", priority=7, permission=GROUP, block=True)
mix_elixir_help = on_fullmatch("炼丹配方帮助", priority=7, permission=GROUP, block=True)
elixir_back = on_command("丹药背包", priority=10, permission=GROUP, block=True)
yaocai_back = on_command("药材背包", priority=10, permission=GROUP, block=True)
yaocai_get = on_command("灵田收取", aliases={"灵田结算"}, priority=8, permission=GROUP, block=True)
my_mix_elixir_info = on_fullmatch("我的炼丹信息", priority=6, permission=GROUP, block=True)
mix_elixir_sqdj_up = on_fullmatch("升级收取等级", priority=6, permission=GROUP, block=True)
mix_elixir_dykh_up = on_fullmatch("升级丹药控火", priority=6, permission=GROUP, block=True)

__elixir_help__ = f"""
炼丹帮助信息:
-指令：
  - 炼丹：会检测背包内的药材，自动生成配方【一次最多匹配25种药材】
  - 配方：发送配方领取丹药【配方主药.....】
  - 炼丹帮助：获取本帮助信息
  - 丹药背包：获取背包内丹药以及炼丹炉信息
  - 药材背包：获取背包内药材信息
  - 炼丹配方帮助：获取炼丹配方帮助
  - 灵田收取、灵田结算：收取洞天福地里灵田的药材
  - 我的炼丹信息：查询自己的炼丹信息
  - 升级收取等级：每一个等级会增加灵田收取的数量
  - 升级丹药控火：每一个等级会增加炼丹的产出数量
""".strip()

__mix_elixir_help__ = f"""
炼丹配方信息:
- 炼丹需要主药、药引、辅药
- 主药和药引控制炼丹时的冷热调和，冷热失和则炼不出丹药
- 草药的类型控制产出丹药的类型
- 来自群友猫猫头工具网址：https://huggingface.co/spaces/chewing/liandan
""".strip()



@mix_elixir_sqdj_up.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_sqdj_up_(bot: Bot, event: GroupMessageEvent):
    """收取等级升级"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_sqdj_up.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_sqdj_up.finish()

    SQDJCONFIG = MIXELIXIRCONFIG['收取等级']
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_level = mix_elixir_info['收取等级']

    if now_level >= len(SQDJCONFIG):
        msg = f"道友的收取等级已达到最高等级，无法升级了"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_sqdj_up.finish()

    next_level_cost = SQDJCONFIG[str(now_level + 1)]['level_up_cost']
    if mix_elixir_info['炼丹经验'] < next_level_cost:
        msg = f"下一个收取等级所需要的炼丹经验为{next_level_cost}点，道友请炼制更多的丹药再来升级吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_sqdj_up.finish()

    mix_elixir_info['炼丹经验'] = mix_elixir_info['炼丹经验'] - next_level_cost
    mix_elixir_info['收取等级'] = now_level + 1
    save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')

    msg = f"道友的收取等级目前为：{mix_elixir_info['收取等级']}级，可以使灵田收获的药材增加{mix_elixir_info['收取等级']}个！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await mix_elixir_sqdj_up.finish()



@mix_elixir_dykh_up.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_dykh_up_(bot: Bot, event: GroupMessageEvent):
    """丹药控火升级"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_dykh_up.finish()

    user_id = user_info['user_id']
    DYKHCONFIG = MIXELIXIRCONFIG['丹药控火']
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_level = mix_elixir_info['丹药控火']

    if now_level >= len(DYKHCONFIG):
        msg = f"道友的丹药控火等级已达到最高等级，无法升级了"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_dykh_up.finish()

    next_level_cost = DYKHCONFIG[str(now_level + 1)]['level_up_cost']
    if mix_elixir_info['炼丹经验'] < next_level_cost:
        msg = f"下一个丹药控火等级所需要的炼丹经验为{next_level_cost}点，道友请炼制更多的丹药再来升级吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir_dykh_up.finish()

    mix_elixir_info['炼丹经验'] = mix_elixir_info['炼丹经验'] - next_level_cost
    mix_elixir_info['丹药控火'] = now_level + 1
    save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')

    msg = f"道友的丹药控火等级目前为：{mix_elixir_info['丹药控火']}级，可以使炼丹收获的丹药增加{mix_elixir_info['丹药控火']}个！"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await mix_elixir_dykh_up.finish()



@yaocai_get.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
async def yaocai_get_(bot: Bot, event: GroupMessageEvent):
    """灵田收取"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await yaocai_get.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await yaocai_get.finish()

    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    GETCONFIG = {
        "time_cost": 48,  # 单位小时
        "加速基数": 0.05
    }
    last_time = mix_elixir_info['收取时间']
    if last_time != 0:
        nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
        timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S') - datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)
        if timedeff >= round(GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['药材速度'])), 2):
            yaocai_id_list = items.get_random_id_list_by_rank_and_item_type(convert_rank(user_info['level'])[0], ['药材'])
            # 加入传承
            impart_data = xiuxian_impart.get_user_info_with_id(user_id)
            impart_reap_per = impart_data['impart_reap_per'] if impart_data is not None else 0
            # 功法灵田收取加成
            main_reap = UserBuffDate(user_id).get_user_main_buff_data()

            if main_reap is not None:  # 功法灵田收取加成
                reap_buff = main_reap['reap_buff']
            else:
                reap_buff = 0
            num = mix_elixir_info['灵田数量'] + mix_elixir_info['收取等级'] + impart_reap_per + reap_buff
            msg = ''
            if not yaocai_id_list:
                sql_message.send_back(user_info['user_id'], 3001, '恒心草', '药材', num)  # 没有合适的，保底
                msg += f"道友成功收获药材：恒心草 {num} 个！\n"
            else:
                i = 1
                give_dict = {}
                while i <= num:
                    id = random.choice(yaocai_id_list)
                    try:
                        give_dict[id] += 1
                        i += 1
                    except LookupError:
                        give_dict[id] = 1
                        i += 1
                for k, v in give_dict.items():
                    goods_info = items.get_data_by_item_id(k)
                    msg += f"道友成功收获药材：{goods_info['name']} {v} 个！\n"
                    sql_message.send_back(user_info['user_id'], k, goods_info['name'], '药材', v)
            mix_elixir_info['收取时间'] = nowtime
            save_player_info(user_id, mix_elixir_info, "mix_elixir_info")
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await yaocai_get.finish()
        else:
            msg = f"道友的灵田还不能收取，下次收取时间为：{round(GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['药材速度'])), 2) - timedeff}小时之后"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await yaocai_get.finish()



@my_mix_elixir_info.handle(parameterless=[Cooldown(at_sender=False)])
async def my_mix_elixir_info_(bot: Bot, event: GroupMessageEvent):
    """我的炼丹信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await my_mix_elixir_info.finish()

    user_id = user_info['user_id']
    mix_elixir_info = get_player_info(user_id, 'mix_elixir_info')

    # 初始化消息
    l_msg = [f"☆------道友的炼丹信息------☆"]
    msg = f"药材收取等级：{mix_elixir_info.get('收取等级', '未知')}\n"
    msg += f"丹药控火等级：{mix_elixir_info.get('丹药控火', '未知')}\n"
    msg += f"丹药耐药性等级：{mix_elixir_info.get('丹药耐药性', '未知')}\n"
    msg += f"炼丹经验：{mix_elixir_info.get('炼丹经验', '未知')}\n"
    l_msg.append(msg)

    if mix_elixir_info.get('炼丹记录', {}) != {}:
        l_msg.append(f"☆------道友的炼丹记录------☆")
        # 构建炼丹记录的消息
        i = 1
        for k, v in mix_elixir_info['炼丹记录'].items():
            msg = f"编号：{i},{v.get('name', '未知')}，炼成次数：{v.get('num', '未知')}次"
            l_msg.append(msg)
            i += 1

    # 发送最终消息
    full_msg = "\n".join(l_msg)
    await bot.send_group_msg(group_id=int(send_group_id), message=full_msg)
    await my_mix_elixir_info.finish()


@elixir_help.handle(parameterless=[Cooldown(at_sender=False)])
async def elixir_help_(bot: Bot, event: GroupMessageEvent):
    """炼丹帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __elixir_help__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await elixir_help.finish()


@mix_elixir_help.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_help_(bot: Bot, event: GroupMessageEvent):
    """炼丹配方帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __mix_elixir_help__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await mix_elixir_help.finish()





class DateTimeEncoder(json.JSONEncoder):
    """ 自定义的JSONEncoder类来处理datetime类型 """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def load_danfang_info():
    """加载丹方信息"""
    if DANFANG_PATH.exists():
        with open(DANFANG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_danfang_info(danfang_info):
    """保存丹方信息"""
    with open(DANFANG_PATH, 'w', encoding='utf-8') as f:
        json.dump(danfang_info, f, cls=DateTimeEncoder, ensure_ascii=False, indent=4)


def check_danfang_expiration(danfang_info):
    """检查丹方是否过期"""
    now = datetime.now()
    expired_users = []
    for user_id, info in danfang_info.items():
        if 'expiration' in info and info['expiration']:
            try:
                expiration = datetime.fromisoformat(info['expiration'])
                if expiration < now:
                    expired_users.append(user_id)
            except ValueError:
                pass
    for user_id in expired_users:
        del danfang_info[user_id]
    return danfang_info


# 初始化丹方信息
danfang_info = load_danfang_info()
danfang_info = check_danfang_expiration(danfang_info)

# 初始化全局变量
user_ldl_dict = {}
user_ldl_flag = {}
user_cache = {}

# 定义正则表达式匹配
mix_elixir = on_regex(
    r"^(炼丹)\s?(\d+)?$",  # 匹配“炼丹”后面可选的页码
    flags=re.I,
    priority=1,
    block=True
)


@mix_elixir.handle()
async def mix_elixir_(bot: Bot,event: GroupMessageEvent):
    global user_ldl_dict, user_ldl_flag, danfang_info
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_elixir.finish()

    user_id = user_info['user_id']

    # 尝试获取页码
    match = re.match(r"^(炼丹)\s?(\d+)?$", event.get_plaintext())
    if match:
        try:
            page_str = match.group(2)  # 使用正则匹配结果
            page = int(page_str) if page_str else 1  # 如果没有提供页码，默认为第一页
        except (ValueError, IndexError):
            page = 1  # 如果页码格式不正确，默认为第一页
    else:
        page = 1  # 默认为第一页

    # 检查是否存在缓存数据
    if user_id in danfang_info:
        # 确保缓存中的数据是列表形式
        data_list = danfang_info[user_id].get('data_list', [])
        total_pages = danfang_info[user_id].get('total_pages', 1)
    else:
        # 清除过期缓存
        danfang_info = check_danfang_expiration(danfang_info)
        save_danfang_info(danfang_info)

        # 生成新的丹方信息
        user_back = sql_message.get_back_msg(user_id)
        yaocai_dict = {}
        user_ldl_flag[user_id] = False  # 初始化炼丹炉标志
        for back in user_back:
            if back['goods_type'] == "药材":
                yaocai_dict[back['goods_id']] = items.get_data_by_item_id(back['goods_id'])
                yaocai_dict[back['goods_id']]['num'] = back['goods_num']
            elif back['goods_type'] == "炼丹炉":
                if user_id not in user_ldl_dict:
                    user_ldl_dict[user_id] = {}
                user_ldl_dict[user_id][back['goods_id']] = back['goods_name']
                user_ldl_flag[user_id] = True

        if user_back is None:
            await bot.send_group_msg(group_id=int(send_group_id), message="道友的背包空空如也，无法炼丹")
            await mix_elixir.finish()

        if yaocai_dict == {}:
            await bot.send_group_msg(group_id=int(send_group_id), message="道友的背包内没有药材，无法炼丹！")
            await mix_elixir.finish()

        if not user_ldl_flag[user_id]:
            await bot.send_group_msg(group_id=int(send_group_id), message="道友背包内没有炼丹炉，无法炼丹！")
            await mix_elixir.finish()

        await bot.send_group_msg(group_id=int(send_group_id), message="正在生成丹方，请稍候...")

        yaocai_dict = await make_dict(yaocai_dict)
        finall_mix_elixir_msg = await get_mix_elixir_msg(yaocai_dict)
        if finall_mix_elixir_msg == {}:
            await bot.send_group_msg(group_id=int(send_group_id), message="系统未检测到丹方，道友背包内的药材不满足！")
            await mix_elixir.finish()
        else:
            ldl_name = sorted(user_ldl_dict[user_id].items(), key=lambda x: x[0], reverse=False)[0][1]

            # 将炼丹结果转化为列表，便于分页
            data_list = []
            for k, v in finall_mix_elixir_msg.items():
                goods_info = items.get_data_by_item_id(v['id'])
                msg = f"名字：{goods_info['name']}\n"
                msg += f"效果：{goods_info['desc']}\n"
                msg += f"配方：{v['配方']['配方简写']}丹炉{ldl_name}\n"
                msg += f"☆------药材清单------☆\n"
                msg += f"主药：{v['配方']['主药']},{v['配方']['主药_level']}，数量：{v['配方']['主药_num']}\n"
                msg += f"药引：{v['配方']['药引']},{v['配方']['药引_level']}，数量：{v['配方']['药引_num']}\n"
                if v['配方']['辅药_num'] != 0:
                    msg += f"辅药：{v['配方']['辅药']},{v['配方']['辅药_level']}，数量：{v['配方']['辅药_num']}\n"
                data_list.append(msg)
                total_items = len(data_list)

            # 计算总页数
            total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整

            # 存储缓存数据
            expiration_time = datetime.now() + CACHE_TIMEOUT
            danfang_info[user_id] = {
                'data_list': data_list,
                'total_pages': total_pages,
                'expiration': expiration_time.isoformat()
            }

            # 保存丹方信息到文件
            save_danfang_info(danfang_info)

    # 获取当前页的数据
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(data_list))
    page_data = data_list[start_idx:end_idx]

    # 检查当前页码是否有效
    if page < 1 or page > total_pages:
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"无效的页码。请输入有效的页码范围：1-{total_pages}")
        await mix_elixir.finish()

    # 组装并发送当前页的数据
    final_msg = f"丹方列表 \n" + "\n\n".join(page_data)
    final_msg += f"\n\n第 {page}/{total_pages} 页\n使用命令 '炼丹 {page + 1}' 查看下一页" if page < total_pages else "\n\n这是最后一页。"

    await bot.send_group_msg(group_id=int(send_group_id), message=final_msg)

    # 结束匹配器执行
    await mix_elixir.finish()


@mix_make.handle(parameterless=[Cooldown(stamina_cost=3, at_sender=False)])
async def mix_elixir_(bot: Bot, event: GroupMessageEvent, mode: str = EventPlainText()):
    """配方"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.user_id
    pattern = r"主药([\u4e00-\u9fa5]+)(\d+)药引([\u4e00-\u9fa5]+)(\d+)辅药([\u4e00-\u9fa5]+)(\d+)丹炉([\u4e00-\u9fa5]+)+"
    matched = re.search(pattern, mode)
    if matched is None:
        msg = f"请输入正确的配方！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await mix_make.finish()
    else:
        zhuyao_name = matched.groups()[0]
        zhuyao_num = int(matched.groups()[1])  # 数量一定会有
        check, zhuyao_goods_id = await check_yaocai_name_in_back(user_id, zhuyao_name, zhuyao_num)
        if not check:
            msg = f"请检查药材：{zhuyao_name} 是否在背包中，或者数量是否足够！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await mix_make.finish()
        yaoyin_name = matched.groups()[2]
        yaoyin_num = int(matched.groups()[3])  # 数量一定会有
        check, yaoyin_goods_id = await check_yaocai_name_in_back(user_id, yaoyin_name, yaoyin_num)
        if not check:
            msg = f"请检查药材：{yaoyin_name} 是否在背包中，或者数量是否足够！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await mix_make.finish()
        fuyao_name = matched.groups()[4]
        fuyao_num = int(matched.groups()[5])
        check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num)
        if not check:
            msg = f"请检查药材：{fuyao_name} 是否在背包中，或者数量是否足够！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await mix_make.finish()
        if zhuyao_name == fuyao_name:
            check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num + zhuyao_num)
            if not check:
                msg = f"请检查药材：{zhuyao_name} 是否在背包中，或者数量是否足够！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await mix_make.finish()
        if yaoyin_name == fuyao_name:
            check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num + yaoyin_num)
            if not check:
                msg = f"请检查药材：{yaoyin_name} 是否在背包中，或者数量是否足够！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await mix_make.finish()

        ldl_name = matched.groups()[6]
        check, ldl_info = await check_ldl_name_in_back(user_id, ldl_name)
        if not check:
            msg = f"请检查炼丹炉：{ldl_name} 是否在背包中！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await mix_make.finish()
        # 检测通过
        zhuyao_info = Items().get_data_by_item_id(zhuyao_goods_id)
        yaoyin_info = Items().get_data_by_item_id(yaoyin_goods_id)
        if await tiaohe(zhuyao_info, zhuyao_num, yaoyin_info, yaoyin_num):  # 调和失败
            msg = f"冷热调和失败！小心炸炉哦~"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await mix_make.finish()
        else:
            elixir_config = {
                str(zhuyao_info['主药']['type']): zhuyao_info['主药']['power'] * zhuyao_num
            }
            fuyao_info = Items().get_data_by_item_id(fuyao_goods_id)
            elixir_config[str(fuyao_info['辅药']['type'])] = fuyao_info['辅药']['power'] * fuyao_num
            is_mix, id = await check_mix(elixir_config)
            if is_mix:
                mix_elixir_info = get_player_info(user_id, 'mix_elixir_info')
                goods_info = Items().get_data_by_item_id(id)
                # 加入传承
                impart_data = xiuxian_impart.get_user_info_with_id(user_id)
                impart_mix_per = impart_data['impart_mix_per'] if impart_data is not None else 0
                # 功法炼丹数加成
                main_dan_data = UserBuffDate(user_id).get_user_main_buff_data()
                main_dan = main_dan_data['dan_buff'] if main_dan_data is not None else 0
                # 功法炼丹经验加成
                main_dan_exp = UserBuffDate(user_id).get_user_main_buff_data()
                main_exp = main_dan_exp['dan_exp'] if main_dan_exp is not None else 0

                num = 1 + ldl_info['buff'] + mix_elixir_info['丹药控火'] + impart_mix_per + main_dan  # 炼丹数量提升
                msg = f"恭喜道友成功炼成丹药：{goods_info['name']}{num}枚"
                # 背包sql
                sql_message.send_back(user_id, id, goods_info['name'], "丹药", num)  # 将炼制的丹药加入背包
                sql_message.update_back_j(user_id, zhuyao_goods_id, zhuyao_num)  # 将消耗的药材从背包中减去
                sql_message.update_back_j(user_id, fuyao_goods_id, fuyao_num)
                sql_message.update_back_j(user_id, yaoyin_goods_id, yaoyin_num)
                try:
                    var = mix_elixir_info['炼丹记录'][id]
                    now_num = mix_elixir_info['炼丹记录'][id]['num']  # now_num 已经炼制的丹药数量
                    if now_num >= goods_info['mix_all']:
                        msg += f"该丹药道友已炼制{now_num}次，无法获得炼丹经验了~"
                    elif now_num + num >= goods_info['mix_all']:
                        exp_num = goods_info['mix_all'] - now_num
                        mix_elixir_info['炼丹经验'] += (goods_info['mix_exp'] + main_exp) * exp_num
                        msg += f"获得炼丹经验{goods_info['mix_exp'] * exp_num}点"
                    else:
                        mix_elixir_info['炼丹经验'] += (goods_info['mix_exp'] + main_exp) * num
                        msg += f"获得炼丹经验{(goods_info['mix_exp'] + main_exp) * num}点"
                    mix_elixir_info['炼丹记录'][id]['num'] += num
                except:
                    mix_elixir_info['炼丹记录'][id] = {}
                    mix_elixir_info['炼丹记录'][id]['name'] = goods_info['name']
                    mix_elixir_info['炼丹记录'][id]['num'] = num
                    mix_elixir_info['炼丹经验'] += (goods_info['mix_exp'] + main_exp) * num
                    msg += f"获得炼丹经验{(goods_info['mix_exp'] + main_exp) * num}点"
                save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await mix_make.finish()
            else:
                msg = f"没有炼成丹药哦~就不扣你药材啦"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await mix_make.finish()


@elixir_back.handle(parameterless=[Cooldown(at_sender=False)])
async def elixir_back_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """丹药背包
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await elixir_back.finish()

    user_id = user_info['user_id']
    msg = get_user_elixir_back_msg(user_id)

    # 尝试获取页码
    try:
        page = int(args.extract_plain_text().strip())
    except ValueError:
        page = 1  # 如果没有提供页码或格式不正确，默认为第一页

    # 将背包数据转化为列表，便于分页
    data_list = []
    for item in msg:
        data_list.append(item)

    # 计算总页数
    total_items = len(data_list)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整

    # 检查当前页码是否有效
    if page < 1 or page > total_pages:
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"无效的页码。请输入有效的页码范围：1-{total_pages}")
        await elixir_back.finish()

    # 获取当前页的数据
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_items)
    page_data = data_list[start_idx:end_idx]

    # 合并所有消息为一个字符串
    header = f"{user_info['user_name']}的丹药背包\n"
    full_msg = header + "\n".join(page_data)

    # 添加翻页提示
    full_msg += f"\n\n第 {page}/{total_pages} 页\n使用命令 '丹药背包 {page + 1}' 查看下一页" if page < total_pages else "\n\n这是最后一页。"

    try:
        # 将所有消息作为一条消息发送
        await bot.send_group_msg(group_id=int(send_group_id), message=full_msg)
    except ActionFailed:
        await elixir_back.finish("查看丹药背包失败!", reply_message=True)

    await elixir_back.finish()


@yaocai_back.handle(parameterless=[Cooldown(at_sender=False)])
async def yaocai_back_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """药材背包
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await yaocai_back.finish()

    user_id = user_info['user_id']
    msg = get_user_yaocai_back_msg(user_id)

    # 尝试获取页码
    try:
        page = int(args.extract_plain_text().strip())
    except ValueError:
        page = 1  # 如果没有提供页码或格式不正确，默认为第一页

    # 将药材背包数据转化为列表，便于分页
    data_list = []
    for item in msg:
        data_list.append(item)

    # 计算总页数
    total_items = len(data_list)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE  # 向上取整

    # 检查当前页码是否有效
    if page < 1 or page > total_pages:
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"无效的页码。请输入有效的页码范围：1-{total_pages}")
        await yaocai_back.finish()

    # 获取当前页的数据
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_items)
    page_data = data_list[start_idx:end_idx]

    # 合并所有消息为一个字符串
    header = f"{user_info['user_name']}的药材背包\n"
    header += f"☆------拥有药材------☆\n"
    full_msg = header + "\n".join(page_data)

    # 添加翻页提示
    full_msg += f"\n\n第 {page}/{total_pages} 页\n使用命令 '药材背包 {page + 1}' 查看下一页" if page < total_pages else "\n\n这是最后一页。"

    try:
        # 将所有消息作为一条消息发送
        await bot.send_group_msg(group_id=int(send_group_id), message=full_msg)
    except ActionFailed:
        await yaocai_back.finish("查看药材背包失败!", reply_message=True)

    await yaocai_back.finish()


async def check_yaocai_name_in_back(user_id, yaocai_name, yaocai_num):
    flag = False
    goods_id = 0
    user_back = sql_message.get_back_msg(user_id)
    for back in user_back:
        if back['goods_type'] == '药材':
            if Items().get_data_by_item_id(back['goods_id'])['name'] == yaocai_name:
                if int(back['goods_num']) >= int(yaocai_num):
                    flag = True
                    goods_id = back['goods_id']
                    break
            else:
                continue
        else:
            continue
    return flag, goods_id


async def check_ldl_name_in_back(user_id, ldl_name):
    flag = False
    goods_info = {}
    user_back = sql_message.get_back_msg(user_id)
    for back in user_back:
        if back['goods_type'] == '炼丹炉':
            if back['goods_name'] == ldl_name:
                flag = True
                goods_info = Items().get_data_by_item_id(back['goods_id'])
                break
            else:
                continue
        else:
            continue
    return flag, goods_info
