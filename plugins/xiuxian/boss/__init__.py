import random
import json
from decimal import Decimal

import psycopg2
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GROUP
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime

try:
    import ujson as json
except ImportError:
    import json
import re
from pathlib import Path
import random
import os
from nonebot.rule import Rule
from nonebot import get_bots, get_bot, on_command, require
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    GROUP_ADMIN,
    GROUP_OWNER,
    ActionFailed,
    MessageSegment
)
from ..xiuxian_utils.lay_out import assign_bot, put_bot, layout_bot_dict, Cooldown
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, OtherSet, UserBuffDate,
    XIUXIAN_IMPART_BUFF, leave_harm_time, sql_message
)
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.item_database_handler import Items
from ..xiuxian_utils.player_fight import Boss_fight

items = Items()
from ..xiuxian_utils.utils import (
    number_to, check_user,
    CommandObjectID,
    send_msg_handler
)
from .. import DRIVER

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
    -- 创建xiuxian_boss_info表，存储BOSS的信息
    CREATE TABLE IF NOT EXISTS xiuxian_boss_info (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        name VARCHAR(255) NOT NULL, -- BOSS的名字
        jj VARCHAR(255) NOT NULL, -- BOSS的境界
        hp BIGINT NOT NULL, -- 当前HP
        max_hp BIGINT NOT NULL, -- 最大HP
        mp BIGINT NOT NULL, -- 真元
        attack BIGINT NOT NULL, -- 攻击力
        stone BIGINT NOT NULL, -- 奖励灵石
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认为当前时间
    );

    -- 创建xiuxian_boss_config表，存储BOSS相关的配置信息
    CREATE TABLE IF NOT EXISTS xiuxian_boss_config (
        key VARCHAR(255) PRIMARY KEY, -- 配置项的键，唯一标识
        value TEXT NOT NULL -- 配置项的值
    );

    -- 创建xiuxian_world_store表，存储世界商店的商品信息
    CREATE TABLE IF NOT EXISTS xiuxian_world_store (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        item_id INT NOT NULL, -- 商品ID
        cost INT NOT NULL, -- 商品价格(世界积分)
        description TEXT NOT NULL -- 商品描述
    );

    -- 创建xiuxian_boss_fights表，存储用户对BOSS的战斗记录
    CREATE TABLE IF NOT EXISTS xiuxian_boss_fights (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        user_id BIGINT NOT NULL, -- 用户ID
        boss_id INT NOT NULL, -- BOSS ID，外键引用xiuxian_boss_info表的id字段
        damage BIGINT NOT NULL, -- 对BOSS造成的伤害
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间，默认为当前时间
        FOREIGN KEY (boss_id) REFERENCES xiuxian_boss_info(id) -- 外键约束，确保boss_id在xiuxian_boss_info表中存在
    );

    -- 创建xiuxian_boss_damage_leaderboard表，存储用户对BOSS的总伤害排行榜
    CREATE TABLE IF NOT EXISTS xiuxian_boss_damage_leaderboard (
        id SERIAL PRIMARY KEY, -- 主键，自动递增
        user_id BIGINT NOT NULL, -- 用户ID
        boss_id INT NOT NULL, -- BOSS ID，外键引用xiuxian_boss_info表的id字段
        total_damage BIGINT NOT NULL, -- 对BOSS造成的总伤害
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间，默认为当前时间
        FOREIGN KEY (boss_id) REFERENCES xiuxian_boss_info(id) -- 外键约束，确保boss_id在xiuxian_boss_info表中存在
    );
    -- 创建xiuxian_user_world_integral表，存储用户的world积分
    CREATE TABLE IF NOT EXISTS xiuxian_user_world_integral (
        user_id BIGINT PRIMARY KEY, -- 用户ID，主键
        boss_integral BIGINT NOT NULL DEFAULT 0 -- 用户的世界积分
    );
    """

    cursor.execute(create_tables_sql)
    conn.commit()
    cursor.close()
    conn.close()


def get_boss_config():
    """从数据库获取 Boss 配置"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM xiuxian_boss_config")
    config = {row['key']: json.loads(row['value']) for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return config


def create_boss(boss_info):
    """创建 Boss 并保存到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO xiuxian_boss_info (name, jj, hp, max_hp, mp, attack, stone) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (boss_info['name'], boss_info['jj'], boss_info['hp'], boss_info['max_hp'], boss_info['mp'], boss_info['attack'],
         boss_info['stone']))
    boss_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return boss_id

def update_boss_hp(boss_id, new_hp):
    """
    更新 Boss 血量

    :param boss_id: 要更新血量的 Boss 的ID
    :param new_hp: 新的血量值
    :return: 如果更新成功返回 True，否则返回 False
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 执行更新操作
        cursor.execute(
            "UPDATE xiuxian_boss_info SET hp = %s WHERE id = %s",
            (new_hp, boss_id)
        )
        # 提交更改
        conn.commit()
        # 检查是否有行受到影响，确保更新成功
        if cursor.rowcount > 0:
            return True
        else:
            return False
    except Exception as e:
        # 发生错误时回滚
        conn.rollback()
        print(f"发生错误：{e}")
        return False
    finally:
        # 关闭游标和连接
        cursor.close()
        conn.close()

def get_all_bosses():
    """获取所有 Boss 信息"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM xiuxian_boss_info ORDER BY hp DESC")
    bosses = cursor.fetchall()
    cursor.close()
    conn.close()
    return bosses


def delete_boss(boss_id):
    """删除 Boss"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM xiuxian_boss_info WHERE id = %s", (boss_id,))
    conn.commit()
    cursor.close()
    conn.close()


def record_boss_damage(user_id, boss_id, damage):
    """记录用户对 Boss 的伤害"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO xiuxian_boss_fights (user_id, boss_id, damage) VALUES (%s, %s, %s)",
                   (user_id, boss_id, damage))
    conn.commit()
    cursor.close()
    conn.close()


def update_boss_damage_leaderboard(user_id, boss_id, damage):
    """更新 Boss 损害排行榜"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_damage FROM xiuxian_boss_damage_leaderboard WHERE user_id = %s AND boss_id = %s",
                   (user_id, boss_id))
    result = cursor.fetchone()
    if result:
        total_damage = result[0] + damage
        cursor.execute(
            "UPDATE xiuxian_boss_damage_leaderboard SET total_damage = %s WHERE user_id = %s AND boss_id = %s",
            (total_damage, user_id, boss_id))
    else:
        cursor.execute(
            "INSERT INTO xiuxian_boss_damage_leaderboard (user_id, boss_id, total_damage) VALUES (%s, %s, %s)",
            (user_id, boss_id, damage))
    conn.commit()
    cursor.close()
    conn.close()


def get_boss_damage_leaderboard(boss_id):
    """获取 Boss 损害排行榜"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT user_id, total_damage FROM xiuxian_boss_damage_leaderboard WHERE boss_id = %s ORDER BY total_damage DESC LIMIT 10",
        (boss_id,))
    leaderboard = cursor.fetchall()
    cursor.close()
    conn.close()
    return leaderboard


def get_user_world_integral(user_id):
    """从数据库获取用户的world积分"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT boss_integral FROM xiuxian_user_world_integral WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['boss_integral'] if result else 0


def update_user_world_integral(user_id, integral_delta):
    """
    更新用户的world积分。如果用户不存在，则插入新记录。
    积分会根据传入的增量值进行更新（增加或减少）。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # 尝试更新用户的积分（如果用户存在）
    try:
        cursor.execute(
            "UPDATE xiuxian_user_world_integral SET boss_integral = boss_integral + %s WHERE user_id = %s",
            (integral_delta, user_id)
        )
        # 如果更新影响的行数为0，说明用户不存在
        if cursor.rowcount == 0:
            # 用户不存在，插入新记录
            cursor.execute(
                "INSERT INTO xiuxian_user_world_integral (user_id, boss_integral) VALUES (%s, %s)",
                (user_id, integral_delta)  # 这里假设如果用户不存在，则初始积分为增量值
                # 如果你想在用户不存在时设置初始积分为0，并加上增量值，可以改为：
                # (user_id, COALESCE(NULLIF((SELECT boss_integral FROM xiuxian_user_world_integral WHERE user_id = %s) IS NULL, 0), 0) + %s)
                # 但是由于用户不存在，这个子查询会失败或返回NULL，所以直接设置为增量值更简单
            )
    except Exception as e:
        # 这里可以添加错误处理逻辑，比如回滚事务、记录日志等
        conn.rollback()
        raise e  # 重新抛出异常以便上层调用者处理
    else:
        # 如果没有异常发生，提交事务
        conn.commit()
    finally:
        # 关闭游标和连接
        cursor.close()
        conn.close()


def get_world_store_items():
    """从数据库获取世界积分商店的商品信息"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM xiuxian_world_store")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items


def save_world_store_items(items):
    """保存世界积分商店的商品信息到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in items:
        cursor.execute(
            "INSERT INTO xiuxian_world_store (item_id, cost, description) VALUES (%s, %s, %s) ON CONFLICT (item_id) DO UPDATE SET cost = EXCLUDED.cost, description = EXCLUDED.description",
            (item['item_id'], item['cost'], item['description']))
    conn.commit()
    cursor.close()
    conn.close()


def get_jingjie_from_db():
    """从数据库获取境界列表和经验值"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM xiuxian_jingjie")
    jingjie_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jingjie_data

def get_user_dao_name(user_id):
    """通过用户ID获取用户道号"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT user_name FROM user_xiuxian WHERE user_id = %s",
        (user_id,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result['user_name']
    else:
        return "未知用户"

require('nonebot_plugin_apscheduler')
del_boss_id = XiuConfig().del_boss_id
gen_boss_id = XiuConfig().gen_boss_id
config = get_boss_config()# 获取 Boss 配置
xiuxian_impart = XIUXIAN_IMPART_BUFF()

def check_rule_bot_boss() -> Rule:  # 消息检测，是超管，群主或者指定的qq号传入的消息就响应，其他的不响应
    async def _check_bot_(bot: Bot, event: GroupMessageEvent) -> bool:
        if (event.sender.role == "admin" or
                event.sender.role == "owner" or
                event.get_user_id() in bot.config.superusers or
                event.get_user_id() in del_boss_id):
            return True
        else:
            return False

    return Rule(_check_bot_)


def check_rule_bot_boss_s() -> Rule:  # 消息检测，是超管或者指定的qq号传入的消息就响应，其他的不响应
    async def _check_bot_(bot: Bot, event: GroupMessageEvent) -> bool:
        if (event.get_user_id() in bot.config.superusers or
                event.get_user_id() in gen_boss_id):
            return True
        else:
            return False

    return Rule(_check_bot_)


boss_time = config["Boss生成时间参数"]


@DRIVER.on_startup
async def read_boss_():
    global group_boss
    group_boss.update(old_boss_info.read_boss_info())
    logger.opt(colors=True).info(f"<green>历史boss数据读取成功</green>")


@DRIVER.on_startup
async def set_boss_():
    groups_list = list(groups.keys())
    try:
        for group_id in groups_list:
            scheduler.add_job(
                func=send_bot,
                trigger='interval',
                hours=groups[str(group_id)]["hours"],
                minutes=groups[str(group_id)]['minutes'],
                id=f"set_boss_{group_id}",
                args=[group_id],
                misfire_grace_time=10
            )
            logger.opt(colors=True).success(
                f"<green>开启群{group_id}boss,每{groups[str(group_id)]['hours']}小时{groups[str(group_id)]['minutes']}分钟刷新！</green>")
    except Exception as e:
        logger.opt(colors=True).warning(f"<red>警告,定时群boss加载失败!,{e}!</red>")


async def send_bot(group_id: str):
    # 初始化
    if not group_id in group_boss:
        group_boss[group_id] = []

    if group_id not in groups:
        return

    if not sql_message.is_xiuxian_enabled(group_id):
        return

    if len(group_boss[group_id]) >= config['Boss个数上限']:
        logger.opt(colors=True).info(f"<green>群{group_id}Boss个数已到达个数上限</green>")
        return

    api = 'send_group_msg'  # 要调用的函数
    data = {'group_id': int(group_id)}  # 要发送的群

    bossinfo = createboss()
    group_boss[group_id].append(bossinfo)
    msg = f"野生的{bossinfo['jj']}Boss:{bossinfo['name']}出现了,诸位道友请击Boss得奖励吧!"
    data['message'] = MessageSegment.text(msg)

    try:
        bot_id = layout_bot_dict[group_id] if group_id in layout_bot_dict else put_bot[0]
    except:
        bot = get_bot()
        bot_id = bot.self_id

    try:
        if type(bot_id) is str:
            await get_bots()[bot_id].call_api(api, **data)
        elif type(bot_id) is list:
            await get_bots()[random.choice(bot_id)].call_api(api, **data)
        else:
            await get_bots()[put_bot[0]].call_api(api, **data)

    except:
        if group_id not in bot.get_group_list():
            logger.opt(colors=True).warning(f"<red>群{group_id}不存在,请检查配置文件!</red>")
            return
        else:
            await get_bot().call_api(api, **data)

    logger.opt(colors=True).info(f"<green>群{group_id}已生成世界boss</green>")



boss_delete = on_command("天罚boss", aliases={"天罚世界boss", "天罚Boss", "天罚BOSS", "天罚世界Boss", "天罚世界BOSS"},
                         priority=7,
                         rule=check_rule_bot_boss(), block=True)
boss_delete_all = on_command("天罚所有boss",
                             aliases={"天罚所有世界boss", "天罚所有Boss", "天罚所有BOSS", "天罚所有世界Boss",
                                      "天罚所有世界BOSS",
                                      "天罚全部boss", "天罚全部世界boss"}, priority=5,
                             rule=check_rule_bot_boss(), block=True)
boss_info = on_command("查询世界boss",
                       aliases={"查询世界Boss", "查询世界BOSS", "查询boss", "世界Boss查询", "世界BOSS查询", "boss查询"},
                       priority=6, permission=GROUP, block=True)
boss_integral_info = on_command("世界积分查看", aliases={"查看世界积分", "查询世界积分", "世界积分查询"}, priority=10,
                                permission=GROUP, block=True)
boss_integral_use = on_command("世界积分兑换", priority=6, permission=GROUP, block=True)
create = on_command("生成世界boss", aliases={"生成世界Boss", "生成世界BOSS"}, priority=5,
                    rule=check_rule_bot_boss_s(), block=True)
batch_create = on_command("生成boss", priority=5, rule=check_rule_bot_boss_s(), block=True)
create_appoint = on_command("生成指定世界boss",
                            aliases={"生成指定世界boss", "生成指定世界BOSS", "生成指定BOSS", "生成指定boss"},
                            priority=5,
                            rule=check_rule_bot_boss_s())
battle = on_command("讨伐boss", aliases={"讨伐世界boss", "讨伐Boss", "讨伐BOSS", "讨伐世界Boss", "讨伐世界BOSS"},
                    priority=6,
                    permission=GROUP, block=True)


@battle.handle(parameterless=[Cooldown(stamina_cost=20, at_sender=False)])
async def battle_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """讨伐世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()

    user_id = user_info['user_id']
    sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    msg = args.extract_plain_text().strip()
    group_id = str(event.group_id)
    boss_num = re.findall(r'\d+', msg)  # boss编号

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        sql_message.update_user_stamina(user_id, 20, 1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()

    all_bosses = get_all_bosses()
    if not all_bosses:
        msg = f"当前没有生成的世界Boss,请等待世界boss刷新!"
        sql_message.update_user_stamina(user_id, 20, 1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()
    if boss_num:
        boss_num = int(boss_num[0])
        if not (0 < boss_num <= len(all_bosses)):
            msg = f"请输入正确的世界Boss编号!"
            sql_message.update_user_stamina(user_id, 20, 1)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await battle.finish()

    if user_info['hp'] is None or user_info['hp'] == 0:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)

    if user_info['hp'] <= user_info['exp'] / 10:
        time = leave_harm_time(user_id)
        msg = f"重伤未愈，动弹不得！距离脱离危险还需要{time}分钟！\n"
        msg += f"请道友进行闭关，或者使用药品恢复气血，不要干等，没有自动回血！！！"
        sql_message.update_user_stamina(user_id, 20, 1)
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()

    player = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None,
              '防御': Decimal('0')}
    userinfo = sql_message.get_user_real_info(user_id)
    user_weapon_data = UserBuffDate(userinfo['user_id']).get_user_weapon_data()
    user_poxian = userinfo['poxian_num']  # 新增破限次数

    # 获取轮回点数
    user_cultEff = Decimal(user_info['cultEff']) / Decimal('100')
    user_seclEff = Decimal(user_info['seclEff']) / Decimal('100')
    user_maxR = Decimal(user_info['maxR']) / Decimal('100')
    user_maxH = Decimal(user_info['maxH']) * Decimal('100000')
    user_maxM = Decimal(user_info['maxM']) * Decimal('100000')
    user_maxA = Decimal(user_info['maxA']) * Decimal('100000')

    # 计算破限带来的总增幅百分比
    total_poxian_percent = Decimal('0')
    if user_poxian <= 10:
        total_poxian_percent += user_poxian * Decimal('10')
    else:
        total_poxian_percent += 10 * Decimal('10')  # 前10次破限的总增幅
        total_poxian_percent += (user_poxian - 10) * Decimal('20')  # 超过10次之后的增幅

    impart_data = xiuxian_impart.get_user_info_with_id(user_id)
    boss_atk = Decimal(impart_data['boss_atk']) if impart_data['boss_atk'] is not None else Decimal('0')
    user_armor_data = UserBuffDate(userinfo['user_id']).get_user_armor_buff_data()  # boss战防具会心
    user_main_data = UserBuffDate(userinfo['user_id']).get_user_main_buff_data()  # boss战功法会心
    user1_sub_buff_data = UserBuffDate(userinfo['user_id']).get_user_sub_buff_data()  # boss战辅修功法信息
    integral_buff = Decimal(user1_sub_buff_data['integral']) if user1_sub_buff_data is not None else Decimal('0')
    exp_buff = Decimal(user1_sub_buff_data['exp']) if user1_sub_buff_data is not None else Decimal('0')

    if user_main_data is not None:  # boss战功法会心
        main_crit_buff = Decimal(user_main_data['crit_buff'])
    else:
        main_crit_buff = Decimal('0')

    if user_armor_data is not None:  # boss战防具会心
        armor_crit_buff = Decimal(user_armor_data['crit_buff'])
    else:
        armor_crit_buff = Decimal('0')

    if user_weapon_data is not None:
        player['会心'] = int(
            ((Decimal(user_weapon_data['crit_buff']) + armor_crit_buff + main_crit_buff) * Decimal('100') * (
                    Decimal('1') + total_poxian_percent / Decimal('100'))).quantize(Decimal('1')))
    else:
        player['会心'] = int(((armor_crit_buff + main_crit_buff) * Decimal('100') * (
                    Decimal('1') + total_poxian_percent / Decimal('100'))).quantize(Decimal('1')))
    player['user_id'] = userinfo['user_id']
    player['道号'] = userinfo['user_name']
    player['气血'] = (Decimal(userinfo['hp']) + user_maxH) * (Decimal('1') + total_poxian_percent / Decimal('100'))
    player['攻击'] = int(((Decimal(userinfo['atk']) + user_maxA) * (Decimal('1') + boss_atk) * (
                Decimal('1') + total_poxian_percent / Decimal('100'))).quantize(Decimal('1')))
    player['真元'] = (Decimal(userinfo['mp']) + user_maxM) * (Decimal('1') + total_poxian_percent / Decimal('100'))
    player['exp'] = Decimal(userinfo['exp']) * (Decimal('1') + total_poxian_percent / Decimal('100'))

    bossinfo = all_bosses[boss_num - 1]
    if bossinfo['hp'] == 0:
        msg = f"来晚一步, BOSS已被击杀，魂飞魄散！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()

    if bossinfo['jj'] == '零':
        boss_rank = Items().convert_rank(bossinfo['jj'])[0]
    else:
        boss_rank = Items().convert_rank(bossinfo['jj'] + '中期')[0]
    user_rank = Items().convert_rank(userinfo['level'])[0]
    if boss_rank - user_rank >= 12:
        msg = f"道友已是{userinfo['level']}之人，妄图抢小辈的Boss，可耻！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()

    boss_old_hp = bossinfo['hp']  # 打之前的血量
    more_msg = ''
    # battle_flag[group_id] = True
    result, victor, bossinfo_new, get_stone = await Boss_fight(player, bossinfo, bot_id=bot.self_id)
    # 将 result 转换为字符串
    if isinstance(result, list):
        result_str = "『战斗详情』\n"
        result_str += '\n'.join(node['data']['content'] for node in result if node['data']['content'])
    else:
        result_str = result
    if victor == "Boss赢了":
        all_bosses[boss_num - 1] = bossinfo_new
        sql_message.update_ls(user_id, get_stone, 1)
        # 新增boss战斗积分点数
        boss_now_hp = bossinfo_new['hp']  # 打之后的血量
        boss_all_hp = bossinfo['max_hp']  # 总血量
        boss_world_integral = int(
            ((Decimal(boss_old_hp) - Decimal(boss_now_hp)) / Decimal(boss_all_hp) * Decimal('240')).quantize(
                Decimal('1')))
        if boss_world_integral < 5:  # 摸一下不给
            boss_world_integral = 0
        if user_info['root'] == "器师":
            boss_world_integral = int(
                (Decimal(boss_world_integral) * (Decimal('1') + (user_rank - boss_rank))).quantize(Decimal('1')))
            points_bonus = int((Decimal('80') * (user_rank - boss_rank)).quantize(Decimal('1')))
            more_msg = f"道友低boss境界{user_rank - boss_rank}层，获得{points_bonus}%积分加成！"

        damage_dealt = boss_old_hp - boss_now_hp
        update_boss_hp(bossinfo['id'], boss_now_hp) # 更新boss血量
        update_user_world_integral(user_id, boss_world_integral)  # 更新世界积分
        record_boss_damage(user_id, bossinfo['id'], damage_dealt)  # 记录本次战斗伤害量
        update_boss_damage_leaderboard(user_id, bossinfo['id'], damage_dealt)  # 将本次战斗伤害量加入到伤害排行榜
        top_user_info = sql_message.get_top1_user()
        top_user_exp = Decimal(top_user_info['exp'])

        if exp_buff > 0 and user_info['root'] != "器师":
            now_exp = int((((Decimal(top_user_exp) * Decimal('0.1')) / Decimal(user_info['exp'])) / (
                    exp_buff * (Decimal('1') / (Items().convert_rank(user_info['level'])[0] + 1)))).quantize(
                Decimal('1')))
            if now_exp > 1000000:
                now_exp = int((Decimal('1000000') / Decimal(random.randint(5, 10))).quantize(Decimal('1')))
            sql_message.update_exp(user_id, now_exp)
            exp_msg = f"，获得修为{int(now_exp)}点！"
        else:
            exp_msg = f" "

        msg = f"道友不敌{bossinfo['name']}，重伤逃遁，临逃前收获灵石{get_stone}枚，{more_msg}获得世界积分：{boss_world_integral}点{exp_msg} "
        if user_info['root'] == "器师" and boss_world_integral < 0:
            msg += f"\n如果出现负积分，说明你境界太高了，玩器师就不要那么高境界了！！！"
        # battle_flag[group_id] = False
        try:
            await bot.send_group_msg(group_id=int(send_group_id), message=result_str)
        except ActionFailed:
            msg += f"Boss战消息发送错误,可能被风控!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()

    elif victor == "群友赢了":
        # 新增boss战斗积分点数
        boss_all_hp = bossinfo['max_hp']  # 总血量
        boss_world_integral = int((Decimal(boss_old_hp) / Decimal(boss_all_hp) * Decimal('240')).quantize(Decimal('1')))
        if user_info['root'] == "器师":
            boss_world_integral = int(
                (Decimal(boss_world_integral) * (Decimal('1') + (user_rank - boss_rank))).quantize(Decimal('1')))
            points_bonus = int((Decimal('80') * (user_rank - boss_rank)).quantize(Decimal('1')))
            more_msg = f"道友低boss境界{user_rank - boss_rank}层，获得{points_bonus}%积分加成！"
        else:
            if boss_rank - user_rank >= 9:  # 超过太多不给
                boss_world_integral = 0
                more_msg = f"道友的境界超过boss太多了,不齿！"

        top_user_info = sql_message.get_top1_user()
        top_user_exp = Decimal(top_user_info['exp'])

        if exp_buff > 0 and user_info['root'] != "器师":
            now_exp = int((((Decimal(top_user_exp) * Decimal('0.1')) / Decimal(user_info['exp'])) / (
                    exp_buff * (Decimal('1') / (Items().convert_rank(user_info['level'])[0] + 1)))).quantize(
                Decimal('1')))
            if now_exp > 1000000:
                now_exp = int((Decimal('1000000') / Decimal(random.randint(5, 10))).quantize(Decimal('1')))
            sql_message.update_exp(user_id, now_exp)
            exp_msg = f"，获得修为{int(now_exp)}点！"
        else:
            exp_msg = f" "

        drops_id, drops_info = boss_drops(user_rank, boss_rank, bossinfo, userinfo)
        if drops_id is None:
            drops_msg = " "
        elif boss_rank < Items().convert_rank('混沌境中期')[0]:
            drops_msg = f"boss的尸体上好像有什么东西，凑近一看居然是{drops_info['name']}！ "
            sql_message.send_back(user_info['user_id'], drops_info['id'], drops_info['name'], drops_info['type'], 1)
        else:
            drops_msg = " "


        update_boss_hp(bossinfo['id'], 0) # 更新boss血量
        sql_message.update_ls(user_id, get_stone, 1)  # 更新灵石
        update_user_world_integral(user_id, boss_world_integral)  # 更新世界积分
        record_boss_damage(user_id, bossinfo['id'], boss_old_hp)# 记录本次战斗伤害量
        update_boss_damage_leaderboard(user_id, bossinfo['id'], boss_old_hp)# 将本次战斗伤害量加入到伤害排行榜

        msg = f"恭喜道友击败{bossinfo['name']}，收获灵石{get_stone}枚，{more_msg}获得世界积分：{boss_world_integral}点!{exp_msg} {drops_msg}"
        if user_info['root'] == "器师" and boss_world_integral < 0:
            msg += f"\n如果出现负积分，说明你这器师境界太高了(如果总世界积分为负数，会帮你重置成0)，玩器师就不要那么高境界了！！！"
        try:
            await bot.send_group_msg(group_id=int(send_group_id), message=result_str)
        except ActionFailed:
            msg += f"Boss战消息发送错误,可能被风控!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await battle.finish()


def boss_drops(user_rank, boss_rank, boss, user_info):
    boss_dice = random.randint(0, 100)
    drops_id = None
    drops_info = None
    if boss_rank - user_rank >= 6:
        drops_id = None
        drops_info = None

    elif boss_dice >= 90:
        drops_id, drops_info = get_drops(user_info)

    return drops_id, drops_info


def get_drops(user_info):
    """
    随机获取一个boss掉落物
    :param user_info:用户信息类
    :param rift_rank:秘境等级
    :return 法器ID, 法器信息json
    """
    drops_data = items.get_data_by_item_type(['掉落物'])
    drops_id = get_id(drops_data, user_info['level'])
    drops_info = items.get_data_by_item_id(drops_id)
    return drops_id, drops_info


def get_id(dict_data, user_level):
    """根据字典的rank、用户等级、秘境等级随机获取key"""
    l_temp = []
    final_rank = Items().convert_rank(user_level)[0]  # 秘境等级，会提高用户的等级
    pass_rank = Items().convert_rank('搬血境初期')[0]  # 最终等级超过此等级会抛弃
    for k, v in dict_data.items():
        if v["rank"] >= final_rank and (v["rank"] - final_rank) <= pass_rank:
            l_temp.append(k)

    if len(l_temp) == 0:
        return None
    else:
        return random.choice(l_temp)


def get_boss_exp(boss_jj, config, jingjie_data):
    """根据境界名称获取 Boss 的经验值和其他属性"""
    for jingjie in jingjie_data:
        if jingjie['jingjie_name'].startswith(boss_jj.split(' ')[0]):
            bossexp = jingjie['exp']  # 获取该境界的经验值
            break
    else:
        return None  # 如果没有找到匹配的境界，返回 None

    # 根据配置计算 Boss 的属性
    bossinfo = {
        'hp': bossexp * config["Boss倍率"]["气血"],
        'max_hp': bossexp * config["Boss倍率"]["气血"],
        'mp': bossexp * config["Boss倍率"]["真元"],
        'attack': int(bossexp * config["Boss倍率"]["攻击"])
    }
    return bossinfo


def createboss():
    """生成随机 Boss"""
    # top_user_info = sql_message.get_top1_user()  # 获取顶级用户信息
    # top_user_level = top_user_info['level']  # 获取顶级用户的境界
    jingjie_data = get_jingjie_from_db()  # 从数据库获取所有境界信息
    jinjie_list = [item['jingjie_name'] for item in jingjie_data]  # 提取所有境界名称
    # 随机选择一个境界
    boss_jj_siji = random.choice(jinjie_list)

    if len(boss_jj_siji) == 5:
        level = boss_jj_siji[:3]  # 如果境界长度为5，取前3个字符作为主要境界
    elif len(boss_jj_siji) == 4:  # 对江湖好手判断
        level = "搬血境"

    # 随机选择一个符合顶级用户境界或搬血境的 Boss 境界
    # boss_jj = random.choice([jj for jj in jinjie_list if jj.startswith(level) or jj.startswith("搬血境")])
    bossinfo = get_boss_exp(level, config, jingjie_data)  # 获取 Boss 属性
    if bossinfo:
        bossinfo['name'] = random.choice(config["Boss名字"])  # 随机选择 Boss 名称
        bossinfo['jj'] = level  # 设置 Boss 境界
        if len(level) == 5:
            level = level[:3]  # 如果境界长度为5，取前3个字符作为主要境界
        else:
            level = level  # 否则使用完整的境界名称
        bossinfo['jj'] = level
        bossinfo['stone'] = random.choice(config["Boss灵石"][level.split(' ')[0]])  # 随机选择 Boss 奖励灵石
        create_boss(bossinfo)  # 将 Boss 信息保存到数据库
        return bossinfo
    else:
        return None  # 如果没有找到匹配的境界，返回 None


def createboss_jj(boss_jj, boss_name=None):
    """生成指定境界的 Boss"""
    jingjie_data = get_jingjie_from_db()  # 从数据库获取所有境界信息
    bossinfo = get_boss_exp(boss_jj, config, jingjie_data)  # 获取 Boss 属性
    if bossinfo:
        bossinfo['name'] = boss_name if boss_name else random.choice(config["Boss名字"])  # 设置 Boss 名称
        bossinfo['jj'] = boss_jj  # 设置 Boss 境界
        if len(boss_jj) == 5:
            level = boss_jj[:3]  # 如果境界长度为5，取前3个字符作为主要境界
        else:
            level = boss_jj  # 否则使用完整的境界名称
        bossinfo['jj'] = level
        bossinfo['stone'] = random.choice(config["Boss灵石"][level.split(' ')[0]])  # 随机选择 Boss 奖励灵石
        create_boss(bossinfo)  # 将 Boss 信息保存到数据库
        return bossinfo
    else:
        return None  # 如果没有找到匹配的境界，返回 None


@create.handle(parameterless=[Cooldown(at_sender=False)])
async def create_(bot: Bot, event: GroupMessageEvent):
    """生成世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await create.finish()
    bossinfo = createboss()
    msg = f"已生成{bossinfo['jj']}Boss:{bossinfo['name']},诸位道友请击败Boss获得奖励吧!"
    await bot.send(event, msg)
    await create.finish()


@batch_create.handle(parameterless=[Cooldown(at_sender=False)])
async def batch_create_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """批量生成世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await batch_create.finish()

    arg_str = args.extract_plain_text().strip()
    try:
        num_bosses = int(arg_str)
    except ValueError:
        msg = "请输入正确的数量！例如：生成boss 100"
        await bot.send(event, msg)
        await batch_create.finish()

    messages = []
    for _ in range(num_bosses):
        bossinfo = createboss()
        create_boss(bossinfo)
        msg = f"已生成 {bossinfo['jj']} Boss: {bossinfo['name']} ,诸位道友请击败Boss获得奖励吧!\n"
        messages.append(msg)
    final_msg = "".join(messages)
    await bot.send(event, final_msg)
    await batch_create.finish()


@create_appoint.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """生成指定世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss，请联系管理员开启!"
        await create_appoint.finish(msg, at_sender=False)

    arg_list = args.extract_plain_text().split()
    if len(arg_list) < 1:
        msg = f"请输入正确的指令，例如：生成指定世界boss 祭道境 少姜"
        await create_appoint.finish(msg, at_sender=False)

    boss_jj = arg_list[0]  # 用户指定的境界
    boss_name = arg_list[1] if len(arg_list) > 1 else None  # 用户指定的Boss名称，如果有的话

    # 使用提供的境界和名称生成boss信息
    bossinfo = createboss_jj(boss_jj, boss_name)
    if bossinfo is None:
        msg = f"请输入正确的境界，例如：生成指定世界boss 祭道境"
        await create_appoint.finish(msg, at_sender=False)
    create_boss(bossinfo)
    msg = f"已生成{bossinfo['jj']}Boss:{bossinfo['name']}，诸位道友请击败Boss获得奖励吧！"
    await bot.send(event, msg)
    await create_appoint.finish()


@boss_integral_use.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_integral_use_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """世界积分兑换 世界积分商店兑换"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_use.finish()

    user_id = user_info['user_id']
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_use.finish()

    msg = args.extract_plain_text().strip()
    shop_info = re.findall(r"(\d+)\s*(\d*)", msg)

    if not shop_info:
        msg = f"请输入正确的商品编号！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_use.finish()

    shop_id = int(shop_info[0][0])
    quantity = int(shop_info[0][1]) if shop_info[0][1] else 1

    # 从数据库获取世界积分商店的商品信息
    world_store_items = get_world_store_items()
    item = next((item for item in world_store_items if item['item_id'] == shop_id), None)

    if not item:
        msg = f"该编号不在商品列表内哦，请检查后再兑换"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_use.finish()

    cost = item['cost']
    total_cost = cost * quantity

    # 获取用户的world积分
    user_boss_fight_info = get_user_world_integral(user_id)

    if user_boss_fight_info < total_cost:
        msg = f"道友的世界积分不满足兑换条件呢"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_use.finish()
    else:
        # 更新用户的world积分
        new_integral = user_boss_fight_info - total_cost
        update_user_world_integral(user_id, new_integral)

        # 兑换指定数量的商品
        item_info = {"name": item['description'], "type": "商品"}  # 这里假设 `Items().get_data_by_item_id` 返回类似的格式
        sql_message.send_back(user_id, shop_id, item_info['name'], item_info['type'], quantity)

        msg = f"道友成功兑换获得：{item_info['name']} {quantity}个"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_use.finish()


@boss_integral_info.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_integral_info_(bot: Bot, event: GroupMessageEvent):
    """世界积分查看 世界积分商店"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_info.finish()

    user_id = user_info['user_id']
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_integral_info.finish()

    user_boss_fight_info = get_user_world_integral(user_id)
    world_store_items = get_world_store_items()
    l_msg = [f"道友目前拥有的世界积分：{user_boss_fight_info}点"]

    if world_store_items:
        for item in world_store_items:
            msg = f"编号:{item['item_id']}\n"
            msg += f"描述：{item['description']}\n"
            msg += f"所需世界积分：{item['cost']}点\n"
            l_msg.append(msg)
    else:
        l_msg.append(f"世界积分商店内空空如也！")

    message = Message('\n'.join(l_msg))

    await bot.send_group_msg(group_id=int(send_group_id), message=message)
    await boss_integral_info.finish()


@boss_info.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_info_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查询世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_info.finish()

    msg = args.extract_plain_text().strip()
    boss_num = re.findall(r"\d+", msg)  # boss编号

    # 获取所有Boss信息
    all_bosses = get_all_bosses()

    if not all_bosses:
        msg = f"当前没有生成的世界Boss,请等待世界boss刷新!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_info.finish()

    Flag = False  # True查对应Boss
    if boss_num:
        boss_num = int(boss_num[0])
        if not (0 < boss_num <= len(all_bosses)):
            msg = f"请输入正确的世界Boss编号!"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await boss_info.finish()

        Flag = True

    if Flag:  # 查单个Boss信息
        boss = all_bosses[boss_num - 1]
        if boss['hp'] == 0:
            remaining_hp = "BOSS已被击杀"
        else:
            remaining_hp = number_to(boss['hp'])
        bossmsgs = f'''
世界Boss:{boss['name']}
境界：{boss['jj']}
总血量：{number_to(boss['max_hp'])}
剩余血量：{remaining_hp}
攻击：{number_to(boss['attack'])}
携带灵石：{number_to(boss['stone'])}
        '''
        msg = bossmsgs
        if int(boss["hp"] / boss["max_hp"]) < 0.5:
            boss_name = boss["name"] + "_c"
        else:
            boss_name = boss["name"]

        # 获取击杀者信息
        if boss['hp'] == 0:
            leaderboard = get_boss_damage_leaderboard(boss['id'])
            if leaderboard:
                killer = leaderboard[0]['user_id']
                killer_name = get_user_dao_name(killer)
                msg += f"\n『击杀者: {killer_name}』"
        # 获取伤害排行榜前10名
        leaderboard = get_boss_damage_leaderboard(boss['id'])
        if leaderboard:
            msg += "\n\n☆------伤害排行榜前10名------☆"
            for idx, entry in enumerate(leaderboard, start=1):
                user_id = entry['user_id']
                user_name = get_user_dao_name(user_id)
                total_damage = entry['total_damage']
                msg += f"\n{idx}.『{user_name}』(伤害: {number_to(total_damage)})"

        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_info.finish()
    else:  # 查所有Boss信息
        bossmsgs = "\n☆------世界BOSS------☆"
        for i, boss in enumerate(all_bosses, start=1):
            if boss['hp'] == 0:
                status = ""
                # 获取击杀者信息
                if boss['hp'] == 0:
                    leaderboard = get_boss_damage_leaderboard(boss['id'])
                    if leaderboard:
                        killer = leaderboard[0]['user_id']
                        killer_name = get_user_dao_name(killer)
                        status += f"『击杀者: {killer_name}』"
                        bossmsgs += f"\n已击杀: {boss['jj']}Boss:{boss['name']} {status}"
            else:
                status = "(状态: 存活中)"
                bossmsgs += f"\n编号{i}: {boss['jj']} Boss:{boss['name']} {status}"
        msg = bossmsgs
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_info.finish()


@boss_delete_all.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_delete_all_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """天罚全部世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete_all.finish()

    # 获取所有Boss信息
    all_bosses = get_all_bosses()

    if not all_bosses:
        msg = f"当前没有生成的世界Boss,请等待世界boss刷新!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete_all.finish()

    # 删除所有Boss
    for boss in all_bosses:
        delete_boss(boss['id'])

    msg = f"所有的世界Boss都烟消云散了~~"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await boss_delete_all.finish()


@boss_delete.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_delete_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """天罚世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip()
    group_id = str(event.group_id)
    boss_num = re.findall(r"\d+", msg)  # boss编号

    if not sql_message.is_boss_enabled(group_id):  # 不在配置表内
        msg = f"本群尚未开启世界Boss,请联系管理员开启!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    try:
        boss_num = int(boss_num[0])
    except IndexError:
        msg = f"请输入正确的世界Boss编号!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    # 获取所有Boss信息
    all_bosses = get_all_bosses()

    if not all_bosses:
        msg = f"当前没有生成的世界Boss,请等待世界boss刷新!"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    if not (0 < boss_num <= len(all_bosses)):
        msg = f"请输入正确的世界Boss编号! 当前共有 {len(all_bosses)} 个Boss。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    # 获取指定编号的Boss
    target_boss = all_bosses[boss_num - 1]

    # 删除指定的Boss
    delete_boss(target_boss['id'])
    msg = f"该世界Boss被突然从天而降的神雷劈中,烟消云散了"
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await boss_delete.finish()
