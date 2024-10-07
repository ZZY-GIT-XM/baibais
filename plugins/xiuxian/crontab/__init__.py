from datetime import datetime, timedelta

from nonebot import require
from nonebot.log import logger

from .. import XiuConfig
from ..boss import get_boss_config, createboss, create_boss, get_alive_bosses
from ..xiuxian_buff import two_exp_cd
from ..xiuxian_impart_pk import impart_pk, xu_world
from ..xiuxian_sect import config
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage
)

sql_message = XiuxianDateManage()  # sql类
max_stamina = XiuConfig().max_stamina  # 体力上限
stamina_recovery_rate = 1  # 单次方法执行体力恢复数值
boss_config_kv = get_boss_config()  # 获取 Boss 配置
boss_config_v_time = boss_config_kv['Boss生成时间参数']  # 获取 Boss 生成时间参数
boss_config_v_maxnum = boss_config_kv['Boss个数上限']  # 获取 Boss 生成个数上限

reset_day_danyaonum = require("nonebot_plugin_apscheduler").scheduler
reset_day_qiandao = require("nonebot_plugin_apscheduler").scheduler
reset_day_qiyuan = require("nonebot_plugin_apscheduler").scheduler
reset_day_shuangxiunum = require("nonebot_plugin_apscheduler").scheduler
reset_day_xushennum = require("nonebot_plugin_apscheduler").scheduler
reset_day_xuanshangnum = require("nonebot_plugin_apscheduler").scheduler
reset_zongmen_gongxian_zicai = require("nonebot_plugin_apscheduler").scheduler
reset_zongmen_renwu_danyao = require("nonebot_plugin_apscheduler").scheduler
reset_zongmen_tizongzhu = require("nonebot_plugin_apscheduler").scheduler
reset_tilinum = require("nonebot_plugin_apscheduler").scheduler
reset_huifu_hp = require("nonebot_plugin_apscheduler").scheduler
reset_day_mijing = require("nonebot_plugin_apscheduler").scheduler
reset_min_boss = require("nonebot_plugin_apscheduler").scheduler


@reset_min_boss.scheduled_job('interval', minutes=boss_config_v_time['minutes'])
async def generate_world_boss():
    """定时生成世界Boss"""
    # 获取当前所有Boss信息
    current_bosses = get_alive_bosses()

    # 检查当前Boss数量是否达到上限
    if len(current_bosses) >= boss_config_v_maxnum:
        logger.opt(colors=True).info(f"<yellow>当前世界Boss数量已达上限，无法生成新的Boss</yellow>")
        return

    # 生成新的世界Boss信息
    new_boss = createboss()
    if new_boss:
        # 更新数据库中的Boss信息
        create_boss(new_boss)

        # 构建消息
        msg = f'''新的世界Boss生成成功: {new_boss['jj']} Boss:{new_boss['name']},总血量: {new_boss['max_hp']},攻击力: {new_boss['attack']},携带灵石: {new_boss['stone']}'''
        logger.opt(colors=True).info(f"<green>{msg}</green>")
    else:
        logger.opt(colors=True).error(f"<red>生成世界Boss失败</red>")


@reset_day_mijing.scheduled_job("cron", hour=8, minute=0)
async def reset_day_mijing_():
    """秘境信息次数重置成功"""
    # 获取秘境信息
    rift_info = sql_message.get_mijing_info()
    rift_info_name = rift_info['name']
    config_id = sql_message.get_random_config_id()
    rift_info = sql_message.get_config_by_id(config_id)
    # 更新秘境信息
    sql_message.update_dingshi_mijing_info(rift_info_name, rift_info['name'], rift_info['rank'],
                                           rift_info['base_count'], '', rift_info['time'])

    logger.opt(colors=True).info(f"<green>秘境信息重置成功</green>")


@reset_day_xuanshangnum.scheduled_job("cron", hour=0, minute=0)
async def reset_day_xuanshangnum_():
    """重置悬赏令刷新次数"""
    sql_message.reset_work_num()
    logger.opt(colors=True).info(f"<green>用户悬赏令刷新次数重置成功</green>")


@reset_huifu_hp.scheduled_job('interval', minutes=1)
def reset_huifu_hp_():
    """自动恢复血量HP 当前比例千分之一"""
    sql_message.auto_recover_hp()


@reset_tilinum.scheduled_job('interval', minutes=XiuConfig().tilihuifu_min)
def reset_tilinum_():
    """恢复体力，1分钟回一点"""
    sql_message.update_all_users_stamina(max_stamina, stamina_recovery_rate)


@reset_day_danyaonum.scheduled_job("cron", hour=0, minute=0, )
async def reset_day_danyaonum_():
    """重置丹药每日使用次数"""
    sql_message.day_num_reset()
    logger.opt(colors=True).info(f"<green>每日丹药使用次数重置成功！</green>")


@reset_day_qiandao.scheduled_job("cron", hour=0, minute=0)
async def reset_day_qiandao_():
    """重置每日签到"""
    sql_message.sign_remake()
    logger.opt(colors=True).info(f"<green>每日修仙签到重置成功！</green>")


@reset_day_qiyuan.scheduled_job("cron", hour=0, minute=0)
async def reset_day_qiyuan_():
    """重置奇缘"""
    sql_message.beg_remake()
    logger.opt(colors=True).info(f"<green>仙途奇缘重置成功！</green>")


@reset_day_shuangxiunum.scheduled_job("cron", hour=0, minute=0)
async def reset_day_shuangxiunum_():
    """重置用户双修次数"""
    two_exp_cd.re_data()
    logger.opt(colors=True).info(f"<green>双修次数已更新！</green>")


@reset_day_xushennum.scheduled_job("cron", hour=0, minute=0)
async def reset_day_xushennum_():
    """重置用虚神界次数"""
    impart_pk.re_data()
    xu_world.re_data()
    logger.opt(colors=True).info(f"<green>已重置虚神界次数</green>")


@reset_zongmen_gongxian_zicai.scheduled_job("cron", hour=config["发放宗门资材"]["时间"])
async def reset_zongmen_gongxian_zicai_():
    """每1小时按照宗门的贡献度增加资材"""
    all_sects = sql_message.get_all_sects_id_scale()
    for s in all_sects:
        sql_message.update_sect_materials(sect_id=s[0], sect_materials=s[1] * config["发放宗门资材"]["倍率"], key=1)

    logger.opt(colors=True).info(f"<green>已更新所有宗门的资材</green>")


@reset_zongmen_renwu_danyao.scheduled_job("cron", hour=0, minute=0)
async def reset_zongmen_renwu_danyao_():
    """重置用户宗门任务次数、宗门丹药领取次数"""
    sql_message.sect_task_reset()
    sql_message.sect_elixir_get_num_reset()
    all_sects = sql_message.get_all_sects_id_scale()
    for s in all_sects:
        sect_info = sql_message.get_sect_info(s[0])
        if int(sect_info['elixir_room_level']) != 0:
            elixir_room_cost = \
                config['宗门丹房参数']['elixir_room_level'][str(sect_info['elixir_room_level'])]['level_up_cost'][
                    '建设度']
            if sect_info['sect_materials'] < elixir_room_cost:
                logger.opt(colors=True).info(f"<red>宗门：{sect_info['sect_name']}的资材无法维持丹房</red>")
                continue
            else:
                sql_message.update_sect_materials(sect_id=sect_info['sect_id'], sect_materials=elixir_room_cost, key=2)
    logger.opt(colors=True).info(f"<green>已重置所有宗门任务次数、宗门丹药领取次数，已扣除丹房维护费</green>")


@reset_zongmen_tizongzhu.scheduled_job("interval", hours=1)
async def reset_zongmen_tizongzhu_():
    """每1小时自动检测不常玩的宗主"""
    logger.opt(colors=True).info(f"<yellow>开始检测不常玩的宗主</yellow>")

    all_sect_owners_id = sql_message.get_sect_owners()
    all_active = all(sql_message.get_last_check_info_time(owner_id) is None or
                     datetime.now() - sql_message.get_last_check_info_time(owner_id) < timedelta(
        days=XiuConfig().auto_change_sect_owner_cd)
                     for owner_id in all_sect_owners_id)
    if all_active:
        logger.opt(colors=True).info(f"<green>各宗宗主在修行之途上勤勉不辍，宗门安危无忧，可喜可贺！</green>")

    for owner_id in all_sect_owners_id:
        last_check_time = sql_message.get_last_check_info_time(owner_id)
        if last_check_time is None or datetime.now() - last_check_time < timedelta(
                days=XiuConfig().auto_change_sect_owner_cd):
            continue

        user_info = sql_message.get_user_info_with_id(owner_id)
        sect_id = user_info['sect_id']
        logger.opt(colors=True).info(
            f"<red>{user_info['user_name']}离线时间超过{XiuConfig().auto_change_sect_owner_cd}天，开始自动换宗主</red>")
        new_owner_id = sql_message.get_highest_contrib_user_except_current(sect_id, owner_id)
        new_owner_info = sql_message.get_user_info_with_id(new_owner_id[0])

        sql_message.update_usr_sect(owner_id, sect_id, 1)
        sql_message.update_usr_sect(new_owner_id[0], sect_id, 0)
        sql_message.update_sect_owner(new_owner_id[0], sect_id)
        sect_info = sql_message.get_sect_info_by_id(sect_id)
        logger.opt(colors=True).info(
            f"<green>由{new_owner_info['user_name']}继承{sect_info['sect_name']}宗主之位</green>")
