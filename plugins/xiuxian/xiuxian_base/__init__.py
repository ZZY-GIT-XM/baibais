import re
import json
import base64
import random
import asyncio
from datetime import datetime
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
from ..xiuxian_config import XiuConfig, JsonConfig, convert_rank
from ..xiuxian_utils.utils import (
    check_user,
    get_msg_pic, number_to,
    CommandObjectID,
    Txt2Img, send_msg_handler
)
from ..xiuxian_utils.item_json import Items

items = Items()

# 定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler
cache_help = {}
cache_level_help = {}
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()

run_xiuxian = on_fullmatch("我要修仙", priority=8, permission=GROUP, block=True)
restart = on_fullmatch("重入仙途", permission=GROUP, priority=7, block=True)
sign_in = on_fullmatch("修仙签到", priority=13, permission=GROUP, block=True)
help_in = on_fullmatch("修仙帮助", priority=12, permission=GROUP, block=True)
rank = on_command("排行榜", aliases={"排行榜列表", "灵石排行榜", "战力排行榜", "境界排行榜", "宗门排行榜"},
                  priority=7, permission=GROUP, block=True)
remaname = on_command("改名", priority=5, permission=GROUP, block=True)
level_up = on_fullmatch("突破", priority=6, permission=GROUP, block=True)
level_up_dr = on_fullmatch("渡厄突破", priority=7, permission=GROUP, block=True)
level_up_drjd = on_command("渡厄金丹突破", aliases={"金丹突破"}, priority=7, permission=GROUP, block=True)
level_up_zj = on_command("直接突破", aliases={"破"}, priority=7, permission=GROUP, block=True)
give_stone = on_command("送灵石", priority=5, permission=GROUP, block=True)
steal_stone = on_command("偷灵石", aliases={"飞龙探云手"}, priority=4, permission=GROUP, block=True)
gm_command = on_command("神秘力量", permission=SUPERUSER, priority=10, block=True)
gmm_command = on_command("轮回力量", permission=SUPERUSER, priority=10, block=True)
cz = on_command('创造力量', permission=SUPERUSER, priority=15, block=True)
rob_stone = on_command("抢劫", aliases={"抢灵石", "拿来吧你"}, priority=5, permission=GROUP, block=True)
restate = on_command("重置状态", permission=SUPERUSER, priority=12, block=True)
set_xiuxian = on_command("启用修仙功能", aliases={'禁用修仙功能'},
                         permission=GROUP and (SUPERUSER or GROUP_ADMIN or GROUP_OWNER), priority=5, block=True)
user_leveluprate = on_command('我的突破概率', aliases={'突破概率'}, priority=5, permission=GROUP, block=True)
user_stamina = on_command('我的体力', aliases={'体力'}, priority=5, permission=GROUP, block=True)
# lunhui = on_fullmatch('轮回重修帮助', priority=15, permission=GROUP, block=True)
level_help_jingjie = on_command('境界列表', priority=15, permission=GROUP, block=True)
level_help_linggen = on_command('灵根列表', priority=15, permission=GROUP, block=True)
level_help_pinjie = on_command('品阶列表', priority=15, permission=GROUP, block=True)

__xiuxian_notes__ = f"""
修仙帮助详情：
1、我要修仙:步入修仙世界
2、我的修仙信息:获取修仙数据
3、修仙签到:获取灵石
4、重入仙途:重置灵根数据,每次{XiuConfig().remake}灵石
5、改名:随机修改你的道号
6、突破:修为足够后,可突破境界（一定几率失败）
7、闭关、出关、灵石出关、灵石修炼、双修:增加修为
8、送灵石100@xxx,偷灵石@xxx,抢灵石@xxx
9、排行榜:修仙排行榜,灵石排行榜,战力排行榜,宗门排行榜
10、悬赏令帮助:获取悬赏令帮助信息
11、我的状态:查看当前HP,我的功法：查看当前技能
12、宗门系统:发送 宗门帮助 获取
13、灵庄系统:发送 灵庄帮助 获取
14、世界BOSS:发送 世界boss帮助 获取
15、功法/灵田：发送 功法帮助/灵田帮助 查看
16、背包/拍卖：发送 背包帮助 获取
17、秘境系统:发送 秘境帮助 获取
18、炼丹帮助:炼丹功能
19、传承系统:发送 传承帮助/虚神界帮助 获取
20、启用/禁用修仙功能：当前群开启或关闭修仙功能
21、仙途奇缘:发送 仙途奇缘帮助 获取
22、轮回重修:发送 轮回重修帮助 获取
23、境界列表、灵根列表、品阶列表:获取对应列表信息
24、仙器合成:发送 合成xx 获取，目前开放合成的仙器为天罪
""".strip()

__level_help_jingjie__ = """
--境界列表--
祭道境——仙帝境——虚神境——轮回境
金仙境——创世境——混沌境——斩我境
虚道境——天神境——圣祭境——真一境
神火境——尊者境——列阵境——铭纹境
化灵境——洞天境——搬血境——江湖人
""".strip()

__level_help_linggen__ = """
--灵根列表--
轮回——异界——机械——混沌
融——超——龙——天——异——真——伪
""".strip()

__level_help_pinjie__ = """
--功法品阶--
无上
仙阶极品
仙阶上品——仙阶下品
天阶上品——天阶下品
地阶上品——地阶下品
玄阶上品——玄阶下品
黄阶上品——黄阶下品
人阶上品——人阶下品

--法器品阶--
无上
极品仙器
上品仙器——下品仙器
上品通天——下品通天
上品纯阳——下品纯阳
上品法器——下品法器
上品符器——下品符器
""".strip()


# 重置每日签到
@scheduler.scheduled_job("cron", hour=0, minute=0)
async def xiuxian_sing_():
    sql_message.sign_remake()
    logger.opt(colors=True).info(f"<green>每日修仙签到重置成功！</green>")

# 姓氏列表
surnames = [
    "赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "褚", "卫", "蒋", "沈", "韩", "杨", "朱", "秦",
    "尤", "许", "何", "吕", "施", "张", "孔", "曹", "严", "华", "金", "魏", "陶", "姜", "戚", "谢", "邹", "喻",
    "柏", "水", "窦", "章", "云", "苏", "潘", "葛", "奚", "范", "彭", "郎", "鲁", "韦", "昌", "马", "苗", "凤",
    "花", "方", "俞", "任", "袁", "柳", "酆", "鲍", "史", "唐", "费", "廉", "柯", "毕", "郝", "邬", "安", "常",
    "乐", "于", "时", "傅", "皮", "卞", "齐", "康", "伍", "余", "元", "卜", "顾", "孟", "平", "黄", "和", "穆",
    "萧", "尹", "姚", "邵", "湛", "汪", "祁", "毛", "禹", "狄", "米", "贝", "明", "臧", "计", "伏", "成", "戴",
    "谈", "宋", "茅", "庞", "熊", "纪", "舒", "屈", "项", "祝", "董", "沈", "连", "牟", "凌", "耿", "康", "井",
    "段", "富", "巫", "乌", "焦", "巴", "谷", "车", "侯", "宓", "蓬", "全", "郗", "班", "仰", "秋", "仲", "伊",
    "宫", "宁", "仇", "栾", "暴", "甘", "钭", "厉", "戎", "祖", "武", "符", "刘", "景", "詹", "束", "龙", "叶",
    "幸", "司", "琉璃", "上官", "欧阳", "东方", "西门", "南宫", "北冥", "公孙", "独孤", "慕容", "司马", "令狐",
    "诸葛", "端木", "尉迟", "公羊", "司空", "轩辕", "皇甫", "宇文", "长孙", "拓跋", "呼延", "太叔", "子车",
    "灵", "幻", "真", "圣", "神", "仙", "魔", "妖", "鬼",
    "云", "风", "雷", "电", "火", "水", "木", "金", "土", "山", "海", "天", "地", "星", "月", "日", "雪", "冰", "霜",
    "松", "竹", "梅", "兰", "花", "草", "柳", "桃", "荷", "菊", "枫", "杉", "柏", "桂", "樱", "槐", "杏", "梨",
    "龙", "凤", "鹤", "鹰", "虎", "豹", "狼", "鹿", "鹤", "熊", "猿", "狐"
]

# 名字字符列表
names_characters = [
    # 数字
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    # 十二地支
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
    # 十天干
    "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸",
    # 自然
    "天", "地", "人", "和", "风", "云", "雷", "电", "雨", "雪", "山", "水", "火", "木", "金", "土",
    # 季节
    "春", "夏", "秋", "冬",
    # 时间
    "晨", "暮", "夜", "昼",
    # 动物
    "龙", "虎", "豹", "狼", "鹿", "鹤", "鹰", "鸟", "鱼", "蛇", "鼠", "牛", "马", "羊", "猴", "鸡", "狗", "猪",
    # 更多动物
    "兔", "猫", "象", "狮", "熊", "燕", "蝶", "蛙", "蜂", "蚁", "龟", "鹅", "鸭", "鸽", "狐", "狸",
    # 颜色
    "红", "绿", "蓝", "黄", "黑", "白", "紫", "橙", "棕", "灰", "青", "褐",
    # 植物
    "花", "草", "树", "叶", "果", "根", "茎", "枝", "松", "竹", "梅", "兰",
    # 情感
    "喜", "怒", "哀", "乐", "爱", "恨", "悲", "欢", "笑", "哭",
    # 文化
    "诗", "书", "画", "琴", "棋", "茶", "酒", "歌", "舞", "乐",
    # 道德品质
    "仁", "义", "礼", "智", "信", "忠", "孝", "悌", "勇", "诚", "谦", "敬", "慈", "善", "勇", "智",
    # 抽象概念
    "灵", "玄", "幻", "真", "圣", "神", "仙", "魔", "妖", "鬼", "侠", "客", "师", "徒", "道", "法", "剑", "刀", "弓", "箭",
    # 日常物品
    "墨", "灯", "镜", "晨曦", "晚霞", "明岚", "静澜", "沐清", "素心", "梦璃", "琪瑶", "淳风", "靖宇", "景云", "涵烟", "灿星", "淼淼",
    "苍穹", "潇雨", "落英", "烟波", "青岚", "梓萱", "楚歌", "琪瑞", "桃夭", "柳絮", "菊香", "松涛", "梅香", "竹韵", "荷露", "逸尘", "仙羽",
    "玄机", "灵均", "清扬", "慧空", "静逸", "明岚", "沐风", "安歌", "飞鸿", "智渊", "明澈", "悠然", "心怡", "静思", "晓月", "明轩"
]

def generate_random_name(length_range=(3, 5)):
    """随机生成名称"""
    min_length, max_length = length_range
    total_length = random.randint(min_length, max_length)

    # 选择一个姓氏
    surname = random.choice(surnames)

    # 计算名字长度
    name_length = max(1, total_length - len(surname))

    # 选择名字
    name = ''.join(random.choices(names_characters, k=name_length))

    # 返回姓和名的组合
    return surname + name


@run_xiuxian.handle(parameterless=[Cooldown(at_sender=False)])
async def run_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """加入修仙"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    # 生成随机名字
    user_name = generate_random_name()
    root, root_type = XiuxianJsonDate().linggen_get()  # 获取灵根，灵根类型
    rate = sql_message.get_root_rate(root_type)  # 灵根倍率
    power = 100 * float(rate)  # 战力=境界的power字段 * 灵根的rate字段
    create_time = str(datetime.now())
    is_new_user, msg = sql_message.create_user(
        user_id, root, root_type, int(power), create_time, user_name
    )
    try:
        if is_new_user:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            isUser, user_msg, msg = check_user(event)
            if user_msg['hp'] is None or user_msg['hp'] == 0 or user_msg['hp'] == 0:
                sql_message.update_user_hp(user_id)
            await asyncio.sleep(1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    except ActionFailed:
        await run_xiuxian.finish("修仙界网络堵塞，发送失败!", reply_message=True)


@sign_in.handle(parameterless=[Cooldown(at_sender=False)])
async def sign_in_(bot: Bot, event: GroupMessageEvent):
    """修仙签到"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await sign_in.finish()
    user_id = user_info['user_id']
    result = sql_message.get_sign(user_id)
    msg = result
    try:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await sign_in.finish()
    except ActionFailed:
        await sign_in.finish("修仙界网络堵塞，发送失败!", reply_message=True)


@help_in.handle(parameterless=[Cooldown(at_sender=False)])
async def help_in_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """修仙帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await help_in.finish()
    else:
        # markdown 模版代入
        # md = {"markdown": {"custom_template_id": "102125567_1723942446"},"keyboard": {"id": "102125567_1723650390"}}
        md = {"keyboard": {"id": "102125567_1726457258"}}
        json1 = json.dumps(md)
        bytes = json1.encode('utf-8')
        data = base64.b64encode(bytes).decode('utf-8')
        msg = __xiuxian_notes__
        markdown_message = f"[CQ:markdown,data=base64://{data}]" + msg
        await bot.send_group_msg(group_id=int(send_group_id), message=markdown_message)
        await help_in.finish()


@level_help_jingjie.handle(parameterless=[Cooldown(at_sender=False)])
async def level_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """境界列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __level_help_jingjie__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await level_help_jingjie.finish()


@level_help_linggen.handle(parameterless=[Cooldown(at_sender=False)])
async def level_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """灵根列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __level_help_linggen__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await level_help_linggen.finish()


@level_help_pinjie.handle(parameterless=[Cooldown(at_sender=False)])
async def level_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """品阶列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __level_help_pinjie__
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await level_help_pinjie.finish()


@restart.handle(parameterless=[Cooldown(at_sender=False)])
async def restart_(bot: Bot, event: GroupMessageEvent, state: T_State):
    """刷新灵根信息"""
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
    """修改道号"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await remaname.finish()

    user_id = user_info['user_id']
    user_name = generate_random_name()  # 生成随机名字
    msg = sql_message.update_user_name(user_id, user_name)  # 更新数据库中的名字记录
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
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
        percentage = random.randint(
            XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit
        )
        now_exp = int(int(exp) * ((percentage / 100) * (1 - exp_buff)))  # 功法突破扣修为减少
        sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
        nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else 1
        nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else 1
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


@user_stamina.handle(parameterless=[Cooldown(at_sender=False)])
async def user_stamina_(bot: Bot, event: GroupMessageEvent):
    """我的体力信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)

    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await user_stamina.finish()

    msg = f"{user_info['user_name']} 当前体力：{user_info['user_stamina']}"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await user_stamina.finish()


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


@gm_command.handle(parameterless=[Cooldown(at_sender=False)])
async def gm_command_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """神秘力量 GM加灵石"""
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
            await gm_command.finish()
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await gm_command.finish()
    else:
        sql_message.update_ls_all(give_stone_num)
        msg = f"全服通告：赠送所有用户{number_to(give_stone_num)}灵石,请注意查收！"
        enabled_groups = JsonConfig().get_enabled_groups()

        for group_id in enabled_groups:
            bot = await assign_bot_group(group_id=group_id)
            try:
                await bot.send_group_msg(group_id=int(group_id), message=msg)
            except ActionFailed:  # 发送群消息失败
                continue
        await gm_command.finish()


@cz.handle(parameterless=[Cooldown(at_sender=False)])
async def cz_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """创造力量 不输入道号 默认送给所有人 例如：创造力量 物品 数量 道号"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip().split()

    if not args:
        msg = f"请输入正确指令！例如：创造力量 物品 数量"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await cz.finish()

    if len(msg) < 2:
        msg = f"请输入正确的物品名称和数量！例如：创造力量 物品 数量"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await cz.finish()

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
        await cz.finish()

    goods_num = int(msg[1]) if msg[1].isdigit() else 1

    if len(msg) > 2:
        nick_name = ' '.join(msg[2:])
        give_user = sql_message.get_user_info_with_name(nick_name.strip())
        if give_user:
            sql_message.send_back(give_user['user_id'], goods_id, goods_name, goods_type, goods_num, 1)
            msg = f"{give_user['user_name']}道友获得了系统赠送的{goods_name}个{goods_num}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await cz.finish()
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await cz.finish()
    else:
        all_users = sql_message.get_all_user_id()
        for user_id in all_users:
            sql_message.send_back(user_id, goods_id, goods_name, goods_type, goods_num, 1)  # 给每个用户发送物品

        msg = f"全服通告：赠送所有用户{goods_name}个{goods_num},请注意查收！"
        enabled_groups = JsonConfig().get_enabled_groups()
        for group_id in enabled_groups:
            bot = await assign_bot_group(group_id=group_id)
            try:
                await bot.send_group_msg(group_id=int(group_id), message=msg)
            except ActionFailed:  # 发送群消息失败
                continue
        await cz.finish()


@gmm_command.handle(parameterless=[Cooldown(at_sender=False)])
async def gmm_command_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """GM改灵根"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip().split()

    if not args:
        msg = "请输入正确指令！例如：轮回力量 用户名称 x(1为混沌,2为融合,3为超,4为龙,5为天,6为千世,7为万世)"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gmm_command.finish()

    if len(msg) < 2:
        msg = "请输入正确的用户名称和灵根编号！例如：轮回力量 用户名称 1"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gmm_command.finish()

    nick_name = msg[0]
    root_type = msg[1]

    give_user = sql_message.get_user_info_with_name(nick_name.strip())
    if give_user:
        root_name = sql_message.update_root(give_user['user_id'], root_type)
        sql_message.update_power2(give_user['user_id'])
        msg = f"{give_user['user_name']}道友的灵根已变更为{root_name}！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gmm_command.finish()
    else:
        msg = "对方未踏入修仙界，不可修改！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gmm_command.finish()


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

            if convert_rank(user_2['level'])[0] - convert_rank(user_info['level'])[0] >= 12:
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
            atk_with_poxian1 = (user_info['atk']+user1_maxA) * (1 + total_poxian_percent1 / 100)
            atk_with_poxian2 = (user_2['atk']+user2_maxA) * (1 + total_poxian_percent2 / 100)
            hp_with_poxian1 = (user_info['hp']+user1_maxH) * (1 + total_poxian_percent1 / 100)
            hp_with_poxian2 = (user_2['hp']+user2_maxH) * (1 + total_poxian_percent2 / 100)
            mp_with_poxian1 = (user_info['mp']+user1_maxM) * (1 + total_poxian_percent1 / 100)
            mp_with_poxian2 = (user_2['mp']+user2_maxM) * (1 + total_poxian_percent2 / 100)

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


@restate.handle(parameterless=[Cooldown(at_sender=False)])
async def restate_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """重置用户状态。
    单用户：重置状态 [用户名]
    多用户：重置状态"""

    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await restate.finish()

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
            await restate.finish()
        else:
            msg = f"未找到用户 {input_name}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await restate.finish()
    else:
        sql_message.restate()
        msg = f"所有用户信息重置成功！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await restate.finish()


@set_xiuxian.handle()
async def open_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """群修仙开关配置 启用/禁用修仙功能"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_msg = str(event.message)
    group_id = str(event.group_id)
    conf_data = JsonConfig().read_data()

    if "启用" in group_msg:
        if group_id in conf_data["group"]:
            msg = "当前群聊修仙模组已启用，请勿重复操作！"
            await bot.send_group_msg(group_id=int(send_group_id), message=f"@{event.sender.nickname}\n" + msg)
            await set_xiuxian.finish()
        JsonConfig().write_data(1, group_id)
        msg = "当前群聊修仙基础模组已启用，快发送 我要修仙 加入修仙世界吧！"
        await bot.send_group_msg(group_id=int(send_group_id), message=f"@{event.sender.nickname}\n" + msg)
        await set_xiuxian.finish()

    elif "禁用" in group_msg:
        if group_id not in conf_data["group"]:
            msg = "当前群聊修仙模组已禁用，请勿重复操作！"
            await bot.send_group_msg(group_id=int(send_group_id), message=f"@{event.sender.nickname}\n" + msg)
            await set_xiuxian.finish()
        JsonConfig().write_data(2, group_id)
        msg = "当前群聊修仙基础模组已禁用！"
        await bot.send_group_msg(group_id=int(send_group_id), message=f"@{event.sender.nickname}\n" + msg)
        await set_xiuxian.finish()
    else:
        msg = "指令错误，请输入：启用修仙功能/禁用修仙功能"
        await bot.send_group_msg(group_id=int(send_group_id), message=f"@{event.sender.nickname}\n" + msg)
        await set_xiuxian.finish()
