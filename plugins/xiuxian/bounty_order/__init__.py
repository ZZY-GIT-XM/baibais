import json
import random
from datetime import datetime
from typing import Any, Tuple, Dict

import psycopg2
from nonebot import on_regex, on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent
)
from nonebot.params import RegexGroup
from psycopg2 import extras

from plugins.xiuxian.xiuxian_utils.xiuxian2_handle import sql_message, XiuxianJsonDate
from ..xiuxian_utils.item_database_handler import Items
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.utils import check_user, check_user_type
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage

# 数据库连接配置
DB_CONFIG = {
    'dbname': 'baibaidb',
    'user': 'postgres',
    'password': 'robots666',
    'host': 'localhost',
    'port': '5432'
}


def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(**DB_CONFIG)


def initialize_database():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 创建表的 SQL 语句
    create_tables_sql = """
    -- 创建xiuxian_xuanshang_info表，存储悬赏令信息
    CREATE TABLE IF NOT EXISTS xiuxian_xuanshang_info (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        user_id NUMERIC NOT NULL, -- 用户ID
        task_data JSONB NOT NULL, -- 悬赏令数据
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认为当前时间
    );

    -- 创建xiuxian_xuanshang_jichu表，存储悬赏令基本信息
    CREATE TABLE IF NOT EXISTS xiuxian_xuanshang_jichu (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        task_type TEXT NOT NULL, -- 任务类型
        role TEXT NOT NULL, -- 接取需要的境界
        task_name TEXT NOT NULL, -- 任务名称
        level TEXT NOT NULL, -- 难度等级
        succeed TEXT NOT NULL, -- 成功消息
        fail TEXT NOT NULL -- 失败消息
    );

    -- 创建xiuxian_xuanshang_jiangli_jichu表，存储悬赏令奖励信息
    CREATE TABLE IF NOT EXISTS xiuxian_xuanshang_jiangli_jichu (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        role TEXT, -- 接取需要的境界
        level TEXT NOT NULL, -- 难度等级
        award NUMERIC NOT NULL, -- 基础奖励
        needexp NUMERIC NOT NULL, -- 需要的经验标准
        time INT NOT NULL -- 任务的时间(分钟)
    );
    """

    cursor.execute(create_tables_sql)
    conn.commit()
    cursor.close()
    conn.close()


def get_work_info(user_id):
    # 连接到 PostgreSQL 数据库
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    # 查询特定用户的任务信息
    query = """
    SELECT task_data
    FROM xiuxian_xuanshang_info
    WHERE user_id = %s
    ORDER BY created_at DESC
    LIMIT 1;
    """
    cur.execute(query, (user_id,))
    result = cur.fetchone()

    # 关闭游标和连接
    cur.close()
    conn.close()

    if result and 'task_data' in result:
        # 确保 task_data 是字符串形式的 JSON 数据
        if isinstance(result['task_data'], str):
            task_data = json.loads(result['task_data'])
            return task_data
        else:
            # 如果 task_data 是字典，将其转换为字符串
            task_data_str = json.dumps(result['task_data'])
            task_data = json.loads(task_data_str)
            return task_data
    else:
        return {}


class RewardHandler:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()

    def fetch_data(self, table, task_type=None):
        query = f"SELECT * FROM {table}"
        if task_type:
            query += f" WHERE task_type = '{task_type}'"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.conn.close()


def workmake(work_level, exp, user_level, db_config):
    work_level = work_level[:3]  # 统一处理境界长度
    handler = RewardHandler(db_config)
    yaocai_data = handler.fetch_data('xiuxian_xuanshang_jichu', '药材')
    ansha_data = handler.fetch_data('xiuxian_xuanshang_jichu', '暗杀')
    zuoyao_data = handler.fetch_data('xiuxian_xuanshang_jichu', '镇妖')
    levelpricedata = handler.fetch_data('xiuxian_xuanshang_jiangli_jichu')
    handler.close()
    work_json = {}
    work_types = [('药材', yaocai_data), ('暗杀', ansha_data), ('镇妖', zuoyao_data)]
    for work_type, work_data in work_types:
        work_name_list = [row[3] for row in work_data if row[2] == work_level]
        work_name = random.choice(work_name_list)
        work_info = next((row for row in work_data if row[3] == work_name), None)
        level_price_data = next((row for row in levelpricedata if row[1] == work_level and row[2] == work_info[4]),
                                None)
        rate, isOut = countrate(exp, level_price_data[4])
        success_msg = work_info[5]
        fail_msg = work_info[6]
        item_type = get_random_item_type()

        item_id = Items().get_random_id_list_by_rank_and_item_type(Items().convert_rank(user_level)[0], item_type)
        item_id = random.choice(item_id) if item_id else 0
        work_json[work_name] = [rate, int(level_price_data[3]), int(level_price_data[5] * isOut), item_id, success_msg,
                                fail_msg]
    return work_json


def get_random_item_type():
    type_rate = {"功法": 500, "神通": 50, "药材": 500}
    total_rate = sum(type_rate.values())
    rand = random.uniform(0, total_rate)
    current_rate = 0
    for item_type, rate in type_rate.items():
        current_rate += rate
        if rand <= current_rate:
            return [item_type]  # 返回一个包含单个字符串的列表
    return ["药材"]  # 返回一个包含单个字符串的列表


def countrate(exp, needexp):
    exp, needexp = float(exp), float(needexp)
    rate = int(exp / needexp * 100)
    isOut = 1
    if rate >= 100:
        tp = 1
        while exp / needexp * 100 > 100:
            tp += 1
            exp /= 1.5
        rate = 100
        isOut = max(0.5, 1 - tp * 0.05)
    return rate, round(isOut, 2)


class WorkHandler(XiuxianJsonDate):
    def __init__(self, db_config):
        super().__init__()
        self.db_config = db_config
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()

    def do_work(self, key, user_id, level=None, exp=None, name=None, work_list=None):
        """悬赏令获取"""
        if key == 0:  # 悬赏令获取
            data = workmake(level, exp, sql_message.get_user_info_with_id(user_id)['level'], self.db_config)
            get_work_list = [[k, v[0], v[1], v[2], v[3]] for k, v in data.items()]
            self.save_work_info(user_id, data)
            return get_work_list

        elif key == 1:  # 悬赏令获取详情
            data = get_work_info(user_id)
            return data.get(name, [None, None, None, None, None, None])[2]

        elif key == 2:  # 结算悬赏令
            data = get_work_info(user_id)
            target_work = next((details for name, details in data.items() if name == work_list), None)
            if target_work:
                success = random.randint(1, 100) <= target_work[0]
                big_success = target_work[0] >= 100
                reward_stone = target_work[1] * (2 if big_success else 1)
                reward_item_id = target_work[3]
                outcome_msg = target_work[4] if success else target_work[5]
                self.remove_work_info(user_id)
                return outcome_msg, reward_stone, success, reward_item_id, big_success
            return None

    def save_work_info(self, user_id, data):
        # 检查 user_id 是否已经存在
        self.cursor.execute("SELECT * FROM xiuxian_xuanshang_info WHERE user_id = %s", (user_id,))
        existing_record = self.cursor.fetchone()

        if existing_record:
            # 更新现有记录
            self.cursor.execute("UPDATE xiuxian_xuanshang_info SET task_data = %s::jsonb WHERE user_id = %s",
                                (json.dumps(data), user_id))
        else:
            # 插入新记录
            self.cursor.execute("INSERT INTO xiuxian_xuanshang_info (user_id, task_data) VALUES (%s, %s::jsonb)",
                                (user_id, json.dumps(data)))

        self.conn.commit()

    # def get_work_info(self, user_id):
    #     self.cursor.execute("SELECT task_data FROM xiuxian_xuanshang_info WHERE user_id = %s", (user_id,))
    #     result = self.cursor.fetchone()
    #     return json.loads(result[0]) if result else []

    def remove_work_info(self, user_id):
        # 确保 user_id 是一个整数
        user_id = int(user_id)
        self.cursor.execute("DELETE FROM xiuxian_xuanshang_info WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()


work = {}  # 悬赏令信息记录
sql_message = XiuxianDateManage()  # sql类
items = Items()
user_work_nums = 3  # 免费次数

last_work = on_command("最后的悬赏令", priority=15, block=True)
do_work = on_regex(
    r"^悬赏令(刷新|终止|结算|接取)?(\d+)?",
    priority=10,
    permission=GROUP,
    block=True
)


@last_work.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
async def last_work_(bot: Bot, event: GroupMessageEvent):
    """最后的悬赏令"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await last_work.finish()
    user_id = user_info['user_id']
    user_level = user_info['level']
    user_rank = Items().convert_rank(user_level)[0]
    is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
    if is_type and user_rank <= 11:
        user_cd_message = sql_message.get_user_cd(user_id)
        work_time = datetime.strptime(user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f")
        exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
        time2 = WorkHandler(DB_CONFIG).do_work(key=1, user_id=user_id,
                                               name=user_cd_message['scheduled_time'])
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await last_work.finish()
        else:
            msg, give_stone, _, item_id, _ = WorkHandler(DB_CONFIG).do_work(2, user_id=user_info['user_id'],
                                                                            work_list=user_cd_message['scheduled_time'])
            item_msg = f"，额外获得奖励：{items.get_data_by_item_id(item_id)['name']}!" if item_id else "!"
            sql_message.update_ls(user_id, give_stone, 1)
            sql_message.do_work(user_id, 0)
            await bot.send_group_msg(group_id=int(send_group_id),
                                     message=f"悬赏令结算，{msg}获得报酬{give_stone}枚灵石{item_msg}")
            await last_work.finish()
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message="不满足使用条件！")
        await last_work.finish()


@do_work.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
async def do_work_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup(), work={}):
    """悬赏令(刷新|终止|结算|接取)"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()
    user_id = user_info['user_id']
    user_level = user_info['level']
    user_rank = Items().convert_rank(user_level)[0]
    user_cd_message = sql_message.get_user_cd(user_id)

    if user_rank <= 11 or user_info['exp'] >= sql_message.get_level_power("金仙境圆满"):
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message="道友的境界已过创业的初期，悬赏令已经不能满足道友了！")
        await do_work.finish()

    if user_cd_message['type'] == 1:
        await bot.send_group_msg(group_id=int(send_group_id), message="已经在闭关中，请输入【出关】结束后才能获取悬赏令！")
        await do_work.finish()

    if user_cd_message['type'] == 3:
        await bot.send_group_msg(group_id=int(send_group_id), message="道友在秘境中，请等待结束后才能获取悬赏令！")
        await do_work.finish()

    if user_cd_message['type'] == 4:
        now_time = datetime.now()
        in_closing_time = datetime.strptime(str(user_cd_message['create_time']), "%Y-%m-%d %H:%M:%S.%f")  # 预计修炼结束的时间
        seconds_diff = (in_closing_time - now_time).total_seconds()
        remaining_seconds = int(seconds_diff)
        if remaining_seconds > 0:
            msg = f"道友正在修炼中，{remaining_seconds} 秒后结束！"
        else:
            # 如果修炼已经结束，更新状态
            sql_message.in_closing(user_id, 0)
            msg = "修炼已结束，请重新刷新悬赏令！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()

    mode = args[0]  # 操作模式

    if mode == "刷新":
        # stone_use = 0  # 悬赏令刷新提示是否扣灵石
        if user_cd_message['type'] == 2:
            await bot.send_group_msg(group_id=int(send_group_id), message="请先结算当前悬赏令！")
            await do_work.finish()

        user_work_num = sql_message.get_work_num(user_id) # 获取用户当日已刷新次数

        if user_work_num >= user_work_nums:
                await bot.send_group_msg(group_id=int(send_group_id),message=f"道友今日的悬赏令刷新次数已用尽!")
                await do_work.finish()

        work_list = WorkHandler(DB_CONFIG).do_work(0, user_id=user_id, level=user_level, exp=user_info['exp'])
        msg = "☆------道友的个人悬赏令------☆\n"
        for idx, work_info in enumerate(work_list, start=1):
            if work_info[4] == 0:
                item_msg = '!'
            else:
                item_info = Items().get_data_by_item_id(work_info[4])
                item_msg = f"，可能额外获得：{item_info['level']}:{item_info['name']}!"
            msg += f"{idx}. {work_info[0]}, 完成概率{work_info[1]}%, 基础报酬{work_info[2]}修为, 预计需{work_info[3]}分钟{item_msg}\n"
        msg += f"(悬赏令每日刷新次数：{user_work_nums}，今日可刷新次数：{user_work_nums-user_work_num-1}次)"
        sql_message.update_work_num(user_id, user_work_num+1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()

    elif mode == "接取":
        num = args[1]
        if not num or not num.isdigit() or int(num) not in range(1, 4):
            await bot.send_group_msg(group_id=int(send_group_id), message="请输入正确的任务序号")
            await do_work.finish()

        if user_cd_message['type'] == 2:
            await bot.send_group_msg(group_id=int(send_group_id), message="请先结算当前悬赏令！")
            await do_work.finish()
        work = get_work_info(user_id)
        work_info = []
        for task_name, task_details in work.items():
            work_info.append({
                'task_name': task_name,
                'details': task_details
            })

        if not work_info:
            await bot.send_group_msg(group_id=int(send_group_id), message="没有查到你的悬赏令信息呢，请刷新！")
            await do_work.finish()

        selected_work = work_info[int(num) - 1]
        sql_message.do_work(user_id, 2, selected_work['task_name'])
        await bot.send_group_msg(group_id=int(send_group_id), message=f"接取任务【{selected_work['task_name']}】成功")
        await do_work.finish()

    elif mode == "结算":
        user_cd_message = sql_message.get_user_cd(user_id)
        if user_cd_message['type'] != 2:
            await bot.send_group_msg(group_id=int(send_group_id), message="没有正在进行的悬赏令！")
            await do_work.finish()
        create_time_str = str(user_cd_message['create_time'])
        work_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S.%f")
        exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
        time2 = WorkHandler(DB_CONFIG).do_work(1, user_id=user_id,name=user_cd_message['scheduled_time'])
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await last_work.finish()

        work_name = user_cd_message['scheduled_time']
        msg, give_stone, success, item_id, big_success = WorkHandler(DB_CONFIG).do_work(2, user_id=user_id,
                                                                                        work_list=work_name)
        item_msg = f"，额外获得奖励：{items.get_data_by_item_id(item_id)['name']}!" if item_id else "!"

        if big_success:  # 大成功
            sql_message.update_exp(user_id, give_stone * 2)
            sql_message.update_ls(user_id, give_stone, 1)
            sql_message.do_work(user_id, 0)
            msg = f"悬赏令结算，{msg}获得报酬{give_stone}枚灵石，增加修为{give_stone * 2}{item_msg}"
        else:
            sql_message.update_exp(user_id, give_stone)
            sql_message.update_ls(user_id, give_stone, 1)
            sql_message.do_work(user_id, 0)
            msg = f"悬赏令结算，{msg}获得报酬{give_stone}枚灵石，增加修为{give_stone}{item_msg}"

        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await do_work.finish()

    elif mode == "终止":
        if user_cd_message['type'] != 2:
            await bot.send_group_msg(group_id=int(send_group_id), message="没有正在进行的悬赏令！")
            await do_work.finish()

        cost = 4000000
        sql_message.update_ls(user_id, cost, 2)
        sql_message.do_work(user_id, 0)
        await bot.send_group_msg(group_id=int(send_group_id),
                                 message=f"道友不讲诚信，被打了一顿灵石减少{cost},悬赏令已终止！")
        await do_work.finish()

    else:
        await bot.send_group_msg(group_id=int(send_group_id), message="请输入正确的操作指令！")
        await do_work.finish()

# class reward:
#     def __init__(self, db_config):
#         self.db_config = db_config
#         self.conn = psycopg2.connect(**db_config)
#         self.cursor = self.conn.cursor()
#
#     def reward_ansa_data(self):
#         """获取暗杀名单信息"""
#         query = "SELECT * FROM xiuxian_xuanshang_jichu WHERE task_type = '暗杀';"
#         self.cursor.execute(query)
#         data = self.cursor.fetchall()
#         return data
#
#     def reward_levelprice_data(self):
#         """获取等级奖励信息"""
#         query = "SELECT * FROM xiuxian_xuanshang_jiangli_jichu;"
#         self.cursor.execute(query)
#         data = self.cursor.fetchall()
#         return data
#
#     def reward_yaocai_data(self):
#         """获取药材信息"""
#         query = "SELECT * FROM xiuxian_xuanshang_jichu WHERE task_type = '药材';"
#         self.cursor.execute(query)
#         data = self.cursor.fetchall()
#         return data
#
#     def reward_zuoyao_data(self):
#         """获取捉妖信息"""
#         query = "SELECT * FROM xiuxian_xuanshang_jichu WHERE task_type = '镇妖';"
#         self.cursor.execute(query)
#         data = self.cursor.fetchall()
#         return data
#
#     def close(self):
#         self.cursor.close()
#         self.conn.close()

# def workmake(work_level, exp, user_level, db_config):
#     if work_level == '江湖好手':
#         work_level = '江湖好手'
#     else:
#         work_level = work_level[:3]  # 取境界前3位，补全初期、中期、圆满任务可不取
#
#     jsondata_ = reward(db_config)
#     item_s = Items()
#     yaocai_data = jsondata_.reward_yaocai_data()
#     levelpricedata = jsondata_.reward_levelprice_data()
#     ansha_data = jsondata_.reward_ansa_data()
#     zuoyao_data = jsondata_.reward_zuoyao_data()
#     jsondata_.close()
#
#     work_json = {}
#     work_list = [yaocai_data, ansha_data, zuoyao_data]
#     i = 1
#     for w in work_list:
#         work_name_list = []
#         for row in w:
#             if row[1] == work_level:  # 假设第2列是境界
#                 work_name_list.append(row[3])  # 假设第4列是任务名称
#         work_name = random.choice(work_name_list)
#         work_info = next((row for row in w if row[3] == work_name), None)
#         level_price_data = next((row for row in levelpricedata if row[1] == work_level and row[2] == work_info[4]), None)
#         rate, isOut = countrate(exp, level_price_data[3])
#         success_msg = work_info[5]
#         fail_msg = work_info[6]
#         item_type = get_random_item_type()
#         item_id = item_s.get_random_id_list_by_rank_and_item_type(Items().convert_rank(user_level)[0], item_type)
#         if not item_id:
#             item_id = 0
#         else:
#             item_id = random.choice(item_id)
#         work_json[work_name] = [rate, level_price_data[2], int(level_price_data[4] * isOut), item_id, success_msg, fail_msg]
#         i += 1
#     return work_json

# def get_random_item_type():
#     type_rate = {
#         "功法": {
#             "type_rate": 500,
#         },
#         "神通": {
#             "type_rate": 50,
#         },
#         "药材": {
#             "type_rate": 500,
#         }
#     }
#     temp_dict = {}
#     for i, v in type_rate.items():
#         try:
#             temp_dict[i] = v["type_rate"]
#         except:
#             continue
#     key = [OtherSet().calculated(temp_dict)]
#     return key

# def countrate(exp, needexp):
#     # 确保 exp 和 needexp 都是 float 类型
#     exp = float(exp)
#     needexp = float(needexp)
#
#     rate = int(exp / needexp * 100)
#     isOut = 1
#
#     if rate >= 100:
#         tp = 1
#         flag = True
#         while flag:
#             r = exp / needexp * 100
#             if r > 100:
#                 tp += 1
#                 exp /= 1.5
#             else:
#                 flag = False
#
#         rate = 100
#         isOut = float(1 - tp * 0.05)
#         if isOut < 0.5:
#             isOut = 0.5
#
#     return rate, round(isOut, 2)

# class workhandle(XiuxianJsonDate):
#     def __init__(self, db_config):
#         super().__init__()
#         self.db_config = db_config
#         self.conn = psycopg2.connect(**db_config)
#         self.cursor = self.conn.cursor()
#
#     def do_work(self, key, work_list=None, name=None, level="江湖好手", exp=None, user_id=None):
#         """悬赏令获取"""
#         if key == 0:  # 如果没有获取过，则返回悬赏令
#             data = workmake(level, exp, sql_message.get_user_info_with_id(user_id)['level'])
#             get_work_list = []
#             for k, v in data.items():
#                 if v[3] == 0:
#                     item_msg = '!'
#                 else:
#                     item_info = Items().get_data_by_item_id(v[3])
#                     item_msg = f"，可能额外获得：{item_info['level']}:{item_info['name']}!"
#                 get_work_list.append([k, v[0], v[1], v[2], item_msg])
#             self.save_work_info(user_id, data)
#             return get_work_list
#
#         if key == 1:  # 返回对应的悬赏令信息
#             data = self.get_work_info(user_id)
#             if data:
#                 for row in data:
#                     if row[2] == name:
#                         return row[4]
#             return None
#
#         elif key == 2:  # 如果是结算，则获取结果
#             data = self.get_work_info(user_id)
#             if data:
#                 for row in data:
#                     if row[2] == work_list:
#                         bigsuc = False
#                         if row[0] >= 100:
#                             bigsuc = True
#
#                         success_msg = row[5]
#                         fail_msg = row[6]
#                         item_id = row[3]
#
#                         if random.randint(1, 100) <= row[0]:
#                             return success_msg, row[1], True, item_id, bigsuc
#                         else:
#                             return fail_msg, int(row[1] / 2), False, 0, bigsuc
#             return None
#
#     def save_work_info(self, user_id, data):
#         insert_query = "INSERT INTO xiuxian_xuanshang_info (user_id, task_data) VALUES (%s, %s);"
#         task_data = json.dumps(data, ensure_ascii=False)
#         self.cursor.execute(insert_query, (user_id, task_data))
#         self.conn.commit()
#
#     def get_work_info(self, user_id):
#         select_query = "SELECT task_data FROM xiuxian_xuanshang_info WHERE user_id = %s;"
#         self.cursor.execute(select_query, (user_id,))
#         result = self.cursor.fetchone()
#         if result:
#             return json.loads(result[0])
#         return []
#
#     def close(self):
#         self.cursor.close()
#         self.conn.close()


# @last_work.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
# async def last_work_(bot: Bot, event: GroupMessageEvent):
#     bot, send_group_id = await assign_bot(bot=bot, event=event)
#     isUser, user_info, msg = check_user(event)
#     if not isUser:
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await last_work.finish()
#     user_id = user_info['user_id']
#     user_level = user_info['level']
#     user_rank = Items().convert_rank(user_level)[0]
#     is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
#     if (is_type and user_rank <= 11) or (
#             is_type and user_info['exp'] >= sql_message.get_level_power("金仙境圆满")) or (
#             is_type and int(user_info['exp']) >= int(
#         OtherSet().set_closing_type(user_level)) * XiuConfig().closing_exp_upper_limit
#     ):
#         user_cd_message = sql_message.get_user_cd(user_id)
#         work_time = datetime.strptime(
#             user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f"
#         )
#         exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
#         time2 = workhandle().do_work(
#             key=1, name=user_cd_message['scheduled_time'], level=user_level, exp=user_info['exp'],
#             user_id=user_info['user_id']
#         )
#         if exp_time < time2:
#             msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await last_work.finish()
#         else:
#             msg, give_stone, s_o_f, item_id, big_suc = workhandle().do_work(
#                 2,
#                 work_list=user_cd_message['scheduled_time'],
#                 level=user_level,
#                 exp=user_info['exp'],
#                 user_id=user_info['user_id']
#             )
#             item_flag = False
#             item_msg = None
#             item_info = None
#             if item_id != 0:
#                 item_flag = True
#                 item_info = items.get_data_by_item_id(item_id)
#                 item_msg = f"{item_info['level']}:{item_info['name']}"
#             if big_suc:  # 大成功
#                 sql_message.update_ls(user_id, give_stone * 2, 1)
#                 sql_message.do_work(user_id, 0)
#                 msg = f"悬赏令结算，{msg}获得报酬{give_stone * 2}枚灵石"
#                 if item_flag:
#                     sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
#                     msg += f"，额外获得奖励：{item_msg}!"
#                 else:
#                     msg += "!"
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                 await last_work.finish()
#
#             else:
#                 sql_message.update_ls(user_id, give_stone, 1)
#                 sql_message.do_work(user_id, 0)
#                 msg = f"悬赏令结算，{msg}获得报酬{give_stone}枚灵石"
#                 if s_o_f:  # 普通成功
#                     if item_flag:
#                         sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
#                         msg += f"，额外获得奖励：{item_msg}!"
#                     else:
#                         msg += "!"
#                     await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                     await last_work.finish()
#
#                 else:  # 失败
#                     msg += "!"
#                     await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                     await last_work.finish()
#     else:
#         msg = "不满足使用条件！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await last_work.finish()


# @do_work.handle(parameterless=[Cooldown(stamina_cost=1, at_sender=False)])
# async def do_work_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
#     bot, send_group_id = await assign_bot(bot=bot, event=event)
#     user_level = "轮回境初期"
#     isUser, user_info, msg = check_user(event)
#     if not isUser:
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#     user_level_sx = user_info['level']
#     user_id = user_info['user_id']
#     user_rank = Items().convert_rank(user_info['level'])[0]
#     sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
#     user_cd_message = sql_message.get_user_cd(user_id)
#
#     # not os.path.exists(PLAYERSDATA / str(user_id) / "workinfo.json") 需要改成判断用户任务表中是否有有任务数据 如果没有数据 则重置用户状态
#     if not os.path.exists(PLAYERSDATA / str(user_id) / "workinfo.json") and user_cd_message['type'] == 2:
#         sql_message.do_work(user_id, 0)
#         msg = "悬赏令已更新，已重置道友的状态！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#     mode = args[0]  # 刷新、终止、结算、接取
#     if user_rank <= Items().convert_rank('轮回境初期')[0] or user_info['exp'] >= sql_message.get_level_power(
#             user_level):
#         msg = "道友的境界已过创业的初期，悬赏令已经不能满足道友了！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#     user_level = user_info['level']
#     if int(user_info['exp']) >= int(OtherSet().set_closing_type(user_level)) * XiuConfig().closing_exp_upper_limit:
#         # 获取下个境界需要的修为 * 1.5为闭关上限
#         msg = "道友的修为已经到达上限，悬赏令已无法再获得经验！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#     if user_cd_message['type'] == 1:
#         msg = "已经在闭关中，请输入【出关】结束后才能获取悬赏令！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#     if user_cd_message['type'] == 3:
#         msg = "道友在秘境中，请等待结束后才能获取悬赏令！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#     if user_cd_message['type'] == 4:
#         now_time = datetime.now()
#         in_closing_time = datetime.strptime(
#             user_cd_message['create_time'], "%Y-%m-%d %H:%M:%S.%f"
#         )  # 预计修炼结束的时间
#         seconds_diff = (in_closing_time - now_time).total_seconds()
#         remaining_seconds = int(seconds_diff)
#         if remaining_seconds > 0:
#             msg = f"道友正在修炼中，还剩 {remaining_seconds} 秒结束修炼！"
#         else:
#             # 如果修炼已经结束，更新状态
#             sql_message.in_closing(user_id, 0)
#             msg = "修炼已结束，请重新刷新悬赏令！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#
#     if mode is None:  # 接取逻辑
#         if (user_cd_message['scheduled_time'] is None) or (user_cd_message['type'] == 0):
#             try:
#                 msg = work[user_id].msg
#             except KeyError:
#                 msg = "没有查到你的悬赏令信息呢，请刷新！"
#         elif user_cd_message['type'] == 2:
#             create_time = user_cd_message['create_time']
#             work_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S.%f")
#             exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
#             time2 = workhandle().do_work(key=1, name=user_cd_message['scheduled_time'], user_id=user_info['user_id'])
#             if exp_time < time2:
#                 msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
#             else:
#                 msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，已结束，请输入【悬赏令结算】结算任务信息！"
#         else:
#             msg = "状态未知错误！"
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#
#     if mode == "刷新":  # 刷新逻辑
#         stone_use = 0  # 悬赏令刷新提示是否扣灵石
#         if user_cd_message['type'] == 2:
#             create_time = user_cd_message['create_time']
#             work_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S.%f")
#             exp_time = (datetime.now() - work_time).seconds // 60
#             time2 = workhandle().do_work(key=1, name=user_cd_message['scheduled_time'], user_id=user_info['user_id'])
#             if exp_time < time2:
#                 msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
#             else:
#                 msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，已结束，请输入【悬赏令结算】结算任务信息！"
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await do_work.finish()
#         usernums = sql_message.get_work_num(user_id)
#
#         isUser, user_info, msg = check_user(event)
#         if not isUser:
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await do_work.finish()
#
#         freenum = count - usernums - 1
#         if freenum < 0:
#             freenum = 0
#             if int(user_info['stone']) < int(lscost / Items().convert_rank(user_level_sx)[0]):
#                 msg = f"道友的灵石不足以刷新，下次刷新消耗灵石：{int(lscost / Items().convert_rank(user_level_sx)[0])}枚"
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                 await do_work.finish()
#             else:
#                 sql_message.update_ls(user_id, int(lscost / Items().convert_rank(user_level_sx)[0]), 2)
#                 stone_use = 1
#
#         work_msg = workhandle().do_work(0, level=user_level, exp=user_info['exp'], user_id=user_id)
#         n = 1
#         work_list = []
#         work_msg_f = f"☆------道友的个人悬赏令------☆\n"
#         for i in work_msg:
#             work_list.append([i[0], i[3]])
#             work_msg_f += f"{n}、{get_work_msg(i)}"
#             n += 1
#         work_msg_f += f"(悬赏令每日免费刷新次数：{count}，超过{count}次后，下次刷新消耗灵石{int(lscost / Items().convert_rank(user_level_sx)[0])},今日可免费刷新次数：{freenum}次)"
#         if int(stone_use) == 1:
#             work_msg_f += f"\n道友消耗灵石{int(lscost / Items().convert_rank(user_level_sx)[0])}枚，成功刷新悬赏令"
#         work[user_id] = do_is_work(user_id)
#         work[user_id].msg = work_msg_f
#         work[user_id].world = work_list
#         sql_message.update_work_num(user_id, usernums + 1)
#         msg = work[user_id].msg
#         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await do_work.finish()
#
#     elif mode == "终止":
#         is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
#         if is_type:
#             stone = 4000000
#             sql_message.update_ls(user_id, stone, 2)
#             sql_message.do_work(user_id, 0)
#             msg = f"道友不讲诚信，被打了一顿灵石减少{stone},悬赏令已终止！"
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await do_work.finish()
#         else:
#             msg = "没有查到你的悬赏令信息呢，请刷新！"
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await do_work.finish()
#
#     elif mode == "结算":
#         is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
#         if is_type:
#             user_cd_message = sql_message.get_user_cd(user_id)
#             create_time = user_cd_message['create_time']
#             work_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S.%f")
#             exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
#             time2 = workhandle().do_work(
#                 key=1, name=user_cd_message['scheduled_time'], level=user_level, exp=user_info['exp'],
#                 user_id=user_info['user_id']
#             )
#             if exp_time < time2:
#                 msg = f"进行中的悬赏令【{user_cd_message['scheduled_time']}】，预计{time2 - exp_time}分钟后可结束"
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                 await do_work.finish()
#             else:
#                 msg, give_exp, s_o_f, item_id, big_suc = workhandle().do_work(2,
#                                                                                                   work_list=user_cd_message[
#                                                                                                       'scheduled_time'],
#                                                                                                   level=user_level,
#                                                                                                   exp=user_info['exp'],
#                                                                                                   user_id=user_info['user_id'])
#                 item_flag = False
#                 item_info = None
#                 item_msg = None
#                 if item_id != 0:
#                     item_flag = True
#                     item_info = items.get_data_by_item_id(item_id)
#                     item_msg = f"{item_info['level']}:{item_info['name']}"
#                 if big_suc:  # 大成功
#                     sql_message.update_exp(user_id, give_exp * 2)
#                     sql_message.do_work(user_id, 0)
#                     msg = f"悬赏令结算，{msg}增加修为{give_exp * 2}"
#                     if item_flag:
#                         sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
#                         msg += f"，额外获得奖励：{item_msg}!"
#                     else:
#                         msg += "!"
#
#                     await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                     await do_work.finish()
#
#                 else:
#                     sql_message.update_exp(user_id, give_exp)
#                     sql_message.do_work(user_id, 0)
#                     msg = f"悬赏令结算，{msg}增加修为{give_exp}"
#                     if s_o_f:  # 普通成功
#                         if item_flag:
#                             sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
#                             msg += f"，额外获得奖励：{item_msg}!"
#                         else:
#                             msg += "!"
#                         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                         await do_work.finish()
#
#                     else:  # 失败
#                         msg += "!"
#                         await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                         await do_work.finish()
#         else:
#             msg = "没有查到你的悬赏令信息呢，请刷新！"
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await do_work.finish()
#
#     elif mode == "接取":
#         num = args[1]
#         is_type, msg = check_user_type(user_id, 0)  # 需要无状态的用户
#         if is_type:  # 接取逻辑
#             if num is None or str(num) not in ['1', '2', '3']:
#                 msg = '请输入正确的任务序号'
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                 await do_work.finish()
#             work_num = 1
#             try:
#                 if work[user_id]:
#                     work_num = int(num)  # 任务序号
#                 try:
#                     get_work = work[user_id].world[work_num - 1]
#                     sql_message.do_work(user_id, 2, get_work[0])
#                     del work[user_id]
#                     msg = f"接取任务【{get_work[0]}】成功"
#                     await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                     await do_work.finish()
#
#                 except IndexError:
#                     msg = "没有这样的任务"
#                     await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                     await do_work.finish()
#
#             except KeyError:
#                 msg = "没有查到你的悬赏令信息呢，请刷新！"
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#                 await do_work.finish()
#         else:
#             msg = "没有查到你的悬赏令信息呢，请刷新！"
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await do_work.finish()
#

# def get_work_msg(work_):
#     msg = f"{work_[0]},完成机率{work_[1]},基础报酬{work_[2]}修为,预计需{work_[3]}分钟{work_[4]}\n"
#     return msg
