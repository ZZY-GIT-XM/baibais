from psycopg2.extras import DictCursor
from psycopg2.sql import SQL, Identifier

try:
    import ujson as json
except ImportError:
    import json
import os
import random
import psycopg2  # 新增：导入PostgreSQL的Python库
from psycopg2 import sql
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from nonebot.log import logger
from .data_source import jsondata
from .. import DRIVER
from .xn_xiuxian_impart_config import config_impart
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.item_database_handler import Items

WORKDATA = Path() / "data" / "xiuxian" / "work"
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"
DATABASE = Path() / "data" / "xiuxian"
DATABASE_IMPARTBUFF = Path() / "data" / "xiuxian"
SKILLPATHH = DATABASE / "功法"
WEAPONPATH = DATABASE / "装备"
xiuxian_num = "578043031"  # 这里其实是修仙1作者的QQ号
impart_num = "123451234"
items = Items()
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')


class XiuxianDateManage:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XiuxianDateManage, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._connect_to_db()
            self._check_data()

    def _connect_to_db(self):
        try:
            self.conn = psycopg2.connect(
                dbname="baibaidb",
                user="postgres",
                password="robots666",
                host="localhost",
                port=5432
            )
            self.conn.autocommit = True  # 确保每次操作都自动提交
            logger.opt(colors=True).info("<green>修仙数据库已连接！</green>")
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            logger.opt(colors=True).info("<green>修仙数据库关闭！</green>")

    def _check_data(self):
        """检查数据完整性"""
        try:
            with self.conn.cursor() as c:
                tables = [
                    "user_xiuxian",
                    "user_cd",
                    "sects",
                    "back",
                    "buffinfo",
                    "xiuxian_wupin_jichu",
                    "xiuxian_fangju",
                    "xiuxian_shentong",
                    "xiuxian_faqi",
                    "xiuxian_gongfa",
                    "xiuxian_fuxiu_gongfa",
                    "xiuxian_xiulian_wupin",
                    "xiuxian_danyao",
                    "xiuxian_liandandanyao",
                    "xiuxian_liandanlu",
                    "xiuxian_shenwu",
                    "xiuxian_yaocai",
                    "xiuxian_jingjie",
                    "xiuxian_group_config"
                ]
                for table_name in tables:
                    try:
                        c.execute(f"SELECT COUNT(1) FROM {table_name}")
                    except psycopg2.ProgrammingError:
                        logger.warning(f"表 {table_name} 不存在，正在创建...")
                        self._create_table(c, table_name)

                # 检查并添加缺失字段
                self._add_missing_columns(c, "user_xiuxian", XiuConfig().sql_user_xiuxian)
                self._add_missing_columns(c, "user_cd", XiuConfig().sql_user_cd)
                self._add_missing_columns(c, "sects", XiuConfig().sql_sects)
                self._add_missing_columns(c, "back", XiuConfig().sql_back)
                self._add_missing_columns(c, "buffinfo", XiuConfig().sql_buff)
                self._add_missing_columns(c, "xiuxian_wupin_jichu", XiuConfig().sql_xiuxian_wupin_jichu)
                self._add_missing_columns(c, "xiuxian_fangju", XiuConfig().sql_xiuxian_fangju)
                self._add_missing_columns(c, "xiuxian_shentong", XiuConfig().sql_xiuxian_shentong)
                self._add_missing_columns(c, "xiuxian_faqi", XiuConfig().sql_xiuxian_faqi)
                self._add_missing_columns(c, "xiuxian_gongfa", XiuConfig().sql_xiuxian_gongfa)
                self._add_missing_columns(c, "xiuxian_fuxiu_gongfa", XiuConfig().sql_xiuxian_fuxiu_gongfa)
                self._add_missing_columns(c, "xiuxian_xiulian_wupin", XiuConfig().sql_xiuxian_xiulian_wupin)
                self._add_missing_columns(c, "xiuxian_danyao", XiuConfig().sql_xiuxian_danyao)
                self._add_missing_columns(c, "xiuxian_liandandanyao", XiuConfig().sql_xiuxian_liandandanyao)
                self._add_missing_columns(c, "xiuxian_liandanlu", XiuConfig().sql_xiuxian_liandanlu)
                self._add_missing_columns(c, "xiuxian_shenwu", XiuConfig().sql_xiuxian_shenwu)
                self._add_missing_columns(c, "xiuxian_yaocai", XiuConfig().sql_xiuxian_yaocai)
                self._add_missing_columns(c, "xiuxian_jingjie", XiuConfig().sql_xiuxian_jingjie)
                self._add_missing_columns(c, "xiuxian_group_config", XiuConfig().sql_xiuxian_group_config)
                self._add_missing_columns(c, "xiuxian_bank_info", XiuConfig().sql_xiuxian_bank_info)
                self._add_missing_columns(c, "xiuxian_bank_levels", XiuConfig().sql_xiuxian_bank_levels)
                self._add_missing_columns(c, "xiuxian_mijing_config", XiuConfig().sql_xiuxian_mijing_config)
                self._add_missing_columns(c, "xiuxian_mijing_info", XiuConfig().sql_xiuxian_mijing_info)

                self.conn.commit()
        except psycopg2.Error as e:
            logger.error(f"数据库操作失败: {e}")
            self.conn.rollback()

    def _create_table(self, cursor, table_name):
        """根据表名创建表"""
        create_table_sql = {
            "user_xiuxian": """
                CREATE TABLE IF NOT EXISTS "user_xiuxian" (  -- 用户表
                    "id" SERIAL PRIMARY KEY, -- 数据唯一id
                    "user_id" NUMERIC NOT NULL,  -- 用户id
                    "user_name" TEXT DEFAULT NULL, -- 名称
                    "user_sex" TEXT, -- 性别
                    "stone" NUMERIC, -- 灵石数量
                    "root" TEXT, -- 灵根名称
                    "root_type" TEXT, -- 灵根类型
                    "level" TEXT, -- 境界等级
                    "power" NUMERIC DEFAULT 0,  -- 战斗力
                    "create_time" TIMESTAMP, -- 创建时间
                    "is_sign" NUMERIC DEFAULT 0,
                    "is_beg" NUMERIC DEFAULT 0,
                    "is_ban" NUMERIC DEFAULT 0,
                    "exp" NUMERIC DEFAULT 0,  -- 修为
                    "work_num" NUMERIC DEFAULT 0, -- 悬赏次数
                    "level_up_cd" TIMESTAMP,
                    "level_up_rate" NUMERIC DEFAULT 0,
                    "sect_id" NUMERIC DEFAULT NULL,  -- 宗门ID
                    "sect_position" NUMERIC DEFAULT NULL,  -- 宗门职位
                    "hp" NUMERIC DEFAULT 0,  -- 血量
                    "mp" NUMERIC DEFAULT 0,  -- 真元
                    "atk" NUMERIC DEFAULT 0,  -- 攻击力
                    "atkpractice" NUMERIC DEFAULT 0,
                    "sect_task" NUMERIC DEFAULT 0,
                    "sect_contribution" NUMERIC DEFAULT 0,
                    "sect_elixir_get" NUMERIC DEFAULT 0,
                    "blessed_spot_flag" NUMERIC DEFAULT 0,
                    "blessed_spot_name" TEXT DEFAULT NULL,
                    "user_stamina" NUMERIC DEFAULT 0,  -- 体力
                    "consecutive_wins" NUMERIC DEFAULT 0,  -- 鉴石胜利次数
                    "consecutive_losses" NUMERIC DEFAULT 0,  -- 鉴石失败次数
                    "poxian_num" NUMERIC DEFAULT 0,  -- 轮回次数
                    "rbPts" NUMERIC DEFAULT 0,  -- 轮回点数
                    "cultEff" NUMERIC DEFAULT 0,  -- 修炼加点数
                    "seclEff" NUMERIC DEFAULT 0,  -- 闭关加点数
                    "maxR" NUMERIC DEFAULT 0,  -- 灵根加点数
                    "maxH" NUMERIC DEFAULT 0,  -- 血量加点数
                    "maxM" NUMERIC DEFAULT 0,  -- 真元加点数
                    "maxA" NUMERIC DEFAULT 0  -- 攻击加点数
                );
            """,
            "user_cd": """
                CREATE TABLE IF NOT EXISTS "user_cd" (  -- 用户CD表
                    "user_id" NUMERIC NOT NULL PRIMARY KEY,
                    "type" NUMERIC DEFAULT 0,
                    "create_time" TIMESTAMP DEFAULT NULL,
                    "scheduled_time" TEXT DEFAULT NULL,
                    "last_check_info_time" TIMESTAMP DEFAULT NULL
                );
            """,
            "sects": """
                CREATE TABLE IF NOT EXISTS "sects" (   -- 宗门表
                    "sect_id" SERIAL PRIMARY KEY,
                    "sect_name" TEXT NOT NULL,
                    "sect_owner" NUMERIC,
                    "sect_scale" NUMERIC NOT NULL,
                    "sect_used_stone" NUMERIC,
                    "sect_fairyland" TEXT,
                    "sect_materials" NUMERIC DEFAULT 0,
                    "mainbuff" NUMERIC DEFAULT 0,
                    "secbuff" NUMERIC DEFAULT 0,
                    "elixir_room_level" NUMERIC DEFAULT 0
                );
            """,
            "back": """
                CREATE TABLE IF NOT EXISTS "back" (  -- 背包
                    "user_id" NUMERIC NOT NULL,
                    "goods_id" NUMERIC NOT NULL,
                    "goods_name" TEXT,
                    "goods_type" TEXT,
                    "goods_num" NUMERIC,
                    "create_time" TIMESTAMP,
                    "update_time" TIMESTAMP,
                    "remake" TEXT,
                    "day_num" NUMERIC DEFAULT 0,
                    "all_num" NUMERIC DEFAULT 0,
                    "action_time" TIMESTAMP,
                    "state" NUMERIC DEFAULT 0,
                    "bind_num" NUMERIC DEFAULT 0
                );
            """,
            "buffinfo": """
                CREATE TABLE IF NOT EXISTS "buffinfo" ( -- buff加成
                    "id" SERIAL PRIMARY KEY,
                    "user_id" NUMERIC DEFAULT 0,
                    "main_buff" NUMERIC DEFAULT 0,
                    "sec_buff" NUMERIC DEFAULT 0,
                    "faqi_buff" NUMERIC DEFAULT 0,
                    "fabao_weapon" NUMERIC DEFAULT 0,
                    "armor_buff" NUMERIC DEFAULT 0,
                    "atk_buff" NUMERIC DEFAULT 0,
                    "sub_buff" NUMERIC DEFAULT 0,
                    "blessed_spot" NUMERIC DEFAULT 0
                );
            """,
            "xiuxian_wupin_jichu": """
                CREATE TABLE IF NOT EXISTS "xiuxian_wupin_jichu" (
                    "item_id" SERIAL PRIMARY KEY, -- 物品唯一标识符
                    "item_name" VARCHAR(255) NOT NULL, -- 物品名称
                    "item_type" VARCHAR(50) NOT NULL, -- 物品类型（如：装备、丹药、法器等）
                    "type" VARCHAR(50) NOT NULL, -- 物品类型（如：装备、丹药、法器等）
                    "description" TEXT -- 物品描述
                );
            """,
            "xiuxian_fangju": """
                CREATE TABLE IF NOT EXISTS "xiuxian_fangju" (
                    "item_id" INT PRIMARY KEY, -- 防具ID
                    "level" VARCHAR(50), -- 装备等级（如：下品符器）
                    "def_buff" REAL, -- 减伤加成
                    "atk_buff" REAL, -- 攻击加成
                    "crit_buff" REAL, -- 会心加成
                    "rank" INT, -- 防具获取等级相关
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_shentong": """
                CREATE TABLE IF NOT EXISTS "xiuxian_shentong" (
                    "item_id" INT PRIMARY KEY, -- 神通ID
                    "skill_type" INT, -- 技能类型
                    "atkvalue" REAL[], -- 攻击值数组
                    "hpcost" REAL, -- 生命消耗
                    "mpcost" REAL, -- 真元消耗
                    "turncost" INT, -- 使用回合数
                    "jndesc" VARCHAR(50), -- 攻击时的文字描述
                    "rate" INT, -- 成功率
                    "rank" VARCHAR(50), -- 神通品质
                    "level" INT, -- 神通等级
                    "bufftype" INT, -- buff类型
                    "buffvalue" REAL, -- buff值
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_faqi": """
                CREATE TABLE IF NOT EXISTS "xiuxian_faqi" (
                    "item_id" INT PRIMARY KEY, -- 法器ID
                    "atk_buff" REAL, -- 攻击力加成
                    "crit_buff" REAL, -- 会心加成
                    "def_buff" REAL, -- 减伤加成
                    "critatk" REAL, -- 会心伤害加成
                    "zw" REAL, -- 附加属性
                    "mp_buff" REAL, -- 真元/魔法值加成
                    "rank" INT, -- 法器获取等级相关
                    "level" VARCHAR(50), -- 法器等级（如：下品符器）
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_gongfa": """
                CREATE TABLE IF NOT EXISTS "xiuxian_gongfa" (
                    "item_id" INT PRIMARY KEY, -- 功法ID
                    "hpbuff" REAL, -- 生命值加成
                    "mpbuff" REAL, -- 真元值加成
                    "atkbuff" REAL, -- 攻击力加成
                    "ratebuff" REAL, -- 成功率加成
                    "crit_buff" REAL, -- 暴击率加成
                    "def_buff" REAL, -- 防御力加成
                    "dan_exp" REAL, -- 丹药经验加成
                    "dan_buff" REAL, -- 丹药效果加成
                    "reap_buff" REAL, -- 收获加成
                    "exp_buff" REAL, -- 经验加成
                    "critatk" REAL, -- 暴击伤害加成
                    "two_buff" REAL, -- 双修次数加成
                    "number" INT, -- 数量
                    "clo_exp" REAL, -- 闭关经验加成
                    "clo_rs" REAL, -- 闭关恢复加成
                    "random_buff" REAL, -- 随机效果加成
                    "ew" REAL, -- 额外效果
                    "rank" INT, -- 功法品质
                    "level" VARCHAR(50), -- 功法等级
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_fuxiu_gongfa": """
                CREATE TABLE IF NOT EXISTS "xiuxian_fuxiu_gongfa" (
                    "item_id" INT PRIMARY KEY, -- 辅修功法ID
                    "buff_type" VARCHAR(50), -- 加成类型
                    "buff" REAL, -- 加成值
                    "buff2" REAL, -- 第二个加成值
                    "stone" REAL, -- 石头加成
                    "integral" REAL, -- 积分加成
                    "jin" REAL, -- 进阶加成
                    "drop" REAL, -- 掉落加成
                    "fan" REAL, -- 反弹加成
                    "break" REAL, -- 破防加成
                    "exp" REAL, -- 经验加成
                    "rank" INT, -- 辅修功法品质
                    "level" VARCHAR(50), -- 辅修功法等级
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_xiulian_wupin": """
                CREATE TABLE IF NOT EXISTS "xiuxian_xiulian_wupin" (
                    "item_id" INT PRIMARY KEY, -- 修炼物品ID
                    "type" VARCHAR(50), -- 类型（如：聚灵旗）
                    "cultivation_speed" REAL, -- 修炼速度
                    "herb_speed" REAL, -- 药材生长速度
                    "rank" INT, -- 修炼物品排名
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_danyao": """
                CREATE TABLE IF NOT EXISTS "xiuxian_danyao" (
                    "item_id" INT PRIMARY KEY, -- 丹药ID
                    "buff_type" VARCHAR(50), -- 加成类型
                    "buff" REAL, -- 加成值
                    "price" REAL, -- 价格
                    "selling" REAL, -- 销售价格
                    "realm" VARCHAR(50), -- 适用境界
                    "status" INT, -- 状态
                    "quantity" INT, -- 数量
                    "day_num" INT, -- 日使用次数
                    "all_num" INT, -- 总使用次数
                    "rank" INT, -- 丹药排名
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_liandandanyao": """
                CREATE TABLE IF NOT EXISTS "xiuxian_liandandanyao" (
                    "item_id" INT PRIMARY KEY, -- 炼丹丹药ID
                    "buff_type" VARCHAR(50), -- 加成类型
                    "all_num" INT, -- 总使用次数
                    "buff" REAL, -- 加成值
                    "realm" VARCHAR(50), -- 适用境界
                    "mix_need_time" INT, -- 混合所需时间
                    "mix_exp" REAL, -- 混合经验
                    "mix_all" INT, -- 总混合次数
                    "elixir_config" JSONB, -- 药材配置
                    "rank" INT, -- 丹药排名
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_liandanlu": """
                CREATE TABLE IF NOT EXISTS "xiuxian_liandanlu" (
                    "item_id" INT PRIMARY KEY, -- 炼丹炉ID
                    "type" VARCHAR(50), -- 类型（如：炼丹炉）
                    "buff" REAL, -- 加成值
                    "rank" INT, -- 炼丹炉排名
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_shenwu": """
                CREATE TABLE IF NOT EXISTS "xiuxian_shenwu" (
                    "item_id" INT PRIMARY KEY, -- 神物ID
                    "buff_type" VARCHAR(50), -- 加成类型
                    "all_num" INT, -- 总使用次数
                    "buff" REAL, -- 加成值
                    "realm" VARCHAR(50), -- 适用境界
                    "mix_need_time" INT, -- 混合所需时间
                    "mix_exp" REAL, -- 混合经验
                    "mix_all" INT, -- 总混合次数
                    "elixir_config" JSONB, -- 药材配置
                    "rank" INT, -- 神物排名
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_yaocai": """
                CREATE TABLE IF NOT EXISTS "xiuxian_yaocai" (
                    "item_id" INT PRIMARY KEY, -- 药材ID
                    "level" VARCHAR(50), -- 等级（如：五品药材）
                    "primary_ingredient" JSONB, -- 主药成分
                    "catalyst" JSONB, -- 药引成分
                    "auxiliary_ingredient" JSONB, -- 辅药成分
                    "rank" INT, -- 药材排名
                    FOREIGN KEY("item_id") REFERENCES "xiuxian_wupin_jichu"("item_id") ON DELETE CASCADE
                );
            """,
            "xiuxian_jingjie": """
                CREATE TABLE xiuxian_jingjie (
                    id SERIAL PRIMARY KEY, -- 主键，自动递增
                    jingjie_name VARCHAR(255) NOT NULL UNIQUE, -- 境界名称，唯一
                    power NUMERIC NOT NULL, -- 战斗力
                    atk NUMERIC NOT NULL, -- 攻击力
                    ac NUMERIC NOT NULL, -- 防御力
                    spend NUMERIC NOT NULL, 
                    hp NUMERIC NOT NULL, -- 生命值
                    mp NUMERIC NOT NULL, -- 法力值/真元值
                    comment INT DEFAULT 0, -- 备注字段，默认为0
                    rate INT NOT NULL, 
                    exp NUMERIC NOT NULL, -- 经验值
                    sp NUMERIC NOT NULL, 
                    sp_ra NUMERIC(6,1) NOT NULL 
                );
            """,
            "xiuxian_group_config": """
                CREATE TABLE xiuxian_group_config (
                    group_id BIGINT PRIMARY KEY,  -- 群聊id
                    enabled_xiuxian BOOLEAN NOT NULL DEFAULT FALSE,  -- 用于判断群聊是否有开启修仙功能
                    enabled_boss BOOLEAN NOT NULL DEFAULT FALSE,  -- 用于判断群聊是否有开启世界boss功能
                    enabled_paimai BOOLEAN NOT NULL DEFAULT FALSE,  -- 用于判断群聊是否有开启拍卖功能
                    enabled_mijing BOOLEAN NOT NULL DEFAULT FALSE  -- 用于判断群聊是否有开启秘境功能
                );
            """,
            "xiuxian_bank_info": """
                CREATE TABLE IF NOT EXISTS xiuxian_bank_info (
                    user_id BIGINT REFERENCES user_xiuxian(user_id),
                    savestone NUMERIC DEFAULT 0,
                    savetime TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    banklevel NUMERIC DEFAULT 1,
                    PRIMARY KEY (user_id)
                );
            """,
            "xiuxian_bank_levels": """
                CREATE TABLE IF NOT EXISTS xiuxian_bank_levels (
                    level INTEGER PRIMARY KEY,
                    save_max NUMERIC NOT NULL,
                    level_up_cost NUMERIC NOT NULL,
                    interest_rate NUMERIC(7, 4) NOT NULL,
                    level_name VARCHAR(50) NOT NULL
                );
            """,
            "xiuxian_mijing_config": """
                CREATE TABLE IF NOT EXISTS xiuxian_mijing_config (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE, -- 秘境名称
                    type_rate INTEGER NOT NULL, -- 类型概率
                    rank INTEGER NOT NULL, -- 秘境等级
                    base_count INTEGER NOT NULL, -- 基础可探索次数
                    time INTEGER NOT NULL -- 探索所需的时间（单位：分钟）
                );
            """,
            "xiuxian_mijing_info": """
                CREATE TABLE IF NOT EXISTS xiuxian_mijing_info (
                    id SERIAL PRIMARY KEY,
                    config_id INTEGER NOT NULL REFERENCES xiuxian_mijing_config(id), -- 配置ID，外键引用配置表
                    name VARCHAR(255) NOT NULL, -- 秘境名称
                    rank INTEGER NOT NULL, -- 秘境等级
                    current_count INTEGER NOT NULL, -- 当前可探索次数
                    l_user_id TEXT DEFAULT '', -- 已经参加的用户ID列表，以逗号分隔
                    time INTEGER NOT NULL, -- 探索所需的时间（单位：分钟）
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 创建时间
                );
            """
        }

        if table_name in create_table_sql:
            try:
                cursor.execute(create_table_sql[table_name])
                logger.info(f"表 {table_name} 已创建成功！")
            except psycopg2.Error as e:
                logger.error(f"创建表 {table_name} 失败: {e}")
                raise
        else:
            logger.error(f"未知表名：{table_name}")

    def _add_missing_columns(self, cursor, table_name, columns):
        """检查并添加缺失字段"""
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table_name,))
        existing_columns = [desc[0] for desc in cursor.fetchall()]

        for col in columns:
            if col not in existing_columns:
                try:
                    data_type = 'TEXT'  # 默认类型为 TEXT
                    # 先保留原有的逻辑部分
                    if col in ['power', 'atk', 'ac', 'spend', 'hp', 'mp', 'rate', 'exp', 'sp', 'sp_ra', 'savestone',
                               'banklevel', 'save_max', 'level_up_cost', 'interest_rate']:
                        data_type = 'NUMERIC'  # 对于数值类型的字段使用 NUMERIC
                    elif col == 'comment':
                        data_type = 'TEXT'  # 对于文本类型的字段使用 TEXT
                    elif col == ['jingjie_name', 'level_name']:
                        data_type = 'VARCHAR(255)'  # 对于字符串类型的字段使用 VARCHAR(255)
                    elif col in ['user_id', 'sect_id', 'sect_owner', 'sect_scale', 'sect_used_stone',
                                 'sect_fairyland', 'mainbuff', 'secbuff', 'elixir_room_level', 'goods_id', 'goods_num',
                                 'day_num', 'all_num', 'bind_num', 'level_up_rate', 'sect_position', 'consecutive_wins',
                                 'consecutive_losses', 'poxian_num', 'rbPts', 'cultEff', 'seclEff', 'maxR', 'maxH',
                                 'maxM', 'maxA', 'work_num', 'hp', 'mp', 'atk', 'atkpractice', 'sect_task',
                                 'sect_contribution', 'sect_elixir_get', 'user_stamina', 'blessed_spot_flag',
                                 'main_buff',
                                 'sec_buff', 'faqi_buff', 'fabao_weapon', 'armor_buff', 'atk_buff', 'sub_buff',
                                 'blessed_spot', 'item_id', 'level', 'rank', 'state', 'number', 'exp', 'quantity',
                                 'item_name', 'item_type', 'skill_type', 'atkvalue', 'hpcost', 'mpcost', 'turncost',
                                 'jndesc', 'rate', 'def_buff', 'atk_buff', 'crit_buff', 'critatk', 'zw', 'mp_buff',
                                 'hpbuff', 'mpbuff', 'atkbuff', 'ratebuff', 'critatk', 'two_buff', 'clo_exp', 'clo_rs',
                                 'random_buff', 'ew', 'buff_type', 'buff', 'buff2', 'stone', 'integral', 'jin', 'drop',
                                 'fan', 'break', 'dan_exp', 'dan_buff', 'reap_buff', 'exp_buff', 'cultivation_speed',
                                 'herb_speed', 'type', 'price', 'selling', 'realm', 'status', 'mix_need_time',
                                 'mix_exp', 'bufftype',
                                 'mix_all', 'elixir_config', 'primary_ingredient', 'catalyst', 'auxiliary_ingredient']:
                        data_type = 'NUMERIC' if col in ['level', 'rank', 'state', 'number', 'exp',
                                                         'quantity'] else 'VARCHAR(255)'
                    # 新增对于时间戳类型字段的支持
                    elif col in ['create_time', 'scheduled_time', 'last_check_info_time', 'action_time', 'update_time',
                                 'savetime']:
                        data_type = 'TIMESTAMP'
                    # 新增对于 xiuxian_group_config 表的字段支持
                    elif col == 'group_id':
                        data_type = 'BIGINT'
                    elif col == 'buffvalue':
                        data_type = 'REAL'
                    elif col == ['enabled_xiuxian', 'enabled_paimai', 'enabled_boss', 'enabled_mijing']:
                        data_type = 'BOOLEAN NOT NULL DEFAULT FALSE'

                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {data_type} DEFAULT NULL")
                    print(f"字段 {col} 添加成功！")
                except Exception as e:
                    print(f"添加字段 {col} 失败: {e}")
                    raise

    @classmethod
    def close_dbs(cls):
        instance = cls()
        instance.close()

    def _create_user(self, user_id, root, root_type, power, create_time, user_name) -> None:
        """在数据库中创建用户并初始化"""
        c = self.conn.cursor()

        # 检查 user_id 是否已存在
        c.execute("SELECT * FROM user_xiuxian WHERE user_id = %s", (user_id,))
        existing_user = c.fetchone()

        if existing_user:
            # 如果用户已存在，更新某些字段
            sql_update = """
                UPDATE "user_xiuxian"
                SET "root" = %s, "root_type" = %s, "level" = %s, "power" = %s, "create_time" = %s
                WHERE "user_id" = %s;
            """
            params_update = (
                root,  # root
                root_type,  # root_type
                '江湖好手',  # level
                power,  # power
                create_time,  # create_time
                user_id  # user_id
            )
            c.execute(sql_update, params_update)
        else:
            sql_insert = """
                INSERT INTO "user_xiuxian" 
                ("user_id", "user_name", "stone", "root", "root_type", "level", "power", "create_time", "user_sex","is_sign", "is_beg", "is_ban", "exp", "work_num", "level_up_cd", "level_up_rate", "sect_id", "sect_position", "hp", "mp", "atk", "atkpractice", "sect_task", "sect_contribution", "sect_elixir_get", "blessed_spot_flag", "blessed_spot_name", "user_stamina", "consecutive_wins", "consecutive_losses", "poxian_num", "rbPts", "cultEff", "seclEff", "maxR", "maxH", "maxM", "maxA")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            default_values = (
                None,  # user_sex
                0,  # is_sign
                0,  # is_beg
                0,  # is_ban
                0,  # exp
                0,  # work_num
                None,  # level_up_cd
                0,  # level_up_rate
                None,  # sect_id
                None,  # sect_position
                50,  # hp
                100,  # mp
                10,  # atk
                0,  # atkpractice
                0,  # sect_task
                0,  # sect_contribution
                0,  # sect_elixir_get
                0,  # blessed_spot_flag
                None,  # blessed_spot_name
                500,  # user_stamina
                0,  # consecutive_wins
                0,  # consecutive_losses
                0,  # poxian_num
                0,  # rbPts
                0,  # cultEff
                0,  # seclEff
                0,  # maxR
                0,  # maxH
                0,  # maxM
                0  # maxA
            )
            params_insert = (
                                user_id,  # user_id
                                user_name,  # user_name
                                0,  # stone
                                root,  # root
                                root_type,  # root_type
                                '江湖好手',  # level
                                power,  # power
                                create_time,  # create_time
                            ) + default_values
            c.execute(sql_insert, params_insert)
        self.conn.commit()

    def get_user_info_with_id(self, user_id):
        """根据USER_ID获取用户信息,不获取功法加成"""
        cur = self.conn.cursor()
        sql = "SELECT * FROM user_xiuxian WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def get_user_real_info(self, user_id):
        """根据USER_ID获取用户信息,获取功法加成"""
        cur = self.conn.cursor()
        sql = "SELECT * FROM user_xiuxian WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = cur.description
            user_data_dict = final_user_data(result, columns)
            return user_data_dict
        else:
            return None

    def update_user_gender(self, user_id, user_sex):
        """更新用户的性别"""
        cur = self.conn.cursor()
        # 更新用户性别的SQL语句
        sql = "UPDATE user_xiuxian SET user_sex=%s WHERE user_id=%s"
        try:
            # 执行SQL语句
            cur.execute(sql, (user_sex, user_id))
            # 提交事务
            self.conn.commit()
            return True  # 成功更新
        except Exception as e:
            # 回滚事务
            self.conn.rollback()
            raise e  # 抛出异常以便调用者可以捕获和处理

    def update_user_random_gender(self, user_id):
        """更新用户的性别，随机生成一个新的性别"""
        cur = self.conn.cursor()
        genders = ['男', '女']
        new_gender = random.choice(genders)
        # 更新用户性别的SQL语句
        sql = "UPDATE user_xiuxian SET user_sex=%s WHERE user_id=%s"
        try:
            # 执行SQL语句
            cur.execute(sql, (new_gender, user_id))
            # 提交事务
            self.conn.commit()
            return new_gender  # 返回新生成的性别
        except Exception as e:
            # 回滚事务
            self.conn.rollback()
            raise e  # 抛出异常以便调用者可以捕获和处理

    def get_random_user_id(self):
        """
        从数据库中随机获取一个用户ID。

        :return: 随机用户ID
        """
        cur = self.conn.cursor()
        # 获取所有用户的ID
        sql = "SELECT user_id FROM user_xiuxian"
        cur.execute(sql)
        user_ids = [row[0] for row in cur.fetchall()]
        # 如果没有用户，则返回None
        if not user_ids:
            return None
        # 随机选取一个用户ID
        return random.choice(user_ids)

    def get_user_info_with_name(self, user_name):
        """根据user_name获取用户信息"""
        cur = self.conn.cursor()
        sql = "SELECT * FROM user_xiuxian WHERE user_name = %s"
        cur.execute(sql, (user_name,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def update_all_users_stamina(self, max_stamina, stamina_recovery_rate):
        """体力未满用户更新体力值"""
        try:
            with self.conn.cursor() as cur:
                sql = """
                    UPDATE user_xiuxian
                    SET user_stamina = LEAST(user_stamina + %s, %s)
                    WHERE user_stamina < %s;
                """
                cur.execute(sql, (stamina_recovery_rate, max_stamina, max_stamina))
                self.conn.commit()
                # logger.info("所有用户的体力已更新！")
        except psycopg2.Error as e:
            logger.error(f"更新所有用户体力失败: {e}")
            self.conn.rollback()

    def update_user_stamina(self, user_id, stamina_change, key):
        """更新用户体力值 1为增加，2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = "UPDATE user_xiuxian SET user_stamina=user_stamina+%s WHERE user_id=%s"
            cur.execute(sql, (stamina_change, user_id))
            self.conn.commit()
        elif key == 2:
            sql = "UPDATE user_xiuxian SET user_stamina=user_stamina-%s WHERE user_id=%s"
            cur.execute(sql, (stamina_change, user_id))
            self.conn.commit()

    def get_sect_info(self, sect_id):
        """
        通过宗门编号获取宗门信息
        :param sect_id: 宗门编号
        :return:
        """
        cur = self.conn.cursor()
        sql = "SELECT * FROM sects WHERE sect_id = %s"
        cur.execute(sql, (sect_id,))
        result = cur.fetchone()
        if result:
            sect_id_dict = dict(zip((col[0] for col in cur.description), result))
            return sect_id_dict
        else:
            return None

    def get_sect_owners(self):
        """获取所有宗主的 user_id"""
        cur = self.conn.cursor()
        sql = "SELECT user_id FROM user_xiuxian WHERE sect_position = 0"
        cur.execute(sql)
        result = cur.fetchall()
        return [row[0] for row in result]

    def get_elders(self):
        """获取所有长老的 user_id"""
        cur = self.conn.cursor()
        sql = "SELECT user_id FROM user_xiuxian WHERE sect_position = 1"
        cur.execute(sql)
        result = cur.fetchall()
        return [row[0] for row in result]

    def create_user(self, user_id, root, root_type, power, create_time, user_name):
        """校验用户是否存在"""
        cur = self.conn.cursor()
        sql = "SELECT * FROM user_xiuxian WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if not result:
            # 检查 args 是否有足够的元素
            if len((root, root_type, power, create_time, user_name)) >= 5:
                self._create_user(user_id, root, root_type, power, create_time, user_name)
                self.conn.commit()
                welcome_msg = f"欢迎进入修仙世界的【{user_name}】，你的灵根为：{root}，类型是：{root_type}，你的战力为：{power}，当前境界：江湖好手"
                return True, welcome_msg
            else:
                raise ValueError("提供的参数不足，无法创建新用户。")
        else:
            return False, "您已迈入修仙世界，输入【我的修仙信息】获取数据吧！"

    def get_sign(self, user_id):
        """获取用户签到信息"""
        cur = self.conn.cursor()
        sql = "SELECT is_sign FROM user_xiuxian WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if not result:
            return f"修仙界没有你的足迹，输入 我要修仙 加入修仙世界吧！"
        elif result[0] == 0:
            ls = random.randint(XiuConfig().sign_in_lingshi_lower_limit, XiuConfig().sign_in_lingshi_upper_limit)
            sql2 = "UPDATE user_xiuxian SET is_sign = 1, stone = stone + %s WHERE user_id = %s"
            cur.execute(sql2, (ls, user_id))
            self.conn.commit()
            return f"签到成功，获取{ls}块灵石!"
        elif result[0] == 1:
            return f"贪心的人是不会有好运的！"

    def get_beg(self, user_id):
        """获取仙途奇缘信息"""
        cur = self.conn.cursor()
        sql = "SELECT is_beg FROM user_xiuxian WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result and result[0] == 0:
            ls = random.randint(XiuConfig().beg_lingshi_lower_limit, XiuConfig().beg_lingshi_upper_limit)
            sql2 = "UPDATE user_xiuxian SET is_beg = 1, stone = stone + %s WHERE user_id = %s"
            cur.execute(sql2, (ls, user_id))
            self.conn.commit()
            return ls
        elif result and result[0] == 1:
            return None

    def ramaker(self, lg, type, user_id):
        """洗灵根"""
        cur = self.conn.cursor()
        sql = "UPDATE user_xiuxian SET root = %s, root_type = %s, stone = stone - %s WHERE user_id = %s"
        cur.execute(sql, (lg, type, XiuConfig().remake, user_id))
        self.conn.commit()

        self.update_power2(user_id)  # 更新战力
        return f"逆天之行，重获新生，新的灵根为：{lg}，类型为：{type}"

    def get_root_rate(self, name):
        """获取灵根倍率"""
        data = jsondata.root_data()
        return data[name]['type_speeds']

    def get_level_power(self, name):
        """获取境界倍率|exp"""
        data = jsondata.level_data()
        return data[name]['power']

    def get_level_cost(self, name):
        """获取炼体境界倍率"""
        data = jsondata.exercises_level_data()
        return data[name]['cost_exp'], data[name]['cost_stone']

    def update_power2(self, user_id) -> None:
        """更新战力"""
        UserMessage = self.get_user_info_with_id(user_id)
        cur = self.conn.cursor()
        level = jsondata.level_data()
        root = jsondata.root_data()
        poxian_num = UserMessage['poxian_num']  # 获取用户当前破限次数
        poxian_num = Decimal(str(poxian_num))
        if poxian_num <= 10:  # 根据破限次数计算增幅系数
            bonus = 1 + (poxian_num * Decimal('0.1'))  # 1~10次，每次增加10%
        else:
            bonus = 1 + (10 * Decimal('0.1')) + ((poxian_num - 10) * Decimal('0.2'))  # 11次及以上，每次增加20%

        exp = Decimal(str(UserMessage['exp']))
        type_speeds = Decimal(str(root[UserMessage['root_type']]["type_speeds"]))
        spend = Decimal(str(level[UserMessage['level']]["spend"]))
        maxR = Decimal(str(UserMessage['maxR']))
        bonus = Decimal(str(bonus))

        # 计算最终的战力值
        power = round(exp * type_speeds * spend * bonus * (1 + (maxR / Decimal('100'))), 0)

        sql = "UPDATE user_xiuxian SET power = %s WHERE user_id = %s"  # 更新数据库中的战力值
        cur.execute(sql, (power, user_id))
        self.conn.commit()

    def update_ls(self, user_id, price, key):
        """更新用户灵石  1为增加，2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = "UPDATE user_xiuxian SET stone = stone + %s WHERE user_id = %s"
            cur.execute(sql, (price, user_id))
            self.conn.commit()
        elif key == 2:
            sql = "UPDATE user_xiuxian SET stone = stone - %s WHERE user_id = %s"
            cur.execute(sql, (price, user_id))
            self.conn.commit()

    def get_bank_info(self, user_id):
        """获取用户灵庄信息"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM xiuxian_bank_info WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            if result:
                columns = [column[0] for column in cur.description]
                bank_dict = dict(zip(columns, result))
                return bank_dict
            else:
                return None

    def insert_bank_info(self, user_id):
        """插入用户灵庄信息（如果不存在）"""
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO xiuxian_bank_info (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                        (user_id,))
            self.conn.commit()

    def update_bank_info(self, user_id, **kwargs):
        """更新用户灵庄信息"""
        set_clause = SQL(', ').join([Identifier(k) + SQL(' = %s') for k in kwargs])
        query = SQL("UPDATE xiuxian_bank_info SET {} WHERE user_id = %s").format(set_clause)
        values = list(kwargs.values()) + [user_id]

        with self.conn.cursor() as cur:
            cur.execute(query, values)
            self.conn.commit()

    def get_bank_level(self, level):
        """获取灵庄级别信息"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM xiuxian_bank_levels WHERE level = %s", (level,))
            result = cur.fetchone()
        if result:
            return {
                'level': result[0],
                'save_max': result[1],
                'level_up_cost': result[2],
                'interest_rate': result[3],
                'level_name': result[4]
            }
        return None

    def get_max_bank_level(self):
        """获取最高级别的信息"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:  # 使用字典游标
            cur.execute("SELECT * FROM xiuxian_bank_levels ORDER BY level DESC LIMIT 1")
            max_level_info = cur.fetchone()
        return max_level_info or {}

    def update_stone(self, user_id, rate):
        """更新突破成功率"""
        sql = "UPDATE user_xiuxian SET stone = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (rate, user_id))
        self.conn.commit()

    def get_consecutive_wins_and_losses(self, user_id):
        """获取用户的连胜和连败次数"""
        cur = self.conn.cursor()
        sql = "SELECT consecutive_wins, consecutive_losses FROM user_xiuxian WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            return result
        else:
            # 如果用户不存在，则插入默认值
            self.insert_default_consecutive_wins_and_losses(user_id)
            return (0, 0)

    def insert_default_consecutive_wins_and_losses(self, user_id):
        """插入用户的默认连胜和连败次数"""
        cur = self.conn.cursor()
        sql = "INSERT INTO user_xiuxian (user_id, consecutive_wins, consecutive_losses) VALUES (%s, %s, %s)"
        cur.execute(sql, (user_id, 0, 0))
        self.conn.commit()

    def update_consecutive_wins_and_losses(self, user_id, wins, losses):
        """更新用户的连胜和连败次数"""
        cur = self.conn.cursor()
        sql = "UPDATE user_xiuxian SET consecutive_wins = %s, consecutive_losses = %s WHERE user_id = %s"
        cur.execute(sql, (wins, losses, user_id))
        self.conn.commit()

    def update_poxian_num(self, user_id):
        """更新用户打破极限的次数"""
        cur = self.conn.cursor()
        sql = "UPDATE user_xiuxian SET poxian_num = poxian_num + 1 WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_root(self, user_id, key):
        """更新灵根  1为混沌,2为融合,3为超,4为龙,5为天,6为千世,7为万世"""
        cur = self.conn.cursor()
        if int(key) == 1:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("全属性灵根", "混沌灵根", user_id))
            root_name = "混沌灵根"
            self.conn.commit()

        elif int(key) == 2:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("融合万物灵根", "融合灵根", user_id))
            root_name = "融合灵根"
            self.conn.commit()

        elif int(key) == 3:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("月灵根", "超灵根", user_id))
            root_name = "超灵根"
            self.conn.commit()

        elif int(key) == 4:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("言灵灵根", "龙灵根", user_id))
            root_name = "龙灵根"
            self.conn.commit()

        elif int(key) == 5:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("金灵根", "天灵根", user_id))
            root_name = "天灵根"
            self.conn.commit()

        elif int(key) == 6:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("千劫不死", "轮回道果", user_id))
            root_name = "轮回道果"
            self.conn.commit()

        elif int(key) == 7:
            sql = "UPDATE user_xiuxian SET root = %s, root_type = %s WHERE user_id = %s"
            cur.execute(sql, ("万劫不灭", "真·轮回道果", user_id))
            root_name = "真·轮回道果"
            self.conn.commit()

        return root_name  # 返回灵根名称

    def update_ls_all(self, price):
        """所有用户增加灵石"""
        cur = self.conn.cursor()
        sql = "UPDATE user_xiuxian SET stone = stone + %s"
        cur.execute(sql, (price,))
        self.conn.commit()

    def get_exp_rank(self, user_id):
        """修为排行"""
        sql = """
            SELECT rank 
            FROM (
                SELECT user_id, exp, dense_rank() OVER (ORDER BY exp DESC) AS rank
                FROM user_xiuxian
            ) subquery
            WHERE user_id = %s
        """
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        return result

    def get_stone_rank(self, user_id):
        """灵石排行"""
        sql = """
            SELECT rank 
            FROM (
                SELECT user_id, stone, dense_rank() OVER (ORDER BY stone DESC) AS rank
                FROM user_xiuxian
            ) subquery
            WHERE user_id = %s
        """
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        return result

    def get_ls_rank(self):
        """灵石排行榜"""
        sql = """
            SELECT user_id, stone 
            FROM user_xiuxian 
            WHERE stone > 0 
            ORDER BY stone DESC 
            LIMIT 5
        """
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def sign_remake(self):
        """重置签到"""
        sql = "UPDATE user_xiuxian SET is_sign = 0"
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def beg_remake(self):
        """重置仙途奇缘"""
        sql = "UPDATE user_xiuxian SET is_beg = 0"
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def ban_user(self, user_id):
        """小黑屋"""
        sql = "UPDATE user_xiuxian SET is_ban = 1 WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_name(self, user_id, user_name):
        """更新用户道号"""
        cur = self.conn.cursor()
        get_name = "SELECT user_name FROM user_xiuxian WHERE user_name = %s"
        cur.execute(get_name, (user_name,))
        result = cur.fetchone()
        if result:
            return "已存在该道号！"
        else:
            sql = "UPDATE user_xiuxian SET user_name = %s WHERE user_id = %s"
            cur.execute(sql, (user_name, user_id))
            self.conn.commit()
            return f'道友修改道号为【{user_name}】~'

    def updata_level_cd(self, user_id):
        """更新破镜CD"""
        sql = "UPDATE user_xiuxian SET level_up_cd = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        now_time = datetime.now()
        cur.execute(sql, (now_time, user_id))
        self.conn.commit()

    def update_last_check_info_time(self, user_id):
        """更新查看修仙信息时间"""
        sql = "UPDATE user_cd SET last_check_info_time = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        now_time = datetime.now()
        cur.execute(sql, (now_time, user_id))
        self.conn.commit()

    def get_last_check_info_time(self, user_id):
        """获取最后一次查看修仙信息时间"""
        cur = self.conn.cursor()
        sql = "SELECT last_check_info_time FROM user_cd WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            # 确保 result[0] 是字符串类型
            last_check_info_time_str = result[0].strftime('%Y-%m-%d %H:%M:%S.%f') if isinstance(result[0],
                                                                                                datetime) else result[0]
            return datetime.strptime(last_check_info_time_str, '%Y-%m-%d %H:%M:%S.%f')
        else:
            return None

    def updata_level(self, user_id, level_name):
        """更新境界"""
        sql = "UPDATE user_xiuxian SET level = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (level_name, user_id))
        self.conn.commit()

    def get_user_cd(self, user_id):
        """
        获取用户操作CD
        :param user_id: QQ
        :return: 用户CD信息的字典
        """
        sql = "SELECT * FROM user_cd WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_cd_dict = dict(zip(columns, result))
            return user_cd_dict
        else:
            self.insert_user_cd(user_id)
            return None

    def insert_user_cd(self, user_id) -> None:
        """
        添加用户至CD表
        :param user_id: qq
        :return:
        """
        sql = "INSERT INTO user_cd (user_id) VALUES (%s)"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def create_sect(self, user_id, sect_name) -> None:
        """
        创建宗门
        :param user_id: qq
        :param sect_name: 宗门名称
        :return:
        """
        sql = "INSERT INTO sects(sect_name, sect_owner, sect_scale, sect_used_stone) VALUES (%s, %s, 0, 0)"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_name, user_id))
        self.conn.commit()

    def update_sect_name(self, sect_id, sect_name) -> bool:
        """
        修改宗门名称
        :param sect_id: 宗门id
        :param sect_name: 宗门名称
        :return: 返回是否更新成功的标志，True表示更新成功，False表示更新失败（已存在同名宗门）
        """
        cur = self.conn.cursor()
        get_sect_name = "SELECT sect_name FROM sects WHERE sect_name = %s"
        cur.execute(get_sect_name, (sect_name,))
        result = cur.fetchone()
        if result:
            return False
        else:
            sql = "UPDATE sects SET sect_name = %s WHERE sect_id = %s"
            cur.execute(sql, (sect_name, sect_id))
            self.conn.commit()
            return True

    def get_all_sect_names(self):
        """
        获取所有宗门名称
        :return: 所有宗门名称列表
        """
        cur = self.conn.cursor()
        sql = "SELECT sect_name FROM sects"
        cur.execute(sql)
        results = cur.fetchall()
        sect_names = [row[0] for row in results]
        cur.close()
        return sect_names

    def check_sect_name_exists(self, sect_name):
        """
        检查宗门名称是否存在
        :param sect_name: 宗门名称
        :return: 布尔值，表示宗门名称是否存在
        """
        cur = self.conn.cursor()
        sql = "SELECT COUNT(*) FROM sects WHERE sect_name = %s"
        cur.execute(sql, (sect_name,))
        count = cur.fetchone()[0]
        cur.close()
        return count > 0

    def get_sect_info_by_qq(self, user_id):
        """
        通过用户qq获取宗门信息
        :param user_id:
        :return:
        """
        cur = self.conn.cursor()
        sql = "SELECT * FROM sects WHERE sect_owner = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            sect_owner_dict = dict(zip(columns, result))
            return sect_owner_dict
        else:
            return None

    def get_sect_info_by_id(self, sect_id):
        """
        通过宗门id获取宗门信息
        :param sect_id:
        :return:
        """
        cur = self.conn.cursor()
        sql = "SELECT * FROM sects WHERE sect_id = %s"
        cur.execute(sql, (sect_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            sect_dict = dict(zip(columns, result))
            return sect_dict
        else:
            return None

    def update_usr_sect(self, user_id, usr_sect_id, usr_sect_position):
        """
        更新用户信息表的宗门信息字段
        :param user_id:
        :param usr_sect_id:
        :param usr_sect_position:
        :return:
        """
        sql = "UPDATE user_xiuxian SET sect_id = %s, sect_position = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (usr_sect_id, usr_sect_position, user_id))
        self.conn.commit()

    def update_sect_owner(self, user_id, sect_id):
        """
        更新宗门所有者
        :param user_id:
        :param sect_id:
        :return:
        """
        sql = "UPDATE sects SET sect_owner = %s WHERE sect_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, sect_id))
        self.conn.commit()

    def get_highest_contrib_user_except_current(self, sect_id, current_owner_id):
        """
        获取指定宗门的贡献最高的人，排除当前宗主
        :param sect_id: 宗门ID
        :param current_owner_id: 当前宗主的ID
        :return: 贡献最高的人的ID，如果没有则返回None
        """
        cur = self.conn.cursor()
        sql = """
        SELECT user_id
        FROM user_xiuxian
        WHERE sect_id = %s AND sect_position = 1 AND user_id != %s
        ORDER BY sect_contribution DESC
        LIMIT 1
        """
        cur.execute(sql, (sect_id, current_owner_id))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            return None

    def get_all_sect_id(self):
        """获取全部宗门id"""
        sql = "SELECT sect_id FROM sects"
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        if result:
            return [row[0] for row in result]
        else:
            return None

    def get_all_user_id(self):
        """获取全部用户id"""
        sql = "SELECT user_id FROM user_xiuxian"
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        if result:
            return [row[0] for row in result]
        else:
            return None

    def in_closing(self, user_id, the_type):
        """
        更新用户操作CD
        :param user_id: qq
        :param the_type: 0:无状态  1:闭关中  2:历练中
        :return:
        """
        now_time = None
        if the_type == 1:
            now_time = datetime.now()
        elif the_type == 0:
            now_time = None
        elif the_type == 2:
            now_time = datetime.now()
        elif the_type == 4:
            now_time = datetime.now() + timedelta(seconds=60)
        sql = "UPDATE user_cd SET type=%s, create_time=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (the_type, now_time, user_id))
        self.conn.commit()

    def update_exp(self, user_id, exp):
        """增加修为"""
        sql = "UPDATE user_xiuxian SET exp=exp+%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (int(exp), user_id))
        self.conn.commit()

    def update_j_exp(self, user_id, exp):
        """减少修为"""
        sql = "UPDATE user_xiuxian SET exp=exp-%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (int(exp), user_id))
        self.conn.commit()

    def add_rebirth_points(self, user_id, points):
        """
        增加轮回点数
        :param user_id: 用户ID
        :param points: 要增加的点数
        """
        sql = 'UPDATE user_xiuxian SET "rbPts" = "rbPts" + %s WHERE user_id = %s'
        cursor = self.conn.cursor()
        cursor.execute(sql, (int(points), user_id))
        self.conn.commit()
        cursor.close()

    def subtract_rebirth_points(self, user_id, points):
        """减少轮回点数"""
        sql = 'UPDATE user_xiuxian SET "rbPts" = "rbPts" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def add_cultivation_efficiency(self, user_id, points):
        """轮回点增加修炼效率"""
        sql = 'UPDATE user_xiuxian SET "cultEff" = "cultEff" + %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def subtract_cultivation_efficiency(self, user_id, points):
        """轮回点减少修炼效率"""
        sql = 'UPDATE user_xiuxian SET "cultEff" = "cultEff" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def add_seclusion_efficiency(self, user_id, points):
        """轮回点增加闭关效率"""
        sql = 'UPDATE user_xiuxian SET "seclEff" = "seclEff" + %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def subtract_seclusion_efficiency(self, user_id, points):
        """轮回点减少闭关效率"""
        sql = 'UPDATE user_xiuxian SET "seclEff" = "seclEff" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def add_max_root(self, user_id, points):
        """轮回点增加灵根上限"""
        sql = 'UPDATE user_xiuxian SET "maxR" = "maxR" + %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def subtract_max_root(self, user_id, points):
        """轮回点减少灵根上限"""
        sql = 'UPDATE user_xiuxian SET "maxR" = "maxR" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def add_max_hp(self, user_id, points):
        """轮回点增加气血上限"""
        sql = 'UPDATE user_xiuxian SET "maxH" = "maxH" + %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def subtract_max_hp(self, user_id, points):
        """轮回点减少气血上限"""
        sql = 'UPDATE user_xiuxian SET "maxH" = "maxH" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def add_max_mp(self, user_id, points):
        """轮回点增加真元上限"""
        sql = 'UPDATE user_xiuxian SET "maxM" = "maxM" + %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def subtract_max_mp(self, user_id, points):
        """轮回点减少真元上限"""
        sql = 'UPDATE user_xiuxian SET "maxM" = "maxM" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def add_max_attack(self, user_id, points):
        """轮回点增加攻击上限"""
        sql = 'UPDATE user_xiuxian SET "maxA" = "maxA" + %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def subtract_max_attack(self, user_id, points):
        """轮回点减少攻击上限"""
        sql = 'UPDATE user_xiuxian SET "maxA" = "maxA" - %s WHERE user_id=%s'
        cur = self.conn.cursor()
        cur.execute(sql, (int(points), user_id))
        self.conn.commit()

    def update_user_info(self, user_id, updates):
        """
        更新用户信息
        :param user_id: 用户ID
        :param updates: 字典形式的更新字段及其值，例如 {'rbPts': 10, 'maxH': 50}
        """
        cursor = self.conn.cursor()

        set_clause = ', '.join([f'"{key}"=%s' for key in updates.keys()])
        values = list(updates.values())
        values.append(user_id)
        query = f'UPDATE user_xiuxian SET {set_clause} WHERE user_id=%s'
        try:
            cursor.execute(query, tuple(values))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cursor.close()

    def del_exp_decimal(self, user_id, exp):
        """去浮点"""
        sql = "UPDATE user_xiuxian SET exp=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (int(exp), user_id))
        self.conn.commit()

    def realm_top(self):
        """境界排行榜前50"""
        rank_mapping = {rank: idx for idx, rank in enumerate(Items().convert_rank('江湖好手')[1])}

        sql = """SELECT user_name, level, exp FROM user_xiuxian 
                 WHERE user_name IS NOT NULL
                 ORDER BY exp DESC, (CASE level """

        for level, value in sorted(rank_mapping.items(), key=lambda x: x[1], reverse=True):
            sql += f"WHEN '{level}' THEN '{value:02}' "

        # 设置默认值为 '99'
        sql += """ELSE '99' END::text) ASC LIMIT 50"""

        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def stone_top(self):
        """这也是灵石排行榜"""
        sql = """SELECT user_name, stone FROM user_xiuxian 
                 WHERE user_name IS NOT NULL 
                 ORDER BY stone DESC LIMIT 50"""
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def power_top(self):
        """战力排行榜"""
        sql = """SELECT user_name, power FROM user_xiuxian 
                 WHERE user_name IS NOT NULL 
                 ORDER BY power DESC LIMIT 50"""
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def poxian_top(self):
        """破限排行榜/轮回排行榜"""
        sql = """SELECT user_name, poxian_num FROM user_xiuxian 
                 WHERE user_name IS NOT NULL 
                 ORDER BY poxian_num DESC LIMIT 50"""
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def scale_top(self):
        """宗门建设度排行榜"""
        sql = """SELECT sect_id, sect_name, sect_scale FROM sects 
                 WHERE sect_owner IS NOT NULL 
                 ORDER BY sect_scale DESC"""
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def get_all_sects(self):
        """
        获取所有宗门信息
        :return: 宗门信息字典列表
        """
        sql = """SELECT * FROM sects 
                 WHERE sect_owner IS NOT NULL"""
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        results = []
        columns = [column[0] for column in cur.description]
        for row in result:
            sect_dict = dict(zip(columns, row))
            results.append(sect_dict)
        return results

    def get_all_sects_with_member_count(self):
        """
        获取所有宗门及其各个宗门成员数
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.sect_id, s.sect_name, s.sect_scale, 
                   (SELECT user_name FROM user_xiuxian WHERE user_id = s.sect_owner) AS user_name, 
                   COUNT(ux.user_id) AS member_count
            FROM sects s
            LEFT JOIN user_xiuxian ux ON s.sect_id = ux.sect_id
            GROUP BY s.sect_id
        """)
        results = cur.fetchall()
        return results

    def update_user_is_beg(self, user_id, is_beg):
        """
        更新用户的最后奇缘时间

        :param user_id: 用户ID
        :param is_beg: 'YYYY-MM-DD HH:MM:SS'
        """
        cur = self.conn.cursor()
        sql = "UPDATE user_xiuxian SET is_beg=%s WHERE user_id=%s"
        cur.execute(sql, (is_beg, user_id))
        self.conn.commit()

    def get_top1_user(self):
        """
        获取修为第一的用户
        """
        cur = self.conn.cursor()
        sql = "SELECT * FROM user_xiuxian ORDER BY exp DESC LIMIT 1"
        cur.execute(sql)
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            top1_dict = dict(zip(columns, result))
            return top1_dict
        else:
            return None

    def donate_update(self, sect_id, stone_num):
        """宗门捐献更新建设度及可用灵石"""
        sql = "UPDATE sects SET sect_used_stone=sect_used_stone+%s, sect_scale=sect_scale+%s WHERE sect_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (stone_num, stone_num * 1, sect_id))
        self.conn.commit()

    def update_sect_used_stone(self, sect_id, sect_used_stone, key):
        """更新宗门灵石储备  1为增加,2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = "UPDATE sects SET sect_used_stone=sect_used_stone+%s WHERE sect_id=%s"
            cur.execute(sql, (sect_used_stone, sect_id))
            self.conn.commit()
        elif key == 2:
            sql = "UPDATE sects SET sect_used_stone=sect_used_stone-%s WHERE sect_id=%s"
            cur.execute(sql, (sect_used_stone, sect_id))
            self.conn.commit()

    def update_sect_materials(self, sect_id, sect_materials, key):
        """更新资材  1为增加,2为减少"""
        cur = self.conn.cursor()
        if key == 1:
            # 解析 sect_materials 为数值类型
            parsed_sect_materials = self.parse_sect_materials(sect_id)
            # 计算新的 sect_materials 值
            new_sect_materials = parsed_sect_materials + sect_materials
            # 更新数据库
            sql = "UPDATE sects SET sect_materials=%s WHERE sect_id=%s"
            cur.execute(sql, (new_sect_materials, sect_id))
            self.conn.commit()
        elif key == 2:
            # 解析 sect_materials 为数值类型
            parsed_sect_materials = self.parse_sect_materials(sect_id)
            # 计算新的 sect_materials 值
            new_sect_materials = parsed_sect_materials - sect_materials
            # 更新数据库
            sql = "UPDATE sects SET sect_materials=%s WHERE sect_id=%s"
            cur.execute(sql, (new_sect_materials, sect_id))
            self.conn.commit()

    def parse_sect_materials(self, sect_id):
        """解析 sect_materials 为数值类型"""
        cur = self.conn.cursor()
        select_sql = "SELECT sect_materials FROM sects WHERE sect_id=%s"
        cur.execute(select_sql, (sect_id,))
        result = cur.fetchone()
        if result:
            sect_materials = result[0]
            try:
                parsed_sect_materials = int(sect_materials)
                return parsed_sect_materials
            except ValueError:
                # 处理无法解析的情况
                raise ValueError("无法解析 sect_materials 为数值类型")

    def get_all_sects_id_scale(self):
        """
        获取所有宗门信息
        :return
        :result[0] = sect_id   
        :result[1] = 建设度 sect_scale,
        :result[2] = 丹房等级 elixir_room_level 
        """
        sql = "SELECT sect_id, sect_scale, elixir_room_level FROM sects WHERE sect_owner IS NOT NULL ORDER BY sect_scale DESC"
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        return result

    def get_all_users_by_sect_id(self, sect_id):
        """
        获取宗门所有成员信息
        :return: 成员列表
        """
        sql = "SELECT * FROM user_xiuxian WHERE sect_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_id,))
        result = cur.fetchall()
        results = []
        for user in result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, user))
            results.append(user_dict)
        return results

    def do_work(self, user_id, the_type, sc_time=None):
        """
        更新用户操作CD
        :param sc_time: 任务
        :param user_id: qq
        :param the_type: 0:无状态  1:闭关中  2:历练中  3:探索秘境中
        :param the_time: 本次操作的时长
        :return:
        """
        now_time = None
        if the_type == 1 or the_type == 2 or the_type == 3:
            now_time = datetime.now()
        elif the_type == 0:
            now_time = None

        sql = "UPDATE user_cd SET type=%s, create_time=%s, scheduled_time=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (the_type, now_time, sc_time, user_id))
        self.conn.commit()

    def update_levelrate(self, user_id, rate):
        """更新突破成功率"""
        sql = "UPDATE user_xiuxian SET level_up_rate=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (rate, user_id))
        self.conn.commit()

    def update_user_attribute(self, user_id, hp, mp, atk):
        """更新用户HP,MP,ATK信息"""
        sql = "UPDATE user_xiuxian SET hp=%s, mp=%s, atk=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (hp, mp, atk, user_id))
        self.conn.commit()

    def update_user_hp_mp(self, user_id, hp, mp):
        """更新用户HP,MP信息"""
        sql = "UPDATE user_xiuxian SET hp=%s, mp=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (hp, mp, user_id))
        self.conn.commit()

    def update_user_sect_contribution(self, user_id, sect_contribution):
        """更新用户宗门贡献度"""
        sql = "UPDATE user_xiuxian SET sect_contribution=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_contribution, user_id))
        self.conn.commit()

    def update_user_hp(self, user_id):
        """重置用户hp,mp信息"""
        sql = "UPDATE user_xiuxian SET hp=exp/2, mp=exp, atk=exp/10 WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def restate(self, user_id=None):
        """重置所有用户状态或重置对应人状态"""
        if user_id is None:
            sql = "UPDATE user_xiuxian SET hp=exp/2, mp=exp, atk=exp/10"
            cur = self.conn.cursor()
            cur.execute(sql)
            self.conn.commit()
        else:
            sql = "UPDATE user_xiuxian SET hp=exp/2, mp=exp, atk=exp/10 WHERE user_id=%s"
            cur = self.conn.cursor()
            cur.execute(sql, (user_id,))
            self.conn.commit()

    def auto_recover_hp(self):
        """自动回血函数"""
        sql = "SELECT user_id, exp, hp FROM user_xiuxian WHERE hp < exp/2"
        cur = self.conn.cursor()
        cur.execute(sql)
        users = cur.fetchall()

        for user in users:
            user_id, exp, hp = user
            sql = "UPDATE user_xiuxian SET hp=hp + %s * 0.001 WHERE user_id=%s"
            cur.execute(sql, (exp, user_id))

        self.conn.commit()

    def get_back_msg(self, user_id):
        """获取用户背包信息"""
        sql = "SELECT * FROM back WHERE user_id=%s AND goods_num >= 1"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchall()
        if not result:
            return None

        columns = [column[0] for column in cur.description]
        results = []
        for row in result:
            back_dict = dict(zip(columns, row))
            results.append(back_dict)
        return results

    def goods_num(self, user_id, goods_id):
        """
        判断用户物品数量
        :param user_id: 用户qq
        :param goods_id: 物品id
        :return: 物品数量
        """
        sql = "SELECT num FROM back WHERE user_id=%s AND goods_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, goods_id))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            return 0

    def get_all_user_exp(self, level):
        """查询所有对应大境界玩家的修为"""
        sql = "SELECT exp FROM user_xiuxian WHERE level LIKE %s"
        cur = self.conn.cursor()
        cur.execute(sql, (f"{level}%",))
        result = cur.fetchall()
        return result

    def update_user_atkpractice(self, user_id, atkpractice):
        """更新用户攻击修炼等级"""
        sql = "UPDATE user_xiuxian SET atkpractice=%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (atkpractice, user_id))
        self.conn.commit()

    def update_user_sect_task(self, user_id, sect_task):
        """更新用户宗门任务次数"""
        sql = "UPDATE user_xiuxian SET sect_task=sect_task+%s WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_task, user_id))
        self.conn.commit()

    def sect_task_reset(self):
        """重置宗门任务次数"""
        sql = "UPDATE user_xiuxian SET sect_task=0"
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def update_sect_scale_and_used_stone(self, sect_id, sect_used_stone, sect_scale):
        """更新宗门灵石、建设度"""
        sql = "UPDATE sects SET sect_used_stone=%s, sect_scale=%s WHERE sect_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_used_stone, sect_scale, sect_id))
        self.conn.commit()

    def update_sect_elixir_room_level(self, sect_id, level):
        """更新宗门丹房等级"""
        sql = "UPDATE sects SET elixir_room_level=%s WHERE sect_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (level, sect_id))
        self.conn.commit()

    def update_user_sect_elixir_get_num(self, user_id):
        """更新用户每日领取丹药领取次数"""
        sql = "UPDATE user_xiuxian SET sect_elixir_get=1 WHERE user_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def sect_elixir_get_num_reset(self):
        """重置宗门丹药领取次数"""
        sql = "UPDATE user_xiuxian SET sect_elixir_get=0"
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def update_sect_mainbuff(self, sect_id, mainbuffid):
        """更新宗门当前的主修功法"""
        sql = "UPDATE sects SET mainbuff=%s WHERE sect_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (mainbuffid, sect_id))
        self.conn.commit()

    def update_sect_secbuff(self, sect_id, secbuffid):
        """更新宗门当前的神通"""
        sql = "UPDATE sects SET secbuff=%s WHERE sect_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (secbuffid, sect_id))
        self.conn.commit()

    def initialize_user_buff_info(self, user_id):
        """初始化用户buff信息"""
        upsert_sql = """
            INSERT INTO buffinfo (user_id, main_buff, sec_buff, faqi_buff, fabao_weapon)
            VALUES (%s, 0, 0, 0, 0)
            ON CONFLICT (user_id) DO UPDATE SET
            main_buff = EXCLUDED.main_buff,
            sec_buff = EXCLUDED.sec_buff,
            faqi_buff = EXCLUDED.faqi_buff,
            fabao_weapon = EXCLUDED.fabao_weapon
        """

        with self.conn.cursor() as cur:
            cur.execute(upsert_sql, (user_id,))

        # 提交事务
        self.conn.commit()

    def get_user_buff_info(self, user_id):
        """获取用户buff信息"""
        sql = "SELECT * FROM buffinfo WHERE user_id = %s"
        cur = self.conn.cursor()

        try:
            cur.execute(sql, (user_id,))
            result = cur.fetchone()
            if result:
                columns = [column[0] for column in cur.description]
                buff_dict = dict(zip(columns, result))
                return buff_dict
            else:
                return None
        except psycopg2.errors.UndefinedTable as e:
            print(f"UndefinedTable error: {e}")
            self.create_buff_info_table()
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            cur.close()

    def updata_user_main_buff(self, user_id, id):
        """更新用户主功法信息"""
        sql = "UPDATE buffinfo SET main_buff = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_sub_buff(self, user_id, id):
        """更新用户辅修功法信息"""
        sql = "UPDATE buffinfo SET sub_buff = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_sec_buff(self, user_id, id):
        """更新用户副功法信息"""
        sql = "UPDATE buffinfo SET sec_buff = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_faqi_buff(self, user_id, id):
        """更新用户法器信息"""
        sql = "UPDATE buffinfo SET faqi_buff = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_fabao_weapon(self, user_id, id):
        """更新用户法宝信息"""
        sql = "UPDATE buffinfo SET fabao_weapon = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_armor_buff(self, user_id, id):
        """更新用户防具信息"""
        sql = "UPDATE buffinfo SET armor_buff = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_atk_buff(self, user_id, buff):
        """更新用户永久攻击buff信息"""
        sql = "UPDATE buffinfo SET atk_buff = atk_buff + %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (buff, user_id,))
        self.conn.commit()

    def updata_user_blessed_spot(self, user_id, blessed_spot):
        """更新用户洞天福地等级"""
        sql = "UPDATE buffinfo SET blessed_spot = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (blessed_spot, user_id,))
        self.conn.commit()

    def update_user_blessed_spot_flag(self, user_id):
        """更新用户洞天福地是否开启"""
        sql = "UPDATE user_xiuxian SET blessed_spot_flag = 1 WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_blessed_spot_name(self, user_id, blessed_spot_name):
        """更新用户洞天福地的名字"""
        sql = "UPDATE user_xiuxian SET blessed_spot_name = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (blessed_spot_name, user_id,))
        self.conn.commit()

    def day_num_reset(self):
        """重置丹药每日使用次数"""
        sql = "UPDATE back SET day_num = 0 WHERE goods_type = '丹药'"
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def reset_work_num(self):
        """重置用户悬赏令刷新次数"""
        sql = "UPDATE user_xiuxian SET work_num = 0"
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def get_work_num(self, user_id):
        """获取用户悬赏令刷新次数"""
        sql = "SELECT work_num FROM user_xiuxian WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            work_num = result[0]
        return work_num

    def update_work_num(self, user_id, work_num):
        """更新用户悬赏令刷新次数"""
        sql = "UPDATE user_xiuxian SET work_num = %s WHERE user_id = %s"
        cur = self.conn.cursor()
        cur.execute(sql, (work_num, user_id,))
        self.conn.commit()

    def send_back(self, user_id, goods_id, goods_name, goods_type, goods_num, bind_flag=0):
        """
        插入物品至背包
        :param user_id: 用户qq
        :param goods_id: 物品id
        :param goods_name: 物品名称
        :param goods_type: 物品类型
        :param goods_num: 物品数量
        :param bind_flag: 是否绑定物品,0-非绑定,1-绑定
        :return: None
        """
        now_time = datetime.now().isoformat()

        # 检查物品是否存在，存在则update
        cur = self.conn.cursor()
        back = self.get_item_by_good_id_and_user_id(user_id, goods_id)
        if back:
            # 判断是否存在，存在则update
            if bind_flag == 1:
                bind_num = back['bind_num'] + goods_num
            else:
                bind_num = back['bind_num']
            goods_nums = back['goods_num'] + goods_num
            sql = "UPDATE back SET goods_num=%s, update_time=%s, bind_num=%s WHERE user_id=%s AND goods_id=%s"
            cur.execute(sql, (goods_nums, now_time, bind_num, user_id, goods_id))
            self.conn.commit()
        else:
            # 判断是否存在，不存在则INSERT
            if bind_flag == 1:
                bind_num = goods_num
            else:
                bind_num = 0
            sql = """
                INSERT INTO back (user_id, goods_id, goods_name, goods_type, goods_num, create_time, update_time, bind_num)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (user_id, goods_id, goods_name, goods_type, goods_num, now_time, now_time, bind_num))
            self.conn.commit()

    def get_item_by_good_id_and_user_id(self, user_id, goods_id):
        """根据物品id、用户id获取物品信息"""
        sql = "SELECT * FROM back WHERE user_id=%s AND goods_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, goods_id))
        result = cur.fetchone()
        if not result:
            return None

        columns = [column[0] for column in cur.description]
        item_dict = dict(zip(columns, result))
        return item_dict

    def update_back_equipment(self, sql_str):
        """更新背包,传入sql"""
        logger.opt(colors=True).info(f"<green>执行的sql:{sql_str}</green>")
        cur = self.conn.cursor()
        cur.execute(sql_str)
        self.conn.commit()

    def update_back_j(self, user_id, goods_id, num=1, use_key=0):
        """
        使用物品
        :param num: 减少数量，默认1
        :param use_key: 是否使用，丹药使用才传，默认0
        """
        back = self.get_item_by_good_id_and_user_id(user_id, goods_id)
        if back['goods_type'] == "丹药" and use_key == 1:  # 丹药要判断耐药性、日使用上限
            if back['bind_num'] >= num:
                bind_num = back['bind_num'] - num  # 优先使用绑定物品
            else:
                bind_num = back['bind_num']
            day_num = back['day_num'] + num
            all_num = back['all_num'] + num
        else:
            bind_num = back['bind_num']
            day_num = back['day_num']
            all_num = back['all_num']
        goods_num = back['goods_num'] - num
        now_time = datetime.now().isoformat()
        sql_str = "UPDATE back SET update_time=%s, action_time=%s, goods_num=%s, day_num=%s, all_num=%s, bind_num=%s WHERE user_id=%s AND goods_id=%s"
        cur = self.conn.cursor()
        cur.execute(sql_str, (now_time, now_time, goods_num, day_num, all_num, bind_num, user_id, goods_id))
        self.conn.commit()

    def enable_xiuxian(self, group_id):
        """启用群聊的修仙功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_xiuxian) VALUES (%s, TRUE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_xiuxian = TRUE",
                (group_id,)
            )
            self.conn.commit()

    def disable_xiuxian(self, group_id):
        """禁用群聊的修仙功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_xiuxian) VALUES (%s, FALSE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_xiuxian = FALSE",
                (group_id,)
            )
            self.conn.commit()

    def is_xiuxian_enabled(self, group_id):
        """检查群聊是否开启了修仙功能"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT enabled_xiuxian FROM xiuxian_group_config WHERE group_id = %s", (group_id,))
            result = cur.fetchone()
            return result[0] if result else False

    def get_enabled_groups(self):
        """获取所有开启了修仙功能的群聊列表"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT group_id FROM xiuxian_group_config WHERE enabled_xiuxian = TRUE")
            results = cur.fetchall()
            return [row[0] for row in results]

    def enable_auction(self, group_id):
        """启用群聊的拍卖会功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_paimai) VALUES (%s, TRUE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_paimai = TRUE",
                (group_id,)
            )
            self.conn.commit()

    def disable_auction(self, group_id):
        """禁用群聊的拍卖会功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_paimai) VALUES (%s, FALSE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_paimai = FALSE",
                (group_id,)
            )
            self.conn.commit()

    def is_auction_enabled(self, group_id):
        """检查群聊是否开启了拍卖会功能"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT enabled_paimai FROM xiuxian_group_config WHERE group_id = %s", (group_id,))
            result = cur.fetchone()
            return result[0] if result else False

    def get_enabled_auction_groups(self):
        """获取所有开启了拍卖会功能的群聊列表"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT group_id FROM xiuxian_group_config WHERE enabled_paimai = TRUE")
            results = cur.fetchall()
            return [row[0] for row in results]

    def enable_boss(self, group_id):
        """启用群聊的世界 Boss 功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_boss) VALUES (%s, TRUE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_boss = TRUE",
                (group_id,)
            )
            self.conn.commit()

    def disable_boss(self, group_id):
        """禁用群聊的世界 Boss 功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_boss) VALUES (%s, FALSE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_boss = FALSE",
                (group_id,)
            )
            self.conn.commit()

    def is_boss_enabled(self, group_id):
        """检查群聊是否开启了世界 Boss 功能"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT enabled_boss FROM xiuxian_group_config WHERE group_id = %s", (group_id,))
            result = cur.fetchone()
            return result[0] if result else False

    def get_enabled_boss_groups(self):
        """获取所有开启了世界 Boss 功能的群聊列表"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT group_id FROM xiuxian_group_config WHERE enabled_boss = TRUE")
            results = cur.fetchall()
            return [row[0] for row in results]

    def enable_mijing(self, group_id):
        """启用群聊的秘境功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_mijing) VALUES (%s, TRUE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_mijing = TRUE",
                (group_id,)
            )
            self.conn.commit()

    def disable_mijing(self, group_id):
        """禁用群聊的秘境功能"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO xiuxian_group_config (group_id, enabled_mijing) VALUES (%s, FALSE) "
                "ON CONFLICT (group_id) DO UPDATE SET enabled_mijing = FALSE",
                (group_id,)
            )
            self.conn.commit()

    def is_mijing_enabled(self, group_id):
        """检查群聊是否开启了秘境功能"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT enabled_mijing FROM xiuxian_group_config WHERE group_id = %s", (group_id,))
            result = cur.fetchone()
            return result[0] if result else False

    def get_enabled_mijing_groups(self):
        """获取所有开启了秘境功能的群聊列表"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT group_id FROM xiuxian_group_config WHERE enabled_mijing = TRUE")
            results = cur.fetchall()
            return [row[0] for row in results]

    def insert_mijing_info(self, name, rank, current_count, l_user_id, time):
        """
        插入新的秘境信息。

        参数:
        - name: 秘境名称
        - rank: 秘境等级
        - current_count: 当前可探索次数
        - l_user_id: 已经参加的用户ID列表，以逗号分隔
        - time: 探索所需的时间（单位：分钟）
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO xiuxian_mijing_info (config_id, name, rank, current_count, l_user_id, time)
                VALUES ((SELECT id FROM xiuxian_mijing_config WHERE name = %s AND rank = %s),
                        %s, %s, %s, %s, %s);
            """, (name, rank, name, rank, current_count, l_user_id, time))
            self.conn.commit()


    def update_dingshi_mijing_info(self, name, xin_name, rank, current_count, l_user_id, time):
        """
        更新秘境信息。

        参数:
        - name: 秘境名称
        - rank: 秘境等级
        - current_count: 当前可探索次数
        - l_user_id: 已经参加的用户ID列表，以逗号分隔
        - time: 探索所需的时间（单位：分钟）
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE xiuxian_mijing_info
                SET current_count = %s, l_user_id = %s, time = %s, rank = %s, name = %s
                WHERE name = %s;
            """, (current_count, l_user_id, time, rank, xin_name, name))
            self.conn.commit()

    def update_mijing_info(self, name, rank, current_count, l_user_id, time):
        """
        更新秘境信息。

        参数:
        - name: 秘境名称
        - rank: 秘境等级
        - current_count: 当前可探索次数
        - l_user_id: 已经参加的用户ID列表，以逗号分隔
        - time: 探索所需的时间（单位：分钟）
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE xiuxian_mijing_info
                SET current_count = %s, l_user_id = %s, time = %s, rank = %s
                WHERE name = %s;
            """, (current_count, l_user_id, time, rank, name))
            self.conn.commit()

    def get_mijing_info(self):
        """
        获取最新的秘境信息。

        返回:
        - 如果找到对应的记录，则返回该记录；否则返回None。
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:  # 使用 DictCursor
            cur.execute("""
                SELECT * FROM xiuxian_mijing_info 
                ORDER BY created_at DESC
                LIMIT 1;
            """)
            row = cur.fetchone()
            return row  # 直接返回查询结果

    def get_random_config_id(self):
        """
        根据配置表中的 type_rate 字段随机选择一个配置 ID。
        返回:
        - 一个配置 ID。
        """
        rate_dict = {}

        # 获取所有配置的 type_rate 并构建字典
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id, name, type_rate FROM xiuxian_mijing_config;")
            configs = cur.fetchall()

            for config in configs:
                rate_dict[config['name']] = config['type_rate']

        # 使用 calculated 方法进行加权随机选择
        selected_name = OtherSet().calculated(rate_dict)

        # 根据选定的名字获取配置 ID
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id FROM xiuxian_mijing_config WHERE name = %s;", (selected_name,))
            result = cur.fetchone()
            if result:
                return result['id']
            else:
                raise Exception(f"找不到id的配置 {selected_name}")

    def get_config_by_id(self, config_id):
        """
        根据配置 ID 获取配置信息。
        参数:
        - config_id: 配置 ID
        返回:
        - 如果找到对应的记录，则返回该记录；否则返回None。
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:  # 使用 DictCursor
            cur.execute("""
                SELECT * FROM xiuxian_mijing_config
                WHERE id = %s;
            """, (config_id,))
            row = cur.fetchone()
            return row  # 直接返回查询结果



class XiuxianJsonDate:
    def __init__(self):
        self.root_jsonpath = DATABASE / "灵根.json"
        self.level_jsonpath = DATABASE / "突破概率.json"

    def beifen_linggen_get(self):
        with open(self.root_jsonpath, 'r', encoding='utf-8') as e:
            a = e.read()
            data = json.loads(a)
            lg = random.choice(data)
            return lg['name'], lg['type']

    def level_rate(self, level):
        with open(self.level_jsonpath, 'r', encoding='utf-8') as e:
            a = e.read()
            data = json.loads(a)
            return data[0][level]

    def linggen_get(self):
        """获取灵根信息"""
        data = jsondata.root_data()
        rate_dict = {}
        for i, v in data.items():
            rate_dict[i] = v["type_rate"]
        lgen = OtherSet().calculated(rate_dict)
        if data[lgen]["type_flag"]:
            flag = random.choice(data[lgen]["type_flag"])
            root = random.sample(data[lgen]["type_list"], flag)
            msg = ""
            for j in root:
                if j == root[-1]:
                    msg += j
                    break
                msg += (j + "、")

            return msg + '属性灵根', lgen
        else:
            root = random.choice(data[lgen]["type_list"])
            return root, lgen


class OtherSet(XiuConfig):

    def __init__(self):
        super().__init__()

    def set_closing_type(self, user_level):
        list_all = len(self.level) - 1
        now_index = self.level.index(user_level)
        if list_all == now_index:
            need_exp = 0.001
        else:
            is_updata_level = self.level[now_index + 1]
            need_exp = XiuxianDateManage().get_level_power(is_updata_level)
        return need_exp

    def get_type(self, user_exp, rate, user_level):
        list_all = len(self.level) - 1
        now_index = self.level.index(user_level)
        if list_all == now_index:
            return "道友已是最高境界，无法突破！"

        is_updata_level = self.level[now_index + 1]
        need_exp = XiuxianDateManage().get_level_power(is_updata_level)

        # 判断修为是否足够突破
        if user_exp >= need_exp:
            pass
        else:
            return f"道友的修为不足以突破！距离下次突破需要{need_exp - user_exp}修为！突破境界为：{is_updata_level}"

        success_rate = True if random.randint(0, 100) < rate else False

        if success_rate:
            return [self.level[now_index + 1]]
        else:
            return '失败'

    def calculated(self, rate: dict) -> str:
        """
        根据概率计算，轮盘型
        :rate:格式{"数据名":"获取几率"}
        :return: 数据名
        """

        get_list = []  # 概率区间存放

        n = 1
        for name, value in rate.items():  # 生成数据区间
            value_rate = int(value)
            list_rate = [_i for _i in range(n, value_rate + n)]
            get_list.append(list_rate)
            n += value_rate

        now_n = n - 1
        get_random = random.randint(1, now_n)  # 抽取随机数

        index_num = None
        for list_r in get_list:
            if get_random in list_r:  # 判断随机在那个区间
                index_num = get_list.index(list_r)
                break

        return list(rate.keys())[index_num]

    def date_diff(self, new_time, old_time):
        """计算日期差"""
        if isinstance(new_time, datetime):
            pass
        else:
            new_time = datetime.strptime(new_time, '%Y-%m-%d %H:%M:%S.%f')

        if isinstance(old_time, datetime):
            pass
        else:
            old_time = datetime.strptime(old_time, '%Y-%m-%d %H:%M:%S.%f')

        day = (new_time - old_time).days
        sec = (new_time - old_time).seconds

        return (day * 24 * 60 * 60) + sec

    def get_power_rate(self, mind, other):
        power_rate = mind / (other + mind)
        if power_rate >= 0.8:
            return "道友偷窃小辈实属天道所不齿！"
        elif power_rate <= 0.05:
            return "道友请不要不自量力！"
        else:
            return int(power_rate * 100)

    def player_fight(self, player1: dict, player2: dict):
        """
        回合制战斗
        type_in : 1 为完整返回战斗过程（未加）
        2：只返回战斗结果
        数据示例：
        {"道号": None, "气血": None, "攻击": None, "真元": None, '会心':None}
        """
        msg1 = "{}发起攻击，造成了{}伤害\n"
        msg2 = "{}发起攻击，造成了{}伤害\n"

        play_list = []
        suc = None
        if player1['气血'] <= 0:
            player1['气血'] = 1
        if player2['气血'] <= 0:
            player2['气血'] = 1
        while True:
            player1_gj = int(round(random.uniform(0.95, 1.05), 2) * player1['攻击'])
            if random.randint(0, 100) <= player1['会心']:
                player1_gj = int(player1_gj * player1['爆伤'])
                msg1 = "{}发起会心一击，造成了{}伤害\n"

            player2_gj = int(round(random.uniform(0.95, 1.05), 2) * player2['攻击'])
            if random.randint(0, 100) <= player2['会心']:
                player2_gj = int(player2_gj * player2['爆伤'])
                msg2 = "{}发起会心一击，造成了{}伤害\n"

            play1_sh: int = int(player1_gj * (1 - player2['防御']))
            play2_sh: int = int(player2_gj * (1 - player1['防御']))

            play_list.append(msg1.format(player1['道号'], play1_sh))
            player2['气血'] = player2['气血'] - play1_sh
            play_list.append(f"{player2['道号']}剩余血量{player2['气血']}")
            XiuxianDateManage().update_user_hp_mp(player2['user_id'], player2['气血'], player2['真元'])

            if player2['气血'] <= 0:
                play_list.append(f"{player1['道号']}胜利")
                suc = f"{player1['道号']}"
                XiuxianDateManage().update_user_hp_mp(player2['user_id'], 1, player2['真元'])
                break

            play_list.append(msg2.format(player2['道号'], play2_sh))
            player1['气血'] = player1['气血'] - play2_sh
            play_list.append(f"{player1['道号']}剩余血量{player1['气血']}\n")
            XiuxianDateManage().update_user_hp_mp(player1['user_id'], player1['气血'], player1['真元'])

            if player1['气血'] <= 0:
                play_list.append(f"{player2['道号']}胜利")
                suc = f"{player2['道号']}"
                XiuxianDateManage().update_user_hp_mp(player1['user_id'], 1, player1['真元'])
                break
            if player1['气血'] <= 0 or player2['气血'] <= 0:
                play_list.append("逻辑错误！！！")
                break

        return play_list, suc

    def send_hp_mp(self, user_id, hp, mp):
        user_msg = XiuxianDateManage().get_user_info_with_id(user_id)
        max_hp = int(user_msg['exp'] / 2)
        max_mp = int(user_msg['exp'])

        msg = []
        hp_mp = []

        if user_msg['hp'] < max_hp:
            if user_msg['hp'] + hp < max_hp:
                new_hp = user_msg['hp'] + hp
                msg.append(f',回复气血：{hp}')
            else:
                new_hp = max_hp
                msg.append(',气血已回满！')
        else:
            new_hp = user_msg['hp']
            msg.append('')

        if user_msg['mp'] < max_mp:
            if user_msg['mp'] + mp < max_mp:
                new_mp = user_msg['mp'] + mp
                msg.append(f',回复真元：{mp}')
            else:
                new_mp = max_mp
                msg.append(',真元已回满！')
        else:
            new_mp = user_msg['mp']
            msg.append('')

        hp_mp.append(new_hp)
        hp_mp.append(new_mp)
        hp_mp.append(user_msg['exp'])

        return msg, hp_mp


sql_message = XiuxianDateManage()  # sql类
items = Items()


def final_user_data(user_data, columns):
    """传入用户当前信息、buff信息,返回最终信息"""
    user_dict = dict(zip((col[0] for col in columns), user_data))

    # 通过字段名称获取相应的值
    impart_data = xiuxian_impart.get_user_info_with_id(user_dict['user_id'])
    if impart_data:
        pass
    else:
        xiuxian_impart._create_user(user_dict['user_id'])
    impart_data = xiuxian_impart.get_user_info_with_id(user_dict['user_id'])
    impart_hp_per = impart_data['impart_hp_per'] if impart_data is not None else 0
    impart_mp_per = impart_data['impart_mp_per'] if impart_data is not None else 0
    impart_atk_per = impart_data['impart_atk_per'] if impart_data is not None else 0

    user_buff_data = UserBuffDate(user_dict['user_id']).buffinfo

    armor_atk_buff = 0
    if int(user_buff_data['armor_buff']) != 0:
        armor_info = items.get_data_by_item_id(user_buff_data['armor_buff'])
        armor_atk_buff = armor_info['atk_buff']

    weapon_atk_buff = 0
    if int(user_buff_data['faqi_buff']) != 0:
        weapon_info = items.get_data_by_item_id(user_buff_data['faqi_buff'])
        weapon_atk_buff = weapon_info['atk_buff']

    main_buff_data = UserBuffDate(user_dict['user_id']).get_user_main_buff_data()
    main_hp_buff = main_buff_data['hpbuff'] if main_buff_data is not None else 0
    main_mp_buff = main_buff_data['mpbuff'] if main_buff_data is not None else 0
    main_atk_buff = main_buff_data['atkbuff'] if main_buff_data is not None else 0

    main_atk_buff = Decimal(str(main_atk_buff))
    weapon_atk_buff = Decimal(str(weapon_atk_buff))
    armor_atk_buff = Decimal(str(armor_atk_buff))
    impart_atk_per = Decimal(str(impart_atk_per))

    user_dict['atk'] = int((user_dict['atk'] * (user_dict['atkpractice'] * Decimal('0.04') + 1) * (1 + main_atk_buff) *
                            (1 + weapon_atk_buff) * (1 + armor_atk_buff)) * (1 + impart_atk_per)) + int(
        user_buff_data['atk_buff'])

    return user_dict


@DRIVER.on_shutdown
async def close_db():
    XiuxianDateManage().close()


class XIUXIAN_IMPART_BUFF:
    _instance = {}
    _has_init = {}

    def __new__(cls):
        if 'impart_num' not in cls._instance:
            cls._instance['impart_num'] = super(XIUXIAN_IMPART_BUFF, cls).__new__(cls)
        return cls._instance['impart_num']

    def __init__(self):
        if not self._has_init.get('impart_num'):
            self._has_init['impart_num'] = True
            self.database_path = DATABASE_IMPARTBUFF
            self.conn = self._connect_to_db()
            logger.opt(colors=True).info("<green>xiuxian_impart数据库已连接!</green>")
            self._check_data()

    def _connect_to_db(self):
        """连接到PostgreSQL数据库"""
        conn = psycopg2.connect(
            dbname="baibaidb",
            user="postgres",
            password="robots666",
            host="localhost",
            port=5432
        )
        conn.autocommit = True  # 设置为自动提交，以简化事务管理
        return conn

    def close(self):
        if self.conn:
            self.conn.close()
            logger.opt(colors=True).info("<green>xiuxian_impart数据库关闭!</green>")

    def _create_table(self) -> None:
        """创建数据库表"""
        c = self.conn.cursor()
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS xiuxian_impart (
                    id SERIAL PRIMARY KEY,
                    user_id NUMERIC DEFAULT 0,
                    impart_hp_per NUMERIC DEFAULT 0,
                    impart_atk_per NUMERIC DEFAULT 0,
                    impart_mp_per NUMERIC DEFAULT 0,
                    impart_exp_up NUMERIC DEFAULT 0,
                    boss_atk NUMERIC DEFAULT 0,
                    impart_know_per NUMERIC DEFAULT 0,
                    impart_burst_per NUMERIC DEFAULT 0,
                    impart_mix_per NUMERIC DEFAULT 0,
                    impart_reap_per NUMERIC DEFAULT 0,
                    impart_two_exp NUMERIC DEFAULT 0,
                    stone_num NUMERIC DEFAULT 0,
                    exp_day NUMERIC DEFAULT 0,
                    wish NUMERIC DEFAULT 0
                );
            ''')
        except Exception as e:
            logger.error(f"创建表时发生错误: {e}")
        else:
            logger.info("表创建成功")

    def _check_data(self):
        """检查数据完整性"""
        c = self.conn.cursor()

        for table in config_impart.sql_table:
            if table == "xiuxian_impart":
                try:
                    c.execute(f"SELECT COUNT(*) FROM {table}")
                except psycopg2.ProgrammingError:
                    self._create_table()

        for column in config_impart.sql_table_impart_buff:
            try:
                c.execute(f"SELECT {column} FROM xiuxian_impart")
            except psycopg2.ProgrammingError:
                sql = f"ALTER TABLE xiuxian_impart ADD COLUMN IF NOT EXISTS {column} NUMERICNUMERIC DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                logger.opt(colors=True).info("<green>xiuxian_impart数据库核对成功!</green>")
                c.execute(sql)

    @classmethod
    def close_dbs(cls):
        if 'impart_num' in cls._instance:
            instance = cls._instance['impart_num']
            instance.close()
            del cls._instance['impart_num']

    def create_user(self, user_id):
        """校验用户是否存在"""
        cur = self.conn.cursor()
        sql = "SELECT * FROM xiuxian_impart WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if not result:
            return False
        else:
            return True

    def _create_user(self, user_id: str) -> None:
        """在数据库中创建用户并初始化"""
        # 检查用户是否已经存在
        c = self.conn.cursor()
        check_sql = sql.SQL("""
            SELECT EXISTS (
                SELECT 1 
                FROM xiuxian_impart 
                WHERE user_id = %s
            )
        """)

        c.execute(check_sql, (user_id,))
        exists = c.fetchone()[0]

        if not exists:
            # 如果用户不存在，则插入新记录
            insert_sql = sql.SQL("""
                INSERT INTO xiuxian_impart 
                (user_id, impart_hp_per, impart_atk_per, impart_mp_per, impart_exp_up, boss_atk, impart_know_per, impart_burst_per, impart_mix_per, impart_reap_per, impart_two_exp, stone_num, exp_day, wish) 
                VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            """)

            c.execute(insert_sql, (user_id,))
            self.conn.commit()
        else:
            # 用户已存在，可以选择更新或者打印消息提示
            print(f"用户 {user_id} 已存在于数据库中，无需创建。")

    def get_user_info_with_id(self, user_id):
        """根据USER_ID获取用户impart_buff信息"""
        cur = self.conn.cursor()
        sql = "SELECT * FROM xiuxian_impart WHERE user_id = %s"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def update_impart_hp_per(self, impart_num, user_id):
        """更新impart_hp_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_hp_per = %s WHERE user_id = %s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_hp_per(self, impart_num, user_id):
        """增加impart_hp_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_hp_per = impart_hp_per + %s WHERE user_id = %s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_atk_per(self, impart_num, user_id):
        """更新impart_atk_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_atk_per = %s WHERE user_id = %s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_atk_per(self, impart_num, user_id):
        """增加impart_atk_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_atk_per = impart_atk_per + %s WHERE user_id = %s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_mp_per(self, impart_num, user_id):
        """更新impart_mp_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_mp_per = %s WHERE user_id = %s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_mp_per(self, impart_num, user_id):
        """add impart_mp_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_mp_per=impart_mp_per+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_exp_up(self, impart_num, user_id):
        """impart_exp_up"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_exp_up=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_exp_up(self, impart_num, user_id):
        """add impart_exp_up"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_exp_up=impart_exp_up+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_boss_atk(self, impart_num, user_id):
        """boss_atk"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET boss_atk=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_boss_atk(self, impart_num, user_id):
        """add boss_atk"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET boss_atk=boss_atk+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_know_per(self, impart_num, user_id):
        """impart_know_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_know_per=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_know_per(self, impart_num, user_id):
        """add impart_know_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_know_per=impart_know_per+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_burst_per(self, impart_num, user_id):
        """impart_burst_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_burst_per=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_burst_per(self, impart_num, user_id):
        """add impart_burst_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_burst_per=impart_burst_per+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_mix_per(self, impart_num, user_id):
        """impart_mix_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_mix_per=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_mix_per(self, impart_num, user_id):
        """add impart_mix_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_mix_per=impart_mix_per+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_reap_per(self, impart_num, user_id):
        """impart_reap_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_reap_per=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_reap_per(self, impart_num, user_id):
        """add impart_reap_per"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_reap_per=impart_reap_per+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_two_exp(self, impart_num, user_id):
        """更新双修"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_two_exp=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_two_exp(self, impart_num, user_id):
        """add impart_two_exp"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET impart_two_exp=impart_two_exp+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_wish(self, impart_num, user_id):
        """更新抽卡次数"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET wish=%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_wish(self, impart_num, user_id):
        """增加抽卡次数"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET wish=wish+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_stone_num(self, impart_num, user_id, type_):
        """更新结晶数量"""
        if type_ == 1:
            cur = self.conn.cursor()
            sql = "UPDATE xiuxian_impart SET stone_num=stone_num+%s WHERE user_id=%s"
            cur.execute(sql, (impart_num, user_id))
            self.conn.commit()
            return True
        if type_ == 2:
            cur = self.conn.cursor()
            sql = "UPDATE xiuxian_impart SET stone_num=stone_num-%s WHERE user_id=%s"
            cur.execute(sql, (impart_num, user_id))
            self.conn.commit()
            return True

    def update_impart_stone_all(self, impart_stone):
        """所有用户增加结晶"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET stone_num=stone_num+%s"
        cur.execute(sql, (impart_stone,))
        self.conn.commit()

    def add_impart_exp_day(self, impart_num, user_id):
        """add impart_exp_day"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET exp_day=exp_day+%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def use_impart_exp_day(self, impart_num, user_id):
        """use impart_exp_day"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET exp_day=exp_day-%s WHERE user_id=%s"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True


def leave_harm_time(user_id):
    hp_speed = 25
    user_mes = sql_message.get_user_info_with_id(user_id)
    level = user_mes['level']
    level_rate = sql_message.get_root_rate(user_mes['root_type'])  # 灵根倍率
    realm_rate = jsondata.level_data()[level]["spend"]  # 境界倍率
    main_buff_data = UserBuffDate(user_id).get_user_main_buff_data()  # 主功法数据
    main_buff_rate_buff = main_buff_data['ratebuff'] if main_buff_data else 0  # 主功法修炼倍率

    try:
        time = int(((user_mes['exp'] / 1.5) - user_mes['hp']) / ((XiuConfig().closing_exp * level_rate * realm_rate * (
                1 + main_buff_rate_buff)) * hp_speed))
    except ZeroDivisionError:
        time = "无穷大"
    except OverflowError:
        time = "溢出"
    return time


async def impart_check(user_id):
    if XIUXIAN_IMPART_BUFF().get_user_info_with_id(user_id) is None:
        XIUXIAN_IMPART_BUFF()._create_user(user_id)
        return XIUXIAN_IMPART_BUFF().get_user_info_with_id(user_id)
    else:
        return XIUXIAN_IMPART_BUFF().get_user_info_with_id(user_id)


xiuxian_impart = XIUXIAN_IMPART_BUFF()


@DRIVER.on_shutdown
async def close_db():
    XIUXIAN_IMPART_BUFF().close()


# 这里是buff部分
class BuffJsonDate:

    def __init__(self):
        """json文件路径"""
        self.mainbuff_jsonpath = SKILLPATHH / "主功法.json"
        self.secbuff_jsonpath = SKILLPATHH / "神通.json"
        self.gfpeizhi_jsonpath = SKILLPATHH / "功法概率设置.json"
        self.weapon_jsonpath = WEAPONPATH / "法器.json"
        self.armor_jsonpath = WEAPONPATH / "防具.json"

    def get_main_buff(self, id):
        return readf(self.mainbuff_jsonpath)[str(id)]

    def get_sec_buff(self, id):
        return readf(self.secbuff_jsonpath)[str(id)]

    def get_gfpeizhi(self):
        return readf(self.gfpeizhi_jsonpath)

    def get_weapon_data(self):
        return readf(self.weapon_jsonpath)

    def get_weapon_info(self, id):
        return readf(self.weapon_jsonpath)[str(id)]

    def get_armor_data(self):
        return readf(self.armor_jsonpath)

    def get_armor_info(self, id):
        return readf(self.armor_jsonpath)[str(id)]


class UserBuffDate:
    def __init__(self, user_id):
        """用户Buff数据"""
        self.user_id = user_id

    @property
    def buffinfo(self):
        """获取最新的 Buff 信息"""
        return get_user_buff(self.user_id)

    def get_user_main_buff_data(self):
        main_buff_data = None
        buff_info = self.buffinfo
        main_buff_id = buff_info.get('main_buff', 0)
        if main_buff_id != 0:
            main_buff_data = items.get_data_by_item_id(main_buff_id)
        return main_buff_data

    def get_user_sub_buff_data(self):
        sub_buff_data = None
        buff_info = self.buffinfo
        sub_buff_id = buff_info.get('sub_buff', 0)
        if sub_buff_id != 0:
            sub_buff_data = items.get_data_by_item_id(sub_buff_id)
        return sub_buff_data

    def get_user_sec_buff_data(self):
        sec_buff_data = None
        buff_info = self.buffinfo
        sec_buff_id = buff_info.get('sec_buff', 0)
        if sec_buff_id != 0:
            sec_buff_data = items.get_data_by_item_id(sec_buff_id)
        return sec_buff_data

    def get_user_weapon_data(self):
        weapon_data = None
        buff_info = self.buffinfo
        weapon_id = buff_info.get('faqi_buff', 0)
        if weapon_id != 0:
            weapon_data = items.get_data_by_item_id(weapon_id)
        return weapon_data

    def get_user_armor_buff_data(self):
        armor_buff_data = None
        buff_info = self.buffinfo
        armor_buff_id = buff_info.get('armor_buff', 0)
        if armor_buff_id != 0:
            armor_buff_data = items.get_data_by_item_id(armor_buff_id)
        return armor_buff_data


def get_weapon_info_msg(weapon_id, weapon_info=None):
    """
    获取一个法器(武器)信息msg
    :param weapon_id:法器(武器)ID
    :param weapon_info:法器(武器)信息json,可不传
    :return 法器(武器)信息msg
    """
    msg = ''
    if weapon_info is None:
        weapon_info = items.get_data_by_item_id(weapon_id)
    atk_buff_msg = f"提升{int(weapon_info['atk_buff'] * 100)}%攻击力！" if weapon_info['atk_buff'] != 0 else ''
    crit_buff_msg = f"提升{int(weapon_info['crit_buff'] * 100)}%会心率！" if weapon_info['crit_buff'] != 0 else ''
    crit_atk_msg = f"提升{int(weapon_info['critatk'] * 100)}%会心伤害！" if weapon_info['critatk'] != 0 else ''
    # def_buff_msg = f"提升{int(weapon_info['def_buff'] * 100)}%减伤率！" if weapon_info['def_buff'] != 0 else ''
    def_buff_msg = f"{'提升' if weapon_info['def_buff'] > 0 else '降低'}{int(abs(weapon_info['def_buff']) * 100)}%减伤率！" if \
        weapon_info['def_buff'] != 0 else ''
    zw_buff_msg = f"装备专属武器时提升伤害！！" if weapon_info['zw'] != 0 else ''
    mp_buff_msg = f"降低真元消耗{int(weapon_info['mp_buff'] * 100)}%！" if weapon_info['mp_buff'] != 0 else ''
    msg += f"名字：{weapon_info['name']}\n"
    msg += f"品阶：{weapon_info['level']}\n"
    msg += f"效果：{atk_buff_msg}{crit_buff_msg}{crit_atk_msg}{def_buff_msg}{mp_buff_msg}{zw_buff_msg}"
    return msg


def get_armor_info_msg(armor_id, armor_info=None):
    """
    获取一个法宝(防具)信息msg
    :param armor_id:法宝(防具)ID
    :param armor_info;法宝(防具)信息json,可不传
    :return 法宝(防具)信息msg
    """
    msg = ''
    if armor_info is None:
        armor_info = items.get_data_by_item_id(armor_id)
    def_buff_msg = f"提升{int(armor_info['def_buff'] * 100)}%减伤率！"
    atk_buff_msg = f"提升{int(armor_info['atk_buff'] * 100)}%攻击力！" if armor_info['atk_buff'] != 0 else ''
    crit_buff_msg = f"提升{int(armor_info['crit_buff'] * 100)}%会心率！" if armor_info['crit_buff'] != 0 else ''
    msg += f"名字：{armor_info['name']}\n"
    msg += f"品阶：{armor_info['level']}\n"
    msg += f"效果：{def_buff_msg}{atk_buff_msg}{crit_buff_msg}"
    return msg


def get_main_info_msg(id):
    mainbuff = items.get_data_by_item_id(id)
    hpmsg = f"提升{round(mainbuff['hpbuff'] * 100, 0)}%气血" if mainbuff['hpbuff'] != 0 else ''
    mpmsg = f"，提升{round(mainbuff['mpbuff'] * 100, 0)}%真元" if mainbuff['mpbuff'] != 0 else ''
    atkmsg = f"，提升{round(mainbuff['atkbuff'] * 100, 0)}%攻击力" if mainbuff['atkbuff'] != 0 else ''
    ratemsg = f"，提升{round(mainbuff['ratebuff'] * 100, 0)}%修炼速度" if mainbuff['ratebuff'] != 0 else ''

    cri_tmsg = f"，提升{round(mainbuff['crit_buff'] * 100, 0)}%会心率" if mainbuff['crit_buff'] != 0 else ''
    def_msg = f"，{'提升' if mainbuff['def_buff'] > 0 else '降低'}{round(abs(mainbuff['def_buff']) * 100, 0)}%减伤率" if \
        mainbuff['def_buff'] != 0 else ''
    dan_msg = f"，增加炼丹产出{round(mainbuff['dan_buff'])}枚" if mainbuff['dan_buff'] != 0 else ''
    dan_exp_msg = f"，每枚丹药额外增加{round(mainbuff['dan_exp'])}炼丹经验" if mainbuff['dan_exp'] != 0 else ''
    reap_msg = f"，提升药材收取数量{round(mainbuff['reap_buff'])}个" if mainbuff['reap_buff'] != 0 else ''
    exp_msg = f"，突破失败{round(mainbuff['exp_buff'] * 100, 0)}%经验保护" if mainbuff['exp_buff'] != 0 else ''
    critatk_msg = f"，提升{round(mainbuff['critatk'] * 100, 0)}%会心伤害" if mainbuff['critatk'] != 0 else ''
    two_msg = f"，增加{round(mainbuff['two_buff'])}次双修次数" if mainbuff['two_buff'] != 0 else ''
    number_msg = f"，提升{round(mainbuff['number'])}%突破概率" if mainbuff['number'] != 0 else ''

    clo_exp_msg = f"，提升{round(mainbuff['clo_exp'] * 100, 0)}%闭关经验" if mainbuff['clo_exp'] != 0 else ''
    clo_rs_msg = f"，提升{round(mainbuff['clo_rs'] * 100, 0)}%闭关生命回复" if mainbuff['clo_rs'] != 0 else ''
    random_buff_msg = f"，战斗时随机获得一个战斗属性" if mainbuff['random_buff'] != 0 else ''
    ew_msg = f"，使用专属武器时伤害增加50%！" if mainbuff['ew'] != 0 else ''
    msg = f"{mainbuff['name']}: {hpmsg}{mpmsg}{atkmsg}{ratemsg}{cri_tmsg}{def_msg}{dan_msg}{dan_exp_msg}{reap_msg}{exp_msg}{critatk_msg}{two_msg}{number_msg}{clo_exp_msg}{clo_rs_msg}{random_buff_msg}{ew_msg}！"
    return mainbuff, msg


def get_sub_info_msg(id):
    subbuff = items.get_data_by_item_id(id)
    submsg = ""

    if subbuff.get('buff_type') == '1':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%攻击力"
    elif subbuff.get('buff_type') == '2':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%暴击率"
    elif subbuff.get('buff_type') == '3':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%暴击伤害"
    elif subbuff.get('buff_type') == '4':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%每回合气血回复"
    elif subbuff.get('buff_type') == '5':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%每回合真元回复"
    elif subbuff.get('buff_type') == '6':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%气血吸取"
    elif subbuff.get('buff_type') == '7':
        submsg = "提升" + str(subbuff.get('buff', 0)) + "%真元吸取"
    elif subbuff.get('buff_type') == '8':
        submsg = "给对手造成" + str(subbuff.get('buff', 0)) + "%中毒"
    elif subbuff.get('buff_type') == '9':
        submsg = f"提升{subbuff.get('buff', 0)}%气血吸取,提升{subbuff.get('buff2', 0)}%真元吸取"

    return submsg

    stone_msg = "提升{}%boss战灵石获取".format(round(subbuff['stone'] * 100, 0)) if subbuff['stone'] != 0 else ''
    integral_msg = "，提升{}点boss战积分获取".format(round(subbuff['integral'])) if subbuff['integral'] != 0 else ''
    jin_msg = "禁止对手吸取" if subbuff['jin'] != 0 else ''
    drop_msg = "，提升boss掉落率" if subbuff['drop'] != 0 else ''
    fan_msg = "使对手发出的debuff失效" if subbuff['fan'] != 0 else ''
    break_msg = "获得战斗破甲" if subbuff['break'] != 0 else ''
    exp_msg = "，增加战斗获得的修为" if subbuff['exp'] != 0 else ''

    msg = f"{subbuff['name']}：{submsg}{stone_msg}{integral_msg}{jin_msg}{drop_msg}{fan_msg}{break_msg}{exp_msg}"
    return subbuff, msg


def get_user_buff(user_id):
    buffinfo = sql_message.get_user_buff_info(user_id)
    if buffinfo is None:
        sql_message.initialize_user_buff_info(user_id)
        return sql_message.get_user_buff_info(user_id)
    else:
        return buffinfo


def readf(FILEPATH):
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def get_sec_msg(secbuffdata):
    msg = None
    if secbuffdata is None:
        msg = "无"
        return msg
    hpmsg = f"，消耗当前血量{int(secbuffdata['hpcost'] * 100)}%" if secbuffdata['hpcost'] != 0 else ''
    mpmsg = f"，消耗真元{int(secbuffdata['mpcost'] * 100)}%" if secbuffdata['mpcost'] != 0 else ''

    if secbuffdata['skill_type'] == 1:
        shmsg = ''
        for value in secbuffdata['atkvalue']:
            shmsg += f"{value}倍、"
        if secbuffdata['turncost'] == 0:
            msg = f"攻击{len(secbuffdata['atkvalue'])}次，造成{shmsg[:-1]}伤害{hpmsg}{mpmsg}，释放概率：{secbuffdata['rate']}%"
        else:
            msg = f"连续攻击{len(secbuffdata['atkvalue'])}次，造成{shmsg[:-1]}伤害{hpmsg}{mpmsg}，休息{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
    elif secbuffdata['skill_type'] == 2:
        msg = f"持续伤害，造成{secbuffdata['atkvalue']}倍攻击力伤害{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
    elif secbuffdata['skill_type'] == 3:
        if secbuffdata['bufftype'] == 1:
            msg = f"增强自身，提高{secbuffdata['buffvalue']}倍攻击力{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
        elif secbuffdata['bufftype'] == 2:
            msg = f"增强自身，提高{secbuffdata['buffvalue'] * 100}%减伤率{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
    elif secbuffdata['skill_type'] == 4:
        msg = f"封印对手{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%，命中成功率{secbuffdata['success']}%"

    return msg


def get_player_info(user_id, info_name):
    player_info = None
    if info_name == "mix_elixir_info":  # 灵田信息
        mix_elixir_infoconfigkey = ["收取时间", "收取等级", "灵田数量", '药材速度', "丹药控火", "丹药耐药性",
                                    "炼丹记录", "炼丹经验"]
        nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
        MIXELIXIRINFOCONFIG = {
            "收取时间": nowtime,
            "收取等级": 0,
            "灵田数量": 1,
            '药材速度': 0,
            "丹药控火": 0,
            "丹药耐药性": 0,
            "炼丹记录": {},
            "炼丹经验": 0
        }
        try:
            player_info = read_player_info(user_id, info_name)
            for key in mix_elixir_infoconfigkey:
                if key not in list(player_info.keys()):
                    player_info[key] = MIXELIXIRINFOCONFIG[key]
            save_player_info(user_id, player_info, info_name)
        except:
            player_info = MIXELIXIRINFOCONFIG
            save_player_info(user_id, player_info, info_name)
    return player_info


def read_player_info(user_id, info_name):
    user_id = str(user_id)
    FILEPATH = PLAYERSDATA / user_id / f"{info_name}.json"
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def save_player_info(user_id, data, info_name):
    user_id = str(user_id)

    if not os.path.exists(PLAYERSDATA / user_id):
        logger.opt(colors=True).info(f"<green>用户目录不存在，创建目录</green>")
        os.makedirs(PLAYERSDATA / user_id)

    FILEPATH = PLAYERSDATA / user_id / f"{info_name}.json"
    data = json.dumps(data, ensure_ascii=False, indent=4)
    save_mode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=save_mode, encoding="UTF-8") as f:
        f.write(data)
        f.close()
