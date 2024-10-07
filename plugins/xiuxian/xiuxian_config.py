
try:
    import ujson as json  # type: ignore
except ImportError:
    import json
from pathlib import Path
from nonebot.log import logger
from .xiuxian_utils.item_database_handler import Items


DATABASE = Path() / "data" / "xiuxian"

class XiuConfig:
    def __init__(self):
        self.sql_user_xiuxian = [
            "id", "user_id", "user_name", "stone", "root",
            "root_type", "level", "power",
            "create_time", "is_sign", "is_beg", "is_ban",
            "exp", "work_num", "level_up_cd",
            "level_up_rate", "sect_id",
            "sect_position", "hp", "mp", "atk",
            "atkpractice", "sect_task", "sect_contribution",
            "sect_elixir_get", "blessed_spot_flag", "blessed_spot_name",
            "user_stamina", "consecutive_wins", "consecutive_losses", "poxian_num",
            "rbPts", "cultEff", "seclEff", "maxR", "maxH", "maxM", "maxA"
        ]
        self.sql_user_cd = [
            "user_id", "type", "create_time", "scheduled_time", "last_check_info_time"
        ]
        self.sql_sects = [
            "sect_id", "sect_name", "sect_owner", "sect_scale", "sect_used_stone", "sect_fairyland",
            "sect_materials", "mainbuff", "secbuff", "elixir_room_level"
        ]
        self.sql_buff = [
            "id", "user_id", "main_buff", "sec_buff", "faqi_buff", "fabao_weapon", "armor_buff",
            "atk_buff", "sub_buff", "blessed_spot"
        ]
        self.sql_back = [
            "user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
            "remake", "day_num", "all_num", "action_time", "state", "bind_num"
        ]
        self.sql_xiuxian_wupin_jichu = [
            "item_id", "item_name", "item_type", "description","type"
        ]

        self.sql_xiuxian_fangju = [
            "item_id", "level", "def_buff", "atk_buff", "crit_buff", "rank"
        ]

        self.sql_xiuxian_shentong = [
            "item_id", "skill_type", "atkvalue", "hpcost", "mpcost", "turncost", "jndesc", "rate", "rank",
            "level","buffvalue", "bufftype"
        ]

        self.sql_xiuxian_faqi = [
            "item_id", "atk_buff", "crit_buff", "def_buff", "critatk", "zw", "mp_buff", "rank", "level"
        ]

        self.sql_xiuxian_gongfa = [
            "item_id", "hpbuff", "mpbuff", "atkbuff", "ratebuff", "crit_buff", "def_buff", "dan_exp", "dan_buff",
            "reap_buff", "exp_buff", "critatk", "two_buff", "number", "clo_exp", "clo_rs", "random_buff", "ew", "rank",
            "level"
        ]

        self.sql_xiuxian_fuxiu_gongfa = [
            "item_id", "buff_type", "buff", "buff2", "stone", "integral", "jin", "drop", "fan", "break", "exp", "rank",
            "level"
        ]

        self.sql_xiuxian_xiulian_wupin = [
            "item_id", "type", "cultivation_speed", "herb_speed", "rank"
        ]

        self.sql_xiuxian_danyao = [
            "item_id", "buff_type", "buff", "price", "selling", "realm", "status", "quantity", "day_num", "all_num",
            "rank"
        ]

        self.sql_xiuxian_liandandanyao = [
            "item_id", "buff_type", "all_num", "buff", "realm", "mix_need_time", "mix_exp", "mix_all", "elixir_config",
            "rank"
        ]

        self.sql_xiuxian_liandanlu = [
            "item_id", "type", "buff", "rank"
        ]

        self.sql_xiuxian_shenwu = [
            "item_id", "buff_type", "all_num", "buff", "realm", "mix_need_time", "mix_exp", "mix_all", "elixir_config",
            "rank"
        ]

        self.sql_xiuxian_yaocai = [
            "item_id", "level", "primary_ingredient", "catalyst", "auxiliary_ingredient", "rank"
        ]
        self.sql_xiuxian_jingjie = [
            "id", "jingjie_name", "power", "atk", "ac", "spend", "hp", "mp", "comment", "rate", "exp", "sp", "sp_ra"
        ]
        self.sql_xiuxian_group_config = [
            "group_id", "enabled_xiuxian", "enabled_paimai", "enabled_boss", "enabled_mijing"
        ]
        self.sql_xiuxian_bank_info = [
            "user_id", "savestone", "savetime", "banklevel"
        ]
        self.sql_xiuxian_bank_levels = [
            "level", "save_max", "level_up_cost", "interest_rate", "level_name"
        ]
        self.sql_xiuxian_mijing_config = [
            "name", "type_rate", "rank", "base_count", "time"
        ]
        self.sql_xiuxian_mijing_info = [
            "name", "rank", "current_count", "l_user_id", "time", "created_at"
        ]
        # 上面是数据库校验,别动
        self.level = Items().convert_rank('江湖好手')[1]  # 境界列表，别动
        self.img = False  # 是否使用图片发送消息
        self.level_up_cd = 0  # 突破CD(分钟)
        self.closing_exp = 60  # 闭关每分钟获取的修为
        self.cultivation_exp = 6  # 单次修炼获取的修为相对于闭关1分钟修炼的倍数
        self.put_bot = []  # 接收消息qq,主qq，框架将只处理此qq的消息
        self.main_bo = []  # 负责发送消息的qq
        self.shield_group = []  # 屏蔽的群聊
        self.layout_bot_dict = {}
        # QQ所负责的群聊 #{群 ：bot}   其中 bot类型 []或str }
        # "123456":"123456",
        self.sect_min_level = "铭纹境圆满"  # 创建宗门最低境界
        self.sect_create_cost = 5000000  # 创建宗门消耗
        self.sect_rename_cost = 50000000  # 宗门改名消耗
        self.sect_rename_cd = 1  # 宗门改名cd/天
        self.auto_change_sect_owner_cd = 7  # 自动换长时间不玩宗主cd/天
        self.closing_exp_upper_limit = 100  # 获取修为上限（例如：1.5 下个境界的修为数*1.5）
        self.level_punishment_floor = 1  # 突破失败扣除修为，惩罚下限（百分比）
        self.level_punishment_limit = 5  # 突破失败扣除修为，惩罚上限(百分比)
        self.level_up_probability = 0.2  # 突破失败增加当前境界突破概率的比例
        self.sign_in_lingshi_lower_limit = 20000000  # 每日签到灵石下限
        self.sign_in_lingshi_upper_limit = 50000000  # 每日签到灵石上限
        self.beg_max_level = "铭纹境圆满"  # 仙途奇缘能领灵石最高境界
        self.beg_max_days = 3  # 仙途奇缘能领灵石最多天数
        self.beg_lingshi_lower_limit = 50000000  # 仙途奇缘灵石下限
        self.beg_lingshi_upper_limit = 100000000  # 仙途奇缘灵石上限
        self.tou = 100000  # 偷灵石惩罚
        self.peiyang_cd = 0  # 鉴定灵石cd/秒
        self.peiyang_min = "神火境初期"  # 鉴定灵石最低境界需求神火境初期
        self.tou_lower_limit = 0.01  # 偷灵石下限(百分比)
        self.tou_upper_limit = 0.50  # 偷灵石上限(百分比)
        self.remake = 100000  # 重入仙途的消费
        self.max_stamina = 500  # 体力上限
        self.tilihuifu_min = 1  # 体力每分钟回复1
        self.lunhui_min_level = "祭道境圆满"  # 千世轮回最低境界
        self.twolun_min_level = "祭道境圆满"  # 万世轮回最低境界
        self.del_boss_id = []  # 支持非管理员和超管天罚boss
        self.gen_boss_id = []  # 支持非管理员和超管生成boss
        self.merge_forward_send = False  # 消息合并转发,True是合并转发，False是长图发送，建议长图发送
        self.img_compression_limit = 50  # 图片压缩率，0为不压缩，最高100
        self.img_type = "webp"  # 图片类型，webp或者jpeg，如果机器人的图片消息不显示请使用jpeg，jpeg请调低压缩率
        self.img_send_type = "base64"  # 图片发送类型,默认io,官方bot建议base64
        self.third_party_bot = False  # 是否是野生机器人，是的话填True，官方bot请填False
        self.version = "xiuxian_2.2"  # 修仙插件版本，别动
