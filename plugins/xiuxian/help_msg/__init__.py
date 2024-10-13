from nonebot import on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent
)
from nonebot.log import logger

from .. import NICKNAME
from ..xiuxian_back import auction_time_config
from ..xiuxian_config import XiuConfig
from ..xiuxian_sect import config
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..bounty_order import user_work_nums

help_xiuxian = on_command("修仙帮助", priority=12, permission=GROUP, block=True)
help_jingjie = on_fullmatch('境界列表', priority=15, permission=GROUP, block=True)
help_linggen = on_fullmatch('灵根列表', priority=15, permission=GROUP, block=True)
help_pinjie = on_fullmatch('品阶列表', priority=15, permission=GROUP, block=True)
help_back = on_command("背包帮助", aliases={"坊市帮助"}, priority=8, permission=GROUP, block=True)
help_bank = on_fullmatch('灵庄帮助', priority=8, permission=GROUP, block=True)
help_qiyuan = on_fullmatch("仙途奇缘帮助", permission=GROUP, priority=7, block=True)
help_boss = on_command("世界boss帮助", aliases={"世界Boss帮助", "世界BOSS帮助"}, priority=5, block=True)
help_gongfa_lingtian = on_command("功法帮助", aliases={"灵田帮助"}, priority=5, permission=GROUP, block=True)
help_xushen_chuancheng = on_command("传承帮助", aliases={"虚神界帮助"}, priority=8, permission=GROUP, block=True)
help_lunhuicx = on_fullmatch("轮回重修帮助", priority=12, permission=GROUP, block=True)
help_lunhuijd = on_fullmatch('轮回加点帮助', priority=15, permission=GROUP, block=True)
help_jianshi = on_fullmatch("鉴石帮助", priority=7, permission=GROUP, block=True)
help_mijing = on_fullmatch("秘境帮助", priority=6, permission=GROUP, block=True)
help_sect = on_fullmatch("宗门帮助", priority=5, permission=GROUP, block=True)
help_xuanshang = on_fullmatch("悬赏令帮助", priority=9, permission=GROUP, block=True)

__help_xiuxian__ = f"""
修仙帮助详情：
- 指令/说明：
  - 我要修仙: 步入修仙世界。
  - 我的修仙信息: 获取修仙数据。
  - 修仙签到: 获取灵石。
  - 洗髓伐骨: 重置灵根数据，每次消耗 {XiuConfig().remake} 灵石。
  - 改名: 随机修改你的道号。
  - 突破: 修为足够后，可突破境界（有一定几率失败）。
  - 闭关、出关、灵石出关、灵石修炼、双修: 增加修为。
  - 送灵石 [数量] [道号]、偷灵石 [数量] [道号]、抢灵石 [数量] [道号]: 灵石相关操作。
  - 排行榜: 修仙排行榜、灵石排行榜、战力排行榜、轮回排行榜、宗门排行榜。
  - 悬赏令帮助: 获取悬赏令帮助信息。
  - 我的状态: 查看当前各项状态。
  - 我的功法: 查看当前技能。
  - 宗门系统: 发送“宗门帮助”获取。
  - 灵庄系统: 发送“灵庄帮助”获取。
  - 世界 BOSS: 发送“世界 boss 帮助”获取。
  - 功法/灵田: 发送“功法帮助/灵田帮助”查看。
  - 背包/拍卖: 发送“背包帮助”获取。
  - 秘境系统: 发送“秘境帮助”获取。
  - 炼丹帮助: 炼丹功能。
  - 传承系统: 发送“传承帮助/虚神界帮助”获取。
  - 启用/禁用修仙功能: 当前群开启或关闭修仙功能。
  - 仙途奇缘: 发送“仙途奇缘帮助”获取。
  - 轮回重修: 发送“轮回重修帮助”获取。
  - 境界列表、灵根列表、品阶列表: 获取对应列表信息。
  - 仙器合成: 发送“合成 xx”获取，目前开放合成的仙器为天罪。
""".strip()
__help_jingjie__ = """
--境界列表--
祭道境——仙帝境——虚神境——轮回境
金仙境——创世境——混沌境——斩我境
虚道境——天神境——圣祭境——真一境
神火境——尊者境——列阵境——铭纹境
化灵境——洞天境——搬血境——江湖人
""".strip()
__help_linggen__ = """
--灵根列表--
轮回——异界——机械——混沌
融——超——龙——天——异——真——伪
""".strip()
__help_pinjie__ = """
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
__help_back__ = f"""
背包帮助详情：
- 指令/说明：
  - 我的背包、我的物品：查看自身背包前196个物品的信息
  - 使用 + 物品名字：使用物品，可批量使用
  - 换装 + 装备名字：卸载目标装备
  - 坊市购买 + 物品编号：购买坊市内的物品，可批量购买
  - 坊市查看、查看坊市：查询坊市在售物品
  - 查看拍卖品、拍卖品查看：查询将在拍卖品拍卖的玩家物品
  - 坊市上架 物品 金额：上架背包内的物品，最低金额50w，可批量上架
  - 提交拍卖品 物品 金额：上架背包内的物品，最低金额随意，可批量上架（需要超管重启机器人）
  - 系统坊市上架 物品 金额：上架任意存在的物品，超管权限
  - 坊市下架 + 物品编号：下架坊市内的物品，管理员和群主可以下架任意编号的物品！
  - 群交流会开启、关闭：开启/关闭拍卖行功能，管理员指令，注意：会在机器人所在的全部已开启此功能的群内通报拍卖消息
  - 拍卖 + 金额：对本次拍卖会的物品进行拍卖
  - 炼金 + 物品名字：将物品炼化为灵石，支持批量炼金和绑定丹药炼金
  - 背包帮助：获取背包帮助指令
- 非指令：
  - 定时生成拍卖会，每天 {auction_time_config['hours']} 点每整点生成一场拍卖会
""".strip()
__help_bank__ = """
灵庄帮助信息:
- 指令：
  - 灵庄: 查看灵庄帮助信息。
  - 灵庄存灵石 [金额]: 存入指定金额的灵石，并获取利息。
  - 灵庄取灵石 [金额]: 取出指定金额的灵石，会先结算利息，再取出灵石。
  - 灵庄升级会员: 升级灵庄会员等级，提升利息倍率。
  - 灵庄信息: 查询当前的灵庄信息。
  - 灵庄结算: 结算当前的利息。
- 注意事项：
  - 存入和取出灵石时，请确保输入正确的金额。
  - 升级会员可以提高利息倍率。
  - 结算利息时，系统会自动计算并添加到您的账户余额。
""".strip()
__help_qiyuan__ = """
详情：
为了让初入仙途的道友们更顺利地踏上修炼之路，特别开辟了额外的机缘：
- 天降灵石，助君一臂之力。
- 若有心人借此谋取不正当利益，必将遭遇天道轮回，异象降临，后果自负。
- 诸位道友，若不信此言，可自行一试，便知天机不可泄露，天道不容欺。
""".strip()
__help_boss__ = f"""
世界Boss帮助信息:
指令：
- 生成世界boss：生成一只随机大境界的世界Boss，超管权限
- 生成指定世界boss：生成指定大境界与名称的世界Boss，超管权限
- 查询世界boss：查询本群全部世界Boss，可加Boss编号查询对应Boss信息
- 世界boss开启/关闭：开启后才可以生成世界Boss，管理员权限
- 讨伐boss/讨伐世界boss：讨伐世界Boss，必须加Boss编号
- 世界boss帮助/世界boss：获取世界Boss帮助信息
- 天罚boss/天罚世界boss：删除世界Boss，必须加Boss编号，管理员权限
- 天罚所有世界boss：删除所有世界Boss，管理员权限
- 世界积分查看：查看自己的世界积分，和世界积分兑换商品
- 世界积分兑换 + 编号：兑换对应的商品，可以批量购买
""".strip()
__help_gongfa_lingtian__ = f"""
功法帮助信息:
指令：
- 我的功法：查看自身功法以及背包内的所有功法信息
- 切磋 [道号]：切磋对应道友，不会消耗气血
- 洞天福地购买：购买洞天福地
- 洞天福地查看：查看自己的洞天福地
- 洞天福地改名 + 名字：修改自己洞天福地的名字
- 灵田开垦：提升灵田的等级，提高灵田结算的药材数量
- 抑制黑暗动乱：清除修为浮点数
- 我的双修次数：查看剩余双修次数
""".strip()
__help_xushen_chuancheng__ = f"""
传承帮助信息:
-指令：
  - 传承抽卡：花费10颗思恋结晶获取一次传承卡片（抽到的卡片被动加成）
  - 传承信息：获取传承主要信息
  - 传承背包：获取传承全部信息
  - 加载传承数据：重新从卡片中加载所有传承属性（数据显示有误时可用）
  - 传承卡图 + 卡片名字：获取传承卡牌原画
  - 投影虚神界：将自己的分身投影到虚神界，将可被所有地域的道友挑战
  - 虚神界列表：查找虚神界里所有的投影
  - 虚神界对决 + 人物编号：与对方对决，不输入编号将会与 {NICKNAME} 进行对决
  - 虚神界修炼 + 修炼时间：在虚神界修炼
-特别说明：虚神界无轮回破限加成
  -思恋结晶获取方式：虚神界对决【俄罗斯轮盘修仙版】
   双方共有6次机会，6次中必有一次暴毙
   获胜者将获取10颗思恋结晶并不消耗虚神界对决次数
   失败者将获取5颗思恋结晶并且消耗一次虚神界对决次数
   每天有三次虚神界对决次数
""".strip()
__help_lunhuicx__ = """
轮回重修帮助：
- 详情：
  - 散尽修为，轮回重修，将万世的道果凝聚为极致天赋。
  - 修为、功法、神通将被清空！
  - 进入千世轮回：获得轮回灵根，增加破限次数，破限10次可进入万世轮回，可定制极品仙器（在做）。
  - 进入万世轮回：获得真轮回灵根，可定制无上仙器（在做）。
  - 重入修仙：字面意思，仅搬血境可用。
- 使用方法：
  - 输入「进入千世轮回/进入万世轮回」开始轮回重修。
  - 输入「从头再来」将重新开始。
  - 输入「轮回加点 查询」查看当前状态和剩余破限次数。
- 注意事项：
  - 轮回重修后，修为、功法、神通将被清空。
  - 千世轮回每次获得最终增幅10%(真元/血量/灵根/闭关收益/修炼收益)
  - 万世轮回每次获得最终增幅20%(真元/血量/灵根/闭关收益/修炼收益)
  - 重入修仙仅在搬血境可用。
""".strip()
__help_lunhuijd__ = """
轮回加点帮助：
- 使用方法：
  - 输入「轮回加点 属性名称 数字」分配轮回点数到特定属性。
    - 示例：「轮回加点 修炼 10」将10点轮回点数分配给修炼效率。
  - 属性名称对应如下：
    - 修炼：增加修炼效率（每点增加修炼效率1%）
    - 闭关：增加闭关效率（每点增加闭关效率1%）
    - 灵根：增加灵根效率（每点增加灵根效率1%）
    - 血量：增加血量上限（每点增加血量100000）
    - 真元：增加真元上限（每点增加真元100000）
    - 攻击：增加攻击上限（每点增加攻击10000）
  - 输入「轮回加点 重置」重置所有已分配的轮回点数。
  - 输入「轮回加点 查询」查看当前已分配的属性点数和剩余未分配的轮回点数。
- 注意事项：
  - 分配的点数不能超过当前拥有的轮回点数。
  - 重置会将所有已分配的点数返回到轮回点数池中。
  - 查询功能可以帮助你了解当前属性点数分配情况及剩余轮回点数。
  - 千世轮回每次可得20轮回点,万世轮回每次可得50轮回点。
""".strip()
__help_jianshi__ = f"""
鉴定灵石帮助:
【鉴石秘技】
　　在修仙的世界里，灵石不仅是修行者们最宝贵的财富之一，更是通往更高境界的关键。然而，灵石之中往往蕴含着未知的秘密——有的灵石看似平凡无奇，却可能蕴藏着巨大的潜力；有的灵石外表华丽，实则一文不值。只有真正的鉴石大师才能洞察其中的奥秘。
　　当你使用「鉴石」指令时，将会尝试揭示灵石中的潜在能量。如果你的运气足够好，或许能发现那些隐藏在普通灵石中的惊人价值，甚至获得更多的灵石作为奖励。但若是运气不佳，也可能导致灵石失去原有的价值，甚至造成一定的损失。
　　指令(最低境界要求【{XiuConfig().peiyang_min}】):
　　　　鉴石 [灵石数量]
【注意事项】
- 鉴石是一项充满不确定性的活动，务必谨慎行事。
- 仅限达到一定境界的修行者方可尝试，以免因修为不足而遭受反噬。
- 鉴石过程中，可能会触发各种意外事件，增加鉴石的趣味性和挑战性。
""".strip()
__help_mijing__ = f"""
秘境帮助信息(默认开启中):
-指令：
  - 群秘境开启: 开启本群的秘境生成功能，管理员权限
  - 群秘境关闭: 关闭本群的秘境生成功能，管理员权限
  - 生成秘境: 生成一个随机秘境，超管权限
  - 探索秘境: 探索秘境获取随机奖励
  - 秘境结算: 结算秘境奖励
  - 终止探索秘境: 终止秘境事件
  - 秘境帮助: 获取秘境帮助信息
-非指令：
  - 每天早上8点自动生成一个随机等级的秘境
-说明：
  - 群秘境开启：开启本群的秘境生成功能，允许生成新的秘境。
  - 群秘境关闭：关闭本群的秘境生成功能，不允许生成新的秘境。
""".strip()
__help_sect__ = f"""
宗门帮助信息:
- 指令：
  - 我的宗门: 查看当前所处宗门信息。
  - 创建宗门: 创建宗门，需求：{XiuConfig().sect_create_cost} 灵石，需求境界 {XiuConfig().sect_min_level}。
  - 加入宗门: 加入一个宗门，需要带上宗门 ID。
  - 宗门职位变更: 宗主可以改变宗门成员的职位等级【0 1 2 3 4】，分别对应【宗主 长老 亲传 内门 外门】（外门弟子无法获得宗门修炼资源）。
  - 宗门捐献: 建设宗门，提高宗门建设度，每 {config["等级建设度"]} 建设度会提高 1 级攻击修炼等级上限。
  - 宗门改名: 宗主可以改变宗门名称。
  - 退出宗门: 退出当前宗门。
  - 踢出宗门: 踢出对应宗门成员，需要输入正确的 QQ 号或 @ 对方。
  - 宗主传位: 宗主可以传位给宗门成员。
  - 升级攻击修炼: 升级道友的攻击修炼等级，每级修炼等级提升 4% 攻击力，后面可以接升级等级。
  - 宗门列表: 查看所有宗门列表。
  - 宗门任务接取、我的宗门任务: 接取宗门任务，可以增加宗门建设度和资材，每日上限：{config["每日宗门任务次上限"]} 次。
  - 宗门任务完成: 完成所接取的宗门任务，完成间隔时间：{config["宗门任务完成cd"]} 秒。
  - 宗门任务刷新: 刷新当前所接取的宗门任务，刷新间隔时间：{config["宗门任务刷新cd"]} 秒。
  - 宗门功法、神通搜寻: 宗主可消耗宗门资材和宗门灵石来搜寻 100 次功法或者神通。
  - 学习宗门功法、神通: 宗门成员可消耗宗门资材来学习宗门功法或者神通，后面接功法名称。
  - 宗门功法查看: 查看当前宗门已有的功法。
  - 宗门成员查看、查看宗门成员: 查看所在宗门的成员信息。
  - 宗门丹房建设、建设宗门丹房: 建设宗门丹房，可以让每个宗门成员每日领取丹药。
  - 宗门丹药领取、领取宗门丹药: 领取宗门丹药。
- 非指令：
  - 拥有定时任务: 每日 {config["发放宗门资材"]["时间"]} 点发放 {config["发放宗门资材"]["倍率"]} 倍对应宗门建设度的资材。
  - 道统传承: 宗主 | 长老 | 亲传弟子 | 内门弟子 | 外门弟子 | 散修 单次稳定获得百分比修为上限分别为：{jsondata.sect_config_data()[str(0)]["max_exp"]}，{jsondata.sect_config_data()[str(1)]["max_exp"]}，{jsondata.sect_config_data()[str(2)]["max_exp"]}，{jsondata.sect_config_data()[str(3)]["max_exp"]}，{jsondata.sect_config_data()[str(4)]["max_exp"]}，{jsondata.sect_config_data()[str(4)]["max_exp"]}。
""".strip()
__help_xuanshang__ = f"""
悬赏令帮助信息:
- 指令：
  - 悬赏令: 获取对应实力的悬赏令
  - 悬赏令刷新: 刷新当前悬赏令，每日免费 {user_work_nums} 次
  - 悬赏令终止: 终止当前悬赏令任务
  - 悬赏令结算: 结算悬赏奖励
  - 悬赏令接取 + 编号：接取对应的悬赏令
  - 最后的悬赏令: 用于接了悬赏令却境界突破导致卡住的道友使用
- 实力支持：
  - 江湖人 - 搬血境 - 洞天境 - 化灵境
  - 铭纹境 - 列阵境 - 尊者境 - 神火境 
  - 真一境 - 圣祭境 - 天神境 - 虚道境
  - 斩我境 - 混沌境 - 创世境 - 金仙境
""".strip()


async def send_help_info(bot: Bot, event: GroupMessageEvent, msg: str):
    """发送帮助信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await bot.finish()


@help_xiuxian.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_xiuxian(bot: Bot, event: GroupMessageEvent):
    """修仙帮助"""
    await send_help_info(bot, event, __help_xiuxian__)
    await help_xiuxian.finish()


@help_jingjie.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_jingjie(bot: Bot, event: GroupMessageEvent):
    """境界列表"""
    await send_help_info(bot, event, __help_jingjie__)
    await help_jingjie.finish()


@help_linggen.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_linggen(bot: Bot, event: GroupMessageEvent):
    """灵根列表"""
    await send_help_info(bot, event, __help_linggen__)
    await help_linggen.finish()


@help_pinjie.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_pinjie(bot: Bot, event: GroupMessageEvent):
    """品阶列表"""
    await send_help_info(bot, event, __help_pinjie__)
    await help_pinjie.finish()


@help_back.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_back(bot: Bot, event: GroupMessageEvent):
    """背包帮助"""
    await send_help_info(bot, event, __help_back__)
    await help_back.finish()


@help_bank.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_bank(bot: Bot, event: GroupMessageEvent):
    """灵庄帮助"""
    await send_help_info(bot, event, __help_bank__)
    await help_bank.finish()


@help_qiyuan.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_qiyuan(bot: Bot, event: GroupMessageEvent):
    """仙途奇缘帮助"""
    await send_help_info(bot, event, __help_qiyuan__)
    await help_qiyuan.finish()


@help_boss.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_boss(bot: Bot, event: GroupMessageEvent):
    """世界Boss帮助信息"""
    await send_help_info(bot, event, __help_boss__)
    await help_boss.finish()


@help_gongfa_lingtian.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_gongfa_lingtian(bot: Bot, event: GroupMessageEvent):
    """功法帮助信息"""
    await send_help_info(bot, event, __help_gongfa_lingtian__)
    await help_gongfa_lingtian.finish()


@help_xushen_chuancheng.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_xushen_chuancheng(bot: Bot, event: GroupMessageEvent):
    """传承帮助信息"""
    await send_help_info(bot, event, __help_xushen_chuancheng__)
    await help_xushen_chuancheng.finish()


@help_lunhuicx.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_lunhuicx(bot: Bot, event: GroupMessageEvent):
    """轮回重修帮助"""
    await send_help_info(bot, event, __help_lunhuicx__)
    await help_lunhuicx.finish()


@help_lunhuijd.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_lunhuijd(bot: Bot, event: GroupMessageEvent):
    """轮回加点帮助"""
    await send_help_info(bot, event, __help_lunhuijd__)
    await help_lunhuijd.finish()


@help_jianshi.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_jianshi(bot: Bot, event: GroupMessageEvent):
    """鉴定灵石帮助"""
    await send_help_info(bot, event, __help_jianshi__)
    await help_jianshi.finish()


@help_mijing.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_mijing(bot: Bot, event: GroupMessageEvent):
    """秘境帮助"""
    await send_help_info(bot, event, __help_mijing__)
    await help_mijing.finish()


@help_sect.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_sect(bot: Bot, event: GroupMessageEvent):
    """宗门帮助"""
    await send_help_info(bot, event, __help_sect__)
    await help_sect.finish()


@help_xuanshang.handle(parameterless=[Cooldown(at_sender=False)])
async def handle_help_xuanshang(bot: Bot, event: GroupMessageEvent):
    """悬赏令帮助"""
    await send_help_info(bot, event, __help_xuanshang__)
    await help_xuanshang.finish()
