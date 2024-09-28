from decimal import Decimal
from ..xiuxian_utils.xiuxian2_handle import OtherSet, UserBuffDate, XiuxianDateManage
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.utils import number_to

sql_message = XiuxianDateManage()  # sql类

class XiuxianCalculator:
    def __init__(self, user_info):
        self.user_info = user_info

    def calculate(self):
        # 初始化计算结果字典
        result = {}

        # 获取必要的信息
        level_rate = sql_message.get_root_rate(self.user_info['root_type'])  # 灵根倍率
        realm_rate = Decimal(str(jsondata.level_data()[self.user_info['level']]["spend"]))  # 境界倍率
        user_poxian = self.user_info['poxian_num']  # 破限次数
        user_maxR = Decimal(str(self.user_info['maxR'])) # 轮回灵根加点数
        user_info_atk = Decimal(str(self.user_info['atk'])) # 攻击力
        user_maxA = Decimal(str(self.user_info['maxA'])) # 轮回攻击加点数

        # 计算破限带来的总增幅百分比
        total_poxian_percent = self.calculate_total_poxian_percent(user_poxian)

        # 应用破限增幅到战力和攻击力
        level_rate_with_poxian = (Decimal(str(level_rate)) + (user_maxR / Decimal('100'))) * (
                1 + total_poxian_percent / Decimal('100'))
        atk_with_poxian = (user_info_atk + (user_maxA * Decimal('10000'))) * (
                1 + total_poxian_percent / Decimal('100'))

        # 获取用户信息
        user_name = self.user_info['user_name']
        user_sex = self.user_info['user_sex']
        user_id = self.user_info['user_id']
        user_level = self.user_info['level']
        user_exp = self.user_info['exp']
        user_stone = self.user_info['stone']
        user_rank = int(sql_message.get_exp_rank(user_id)[0])
        stone_rank = int(sql_message.get_stone_rank(user_id)[0])
        user_atkpractice = self.user_info['atkpractice']
        sectmsg = self.get_sect_info()
        sectzw = self.get_sect_position_title()
        main_buff_name = self.get_main_buff_name()
        sub_buff_name = self.get_sub_buff_name()
        sec_buff_name = self.get_sec_buff_name()
        weapon_name = self.get_weapon_name()
        armor_name = self.get_armor_name()

        # 计算战力
        combat_power = number_to(int(user_exp * level_rate_with_poxian * realm_rate))

        # 分开计算突破状态和突破概率
        breakthrough_status = self.calculate_breakthrough_status()
        breakthrough_chance = self.calculate_breakthrough_chance()

        # 构造返回结果
        result['道号'] = user_name
        result['性别'] = user_sex
        result['ID'] = user_id
        result['境界'] = user_level
        result['修为'] = number_to(user_exp)
        result['灵石'] = number_to(user_stone)
        result['战力'] = combat_power
        result['灵根'] = f"{self.user_info['root']}({self.user_info['root_type']}+{int(level_rate_with_poxian * 100)}%)"
        result['破限增幅'] = f"{total_poxian_percent}%"
        result['突破状态'] = breakthrough_status
        result['突破概率'] = breakthrough_chance
        result['攻击力'] = number_to(int(atk_with_poxian))
        result['攻修等级'] = user_atkpractice
        result['所在宗门'] = sectmsg
        result['宗门职位'] = sectzw
        result['主修功法'] = main_buff_name
        result['辅修功法'] = sub_buff_name
        result['副修神通'] = sec_buff_name
        result['法器'] = weapon_name
        result['防具'] = armor_name
        result['注册位数'] = self.user_info['id']
        result['修为排行'] = user_rank
        result['灵石排行'] = stone_rank

        return result

    def calculate_total_poxian_percent(self, user_poxian):
        """获取破限次数的增幅"""
        if user_poxian <= 10:
            return user_poxian * 10
        else:
            return (10 * 10) + ((user_poxian - 10) * 20)

    def calculate_breakthrough_status(self):
        """获取距离突破的修为"""
        list_all = len(OtherSet().level) - 1
        now_index = OtherSet().level.index(self.user_info['level'])
        if list_all == now_index:
            return "位面至高"
        else:
            is_updata_level = OtherSet().level[now_index + 1]
            need_exp = sql_message.get_level_power(is_updata_level)
            get_exp = need_exp - self.user_info['exp']
            if get_exp > 0:
                return f"还需{number_to(get_exp)}修为可突破！"
            else:
                return "可突破！"

    def calculate_breakthrough_chance(self):
        """获取当前突破的概率"""
        list_all = len(OtherSet().level) - 1
        now_index = OtherSet().level.index(self.user_info['level'])
        main_rate_buff = UserBuffDate(self.user_info['user_id']).get_user_main_buff_data()  # 功法突破概率提升
        if list_all == now_index:
            return "已达到最高境界"
        else:
            leveluprate = int(self.user_info['level_up_rate'])  # 用户失败次数加成
            number = main_rate_buff["number"] if main_rate_buff is not None else 0
            return f"概率：{jsondata.level_rate_data()[self.user_info['level']] + leveluprate + number}%"

    def get_sect_info(self):
        """获取用户宗门信息"""
        sect_id = self.user_info['sect_id']
        if sect_id:
            sect_info = sql_message.get_sect_info(sect_id)
            return sect_info['sect_name']
        return "无宗门"

    def get_sect_position_title(self):
        """获取宗门配置中 用户的职位"""
        sect_id = self.user_info['sect_id']
        if sect_id:
            return jsondata.sect_config_data()[f"{self.user_info['sect_position']}"]["title"]
        return "无"

    def get_main_buff_name(self):
        """获取用户的主修功法 名字和等级"""
        user_buff_data = UserBuffDate(self.user_info['user_id'])
        user_main_buff_date = user_buff_data.get_user_main_buff_data()
        return f"{user_main_buff_date['name']}({user_main_buff_date['level']})" if user_main_buff_date else '无'

    def get_sub_buff_name(self):
        """获取用户的辅修功法 名字和等级"""
        user_buff_data = UserBuffDate(self.user_info['user_id'])
        user_sub_buff_date = user_buff_data.get_user_sub_buff_data()
        return f"{user_sub_buff_date['name']}({user_sub_buff_date['level']})" if user_sub_buff_date else '无'

    def get_sec_buff_name(self):
        """获取用户的副修神通 名字和等级"""
        user_buff_data = UserBuffDate(self.user_info['user_id'])
        user_sec_buff_date = user_buff_data.get_user_sec_buff_data()
        return f"{user_sec_buff_date['name']}({user_sec_buff_date['level']})" if user_sec_buff_date else '无'

    def get_weapon_name(self):
        """获取用户的法器 名字和等级"""
        user_buff_data = UserBuffDate(self.user_info['user_id'])
        user_weapon_data = user_buff_data.get_user_weapon_data()
        return f"{user_weapon_data['name']}({user_weapon_data['level']})" if user_weapon_data else '无'

    def get_armor_name(self):
        """获取用户的防具 名字和等级"""
        user_buff_data = UserBuffDate(self.user_info['user_id'])
        user_armor_data = user_buff_data.get_user_armor_buff_data()
        return f"{user_armor_data['name']}({user_armor_data['level']})" if user_armor_data else '无'