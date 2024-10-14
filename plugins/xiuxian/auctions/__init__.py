from nonebot.permission import SUPERUSER
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.testing.schema import Column
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy import update, delete, insert, Integer, DateTime, ForeignKey, Boolean, String, BigInteger, \
    Numeric, TIMESTAMP, Sequence
from sqlalchemy.orm import sessionmaker
from plugins.xiuxian.xiuxian_back import get_user_auction_id_list, get_user_auction_price_by_id, \
    get_auction_id_list, get_auction_price_by_id, get_auction_msg
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

# 数据库连接配置
DB_CONFIG = {
    'dbname': 'baibaidb',
    'user': 'postgres',
    'password': 'robots666',
    'host': 'localhost',
    'port': '5432'
}

# 构建数据库 URL
DATABASE_URL = f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=True)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


class XiuxianAuction(Base):
    __tablename__ = 'xiuxian_auction'

    auction_id = Column(Integer, primary_key=True, index=True)
    initiator_id = Column(BigInteger, nullable=False)
    is_system_auction = Column(Boolean, default=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)
    total_items = Column(Integer, nullable=False)
    current_paipin_index = Column(Integer, default=0)


class XiuxianAuctionArchive(Base):
    __tablename__ = 'xiuxian_auction_archive'

    auction_id = Column(Integer, primary_key=True, index=True)
    initiator_id = Column(BigInteger, nullable=False)
    is_system_auction = Column(Boolean, default=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)
    total_items = Column(Integer, nullable=False)
    current_paipin_index = Column(Integer, default=0)
    archive_time = Column(DateTime, nullable=False)


class XiuxianAuctionItems(Base):
    __tablename__ = 'xiuxian_auction_items'

    item_id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, ForeignKey('xiuxian_auction.auction_id'), nullable=False)
    paipin_id = Column(Integer, nullable=False)  # 修改为 Integer
    quantity = Column(Integer, nullable=False)
    start_price = Column(Numeric, nullable=False)
    current_price = Column(Numeric, nullable=False)
    highest_bidder_id = Column(BigInteger, nullable=True)
    bid_time = Column(DateTime, nullable=True)
    is_sold = Column(Boolean, default=False)
    is_user_auction = Column(Boolean, default=False)


class XiuxianAuctionItemsArchive(Base):
    __tablename__ = 'xiuxian_auction_items_archive'

    item_id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, ForeignKey('xiuxian_auction.auction_id'), nullable=False)
    paipin_id = Column(Integer, nullable=False)  # 修改为 Integer
    quantity = Column(Integer, nullable=False)
    start_price = Column(Numeric, nullable=False)
    current_price = Column(Numeric, nullable=False)
    highest_bidder_id = Column(BigInteger, nullable=True)
    bid_time = Column(DateTime, nullable=True)
    is_sold = Column(Boolean, default=False)
    is_user_auction = Column(Boolean, default=False)
    archive_time = Column(DateTime, nullable=False)


class XiuxianAuctionBids(Base):
    __tablename__ = 'xiuxian_auction_bids'

    bid_id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    bid_amount = Column(Numeric, nullable=False)
    bid_time = Column(DateTime, nullable=False)


class XiuxianAuctionBidsArchive(Base):
    __tablename__ = 'xiuxian_auction_bids_archive'

    bid_id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    bid_amount = Column(Numeric, nullable=False)
    bid_time = Column(DateTime, nullable=False)
    archive_time = Column(DateTime, nullable=False)


class AuctionWupin(Base):
    __tablename__ = 'xiuxian_auction_wupin'

    paipin_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, nullable=False)
    user_id = Column(BigInteger)
    min_start_price = Column(Numeric, nullable=False)
    quantity = Column(Integer, nullable=False)
    is_user_provided = Column(Boolean, nullable=False, default=False)
    added_time = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


# 假设这些对象已经定义好了
items = Items()
sql_message = XiuxianDateManage()  # sql类
AUCTIONSLEEPTIME = 30  # 拍卖初始等待时间（秒）
AUCTIONOFFERSLEEPTIME = 30  # 每次拍卖增加拍卖剩余的时间（秒）
auction_offer_time_count = 0  # 计算剩余时间
auction_offer_all_count = 0  # 控制线程等待时间
auction_offer_flag = False  # 拍卖标志
current_auction_index = 0


async def get_item_id_by_paipin_id(paipin_id: int) -> int:
    """通过传入的 paipin_id 获取对应的 item_id"""
    async with AsyncSessionLocal() as session:
        query = select(AuctionWupin.item_id).where(AuctionWupin.paipin_id == paipin_id)
        result = await session.execute(query)
        item_id = result.scalar()
        if item_id is None:
            raise ValueError(f"No item found for paipin_id: {paipin_id}")
        return item_id


async def get_user_auction_info():
    """查询所有用户提供的拍卖物品"""
    async with AsyncSessionLocal() as session:
        query = select(AuctionWupin).where(AuctionWupin.is_user_provided == True)
        result = await session.execute(query)
        user_auctions = result.scalars().all()

        # 提取所有相关信息
        user_auction_info_list = [
            {
                'paipin_id': auction.paipin_id,  # 拍卖唯一id
                'item_id': auction.item_id,  # 物品id
                'user_id': auction.user_id,  # 用户id
                'min_start_price': float(auction.min_start_price),  # 起拍价
                'quantity': auction.quantity,  # 物品数量
                'is_user_provided': auction.is_user_provided,  # 是否为用户提供的 true为用户
                'added_time': auction.added_time  # 提交拍品的时间
            }
            for auction in user_auctions
        ]
        return user_auction_info_list


async def get_admin_auction_info_item_id():
    """查询所有系统提供的拍卖物品"""
    async with AsyncSessionLocal() as session:
        query = select(AuctionWupin).where(AuctionWupin.is_user_provided == False)
        result = await session.execute(query)
        admin_auctions = result.scalars().all()

        # 提取所有系统商品id
        admin_auction_info_id = [auction.item_id for auction in admin_auctions]

        return admin_auction_info_id


async def get_admin_auction_info_min_start_price(auction_id=None):
    """查询所有系统提供的拍卖物品 id 和 底价(起拍价)"""
    async with AsyncSessionLocal() as session:
        query = select(AuctionWupin).where(AuctionWupin.is_user_provided == False)
        if auction_id is not None:
            query = query.where(AuctionWupin.item_id == auction_id)
        result = await session.execute(query)
        admin_auctions = result.scalars().all()

        if auction_id is not None:
            if admin_auctions:
                return [admin_auctions[0]]  # 返回包含单个拍卖品对象的列表
            else:
                return []  # 返回空列表
        else:
            # 提取所有系统商品id和底价
            admin_auction_info_min_start_price = [
                {
                    'item_id': auction.item_id,
                    'min_start_price': float(auction.min_start_price)
                }
                for auction in admin_auctions
            ]
            return admin_auction_info_min_start_price


auction_info = {}  # 临时储存拍卖会记录
# 定时任务
set_auction_by_scheduler = require("nonebot_plugin_apscheduler").scheduler


@set_auction_by_scheduler.scheduled_job("cron", hour=17, minute=0)
async def set_auction_by_scheduler_():
    """定时任务生成拍卖会"""
    global auction_info, auction_offer_flag, auction_offer_all_count, auction_offer_time_count, current_auction_index

    enabled_groups = sql_message.get_enabled_auction_groups()

    if auction_info:
        logger.opt(colors=True).info(f"<green>当前已存在一场拍卖会，已清除！</green>")
        auction_info = {}
        return

    if not enabled_groups:
        logger.opt(colors=True).info("<yellow>当前没有群聊启用拍卖会功能。</yellow>")
        return

    auction_items = []
    try:
        # 获取用户拍卖品信息
        user_auction_info_list = await get_user_auction_info()
        logger.opt(colors=True).info(f"<blue>获取用户拍卖品信息：{user_auction_info_list}</blue>")
        for user_auction_info in user_auction_info_list:
            auction_id = user_auction_info['paipin_id']  # 拍卖品唯一标识符
            item_id = user_auction_info['item_id']  # 物品id
            quantity = user_auction_info['quantity']  # 数量
            start_price = user_auction_info['min_start_price']  # 底价
            user_id = user_auction_info['user_id']  # 用户id
            auction_items.append(
                (auction_id, item_id, quantity, start_price, True, user_id))  # 使用 item_id 替换 auction_id

        # 获取系统拍卖品的物品id列表
        admin_auction_info = await get_admin_auction_info_min_start_price()
        logger.opt(colors=True).info(f"<blue>获取系统拍卖品信息：{admin_auction_info}</blue>")
        admin_auction_id_list = [info['item_id'] for info in admin_auction_info]
        auction_count = random.randint(3, 8)  # 随机挑选数个系统拍卖品
        auction_ids = random.sample(admin_auction_id_list, auction_count)
        for auction_id in auction_ids:
            item_info = items.get_data_by_item_id(auction_id)
            if item_info is None:
                logger.opt(colors=True).error(f"<red>1物品ID {auction_id} 对应的数据不存在。</red>")
                continue
            item_quantity = 1
            if item_info['type'] in ['神物', '丹药']:
                item_quantity = random.randint(1, 3)  # 如果是丹药的话随机挑1-3个
            admin_auction = await get_admin_auction_info_min_start_price(auction_id)
            if admin_auction:
                admin_auction_paipin_id = admin_auction[0].paipin_id if admin_auction else None
                start_price = float(admin_auction[0].min_start_price) if admin_auction else None
                if admin_auction_paipin_id and start_price:
                    auction_items.append((admin_auction_paipin_id, auction_id, item_quantity, start_price, False,
                                          None))  # 使用 admin_auction_paipin_id 替换 auction_id
        logger.opt(colors=True).info(f"<blue>拍卖品列表：{auction_items}</blue>")
    except LookupError:
        logger.opt(colors=True).info("<red>获取不到拍卖物品的信息，请检查配置文件！</red>")
        return

    random.shuffle(auction_items)  # 打乱拍卖品顺序

    logger.opt(colors=True).info("<red>大世界定时拍卖会出现了！！！，请管理员在这个时候不要重启机器人</red>")
    msg = f"大世界定时拍卖会出现了！！！\n"
    msg += f"请各位道友稍作准备，拍卖即将开始...\n"
    msg += f"本场拍卖会共有{len(auction_items)}件物品，将依次拍卖，分别是：\n"
    for idx, (paipin_id, item_id, item_quantity, start_price, is_user_auction, user_id) in enumerate(auction_items):
        item_info = items.get_data_by_item_id(item_id)
        if item_info is None:
            logger.opt(colors=True).error(f"<red>2物品ID {item_id} 对应的数据不存在。</red>")
            continue
        item_name = item_info['name']

        logger.opt(colors=True).info(f"<blue>处理拍卖品 {idx + 1}：{item_name} x {item_quantity}</blue>")

        if is_user_auction:
            owner_info = sql_message.get_user_info_with_id(user_id)
            owner_name = owner_info['user_name']
            msg += f"{idx + 1}号：{item_name}x{item_quantity}（由{owner_name}道友提供）\n"
        else:
            msg += f"{idx + 1}号：{item_name}x{item_quantity}（由拍卖场提供）\n"

    for gid in enabled_groups:
        bot = await assign_bot_group(group_id=gid)
        if bot is None:
            logger.opt(colors=True).error(f"<red>未找到群组 {gid} 对应的 bot 实例。</red>")
            continue
        try:
            await bot.send_group_msg(group_id=int(gid), message=msg)
        except ActionFailed:  # 发送群消息失败
            logger.opt(colors=True).error(f"<red>发送群消息失败，群组ID：{gid}</red>")
            continue

    auction_results = []  # 存储拍卖结果
    async with AsyncSessionLocal() as session:
        auction_id = await create_auction(session, enabled_groups, len(auction_items))
        for i, (paipin_id, item_id, item_quantity, start_price, is_user_auction, user_id) in enumerate(auction_items):
            item_info = items.get_data_by_item_id(item_id)
            if item_info is None:
                logger.opt(colors=True).error(f"<red>物品ID {item_id} 对应的数据不存在。</red>")
                continue
            item_name = item_info['name']

            # 将拍卖物品信息存入数据库
            auction_item = {
                "auction_id": auction_id,
                "paipin_id": paipin_id,
                "quantity": item_quantity,
                "start_price": start_price,
                "current_price": start_price,
                "is_user_auction": is_user_auction,
                "is_sold": False
            }
            stmt = insert(XiuxianAuctionItems).values(**auction_item)
            await session.execute(stmt)
            await session.commit()

            auction_info = {
                'id': paipin_id,
                'user_id': 0,
                'now_price': start_price,
                'name': item_name,
                'type': item_info['type'],
                'quantity': item_quantity,
                'start_time': datetime.now(),
                'group_id': 0
            }

            if i + 1 == len(auction_items):
                msg = f"最后一件拍卖品为：\n{get_auction_msg(item_id)}\n"
            else:
                msg = f"第{i + 1}件拍卖品为：\n{get_auction_msg(item_id)}\n"
            msg += f"\n底价为{start_price}，加价不少于{int(start_price * 0.05)}"
            msg += f"\n竞拍时间为:{AUCTIONSLEEPTIME}秒，请诸位道友发送 拍卖+金额 来进行拍卖吧！"

            if auction_info['quantity'] > 1:
                msg += f"\n注意：拍卖品共{auction_info['quantity']}件，最终价为{auction_info['quantity']} * 成交价。\n"

            if i + 1 < len(auction_items) and auction_items[i + 1]:
                next_item_info = items.get_data_by_item_id(auction_items[i + 1][1])
                if next_item_info:
                    next_item_name = next_item_info['name']
                    msg += f"\n下一件拍卖品为：{next_item_name}，请心仪的道友提前开始准备吧！"

            for gid in enabled_groups:
                bot = await assign_bot_group(group_id=gid)
                if bot is None:
                    logger.opt(colors=True).error(f"<red>未找到群组 {gid} 对应的 bot 实例。</red>")
                    continue
                try:
                    await bot.send_group_msg(group_id=int(gid), message=msg)
                except ActionFailed:  # 发送群消息失败
                    logger.opt(colors=True).error(f"<red>发送群消息失败，群组ID：{gid}</red>")
                    continue

            remaining_time = AUCTIONSLEEPTIME  # 第一轮定时
            while remaining_time > 0:
                await asyncio.sleep(10)
                remaining_time -= 10

            while auction_offer_flag:  # 有人拍卖
                if auction_offer_all_count == 0:
                    auction_offer_flag = False
                    break

                logger.opt(colors=True).info(
                    f"<green>有人拍卖，本次等待时间：{auction_offer_all_count * AUCTIONOFFERSLEEPTIME}秒</green>")
                first_time = auction_offer_all_count * AUCTIONOFFERSLEEPTIME
                auction_offer_all_count = 0
                auction_offer_flag = False
                await asyncio.sleep(first_time)
                logger.opt(colors=True).info(
                    f"<green>总计等待时间{auction_offer_time_count * AUCTIONOFFERSLEEPTIME}秒，当前拍卖标志：{auction_offer_flag}，本轮等待时间：{first_time}</green>")

            logger.opt(colors=True).info(
                f"<green>等待时间结束，总计等待时间{auction_offer_time_count * AUCTIONOFFERSLEEPTIME}秒</green>")
            if auction_info['user_id'] == 0:
                msg = f"很可惜，{auction_info['name']}流拍了\n"
                if i + 1 == len(auction_items):
                    msg += "本场拍卖会到此结束，开始整理拍卖会结果，感谢各位道友参与！"

                for gid in enabled_groups:
                    bot = await assign_bot_group(group_id=gid)
                    if bot is None:
                        logger.opt(colors=True).error(f"<red>未找到群组 {gid} 对应的 bot 实例。</red>")
                        continue
                    try:
                        await bot.send_group_msg(group_id=int(gid), message=msg)
                    except ActionFailed:  # 发送群消息失败
                        logger.opt(colors=True).error(f"<red>发送群消息失败，群组ID：{gid}</red>")
                        continue
                auction_results.append(
                    (paipin_id, None, auction_info['group_id'], auction_info['type'], auction_info['now_price'],
                     auction_info['quantity']))
                auction_info = {}
                continue

            user_info = sql_message.get_user_info_with_id(auction_info['user_id'])
            msg = f"(拍卖锤落下)！！！\n"
            msg += f"恭喜来自群{auction_info['group_id']}的{user_info['user_name']}道友成功拍下：{auction_info['type']}-{auction_info['name']}x{auction_info['quantity']}，将在拍卖会结算后送到您手中。\n"
            if i + 1 == len(auction_items):
                msg += "本场拍卖会到此结束，开始整理拍卖会结果，感谢各位道友参与！"

            auction_results.append((paipin_id, user_info['user_id'], auction_info['group_id'],
                                    auction_info['type'], auction_info['now_price'], auction_info['quantity']))
            auction_info = {}
            auction_offer_time_count = 0
            for gid in enabled_groups:
                bot = await assign_bot_group(group_id=gid)
                if bot is None:
                    logger.opt(colors=True).error(f"<red>未找到群组 {gid} 对应的 bot 实例。</red>")
                    continue
                try:
                    await bot.send_group_msg(group_id=int(gid), message=msg)
                except ActionFailed:  # 发送群消息失败
                    logger.opt(colors=True).error(f"<red>发送群消息失败，群组ID：{gid}</red>")
                    continue

            await asyncio.sleep(random.randint(5, 30))

    # 拍卖会结算
    logger.opt(colors=True).info("<green>大世界定时拍卖会结束了！！！</green>")
    end_msg = "本场拍卖会结束！感谢各位道友的参与。\n拍卖结果整理如下：\n"
    for idx, (paipin_id, user_id, group_id, item_type, final_price, quantity) in enumerate(auction_results):
        item_info = items.get_data_by_item_id(await get_item_id_by_paipin_id(paipin_id))
        if item_info is None:
            logger.opt(colors=True).error(f"<red>物品ID {paipin_id} 对应的数据不存在。</red>")
            continue
        item_name = item_info['name']
        final_user_info = sql_message.get_user_info_with_id(user_id)
        if user_id and (final_user_info['stone'] >= (int(final_price) * quantity)):
            sql_message.update_ls(user_id, int(final_price) * quantity, 2)
            sql_message.send_back(user_id, await get_item_id_by_paipin_id(paipin_id), item_name, item_type, quantity, 0)
            end_msg += f"{idx + 1}号拍卖品：{item_name}x{quantity}由群{group_id}的{final_user_info['user_name']}道友成功拍下\n"

            user_auction_info_list = await get_user_auction_info()
            if user_auction_info_list:
                # 确保 user_auction_info_list 是列表类型
                if isinstance(user_auction_info_list, list):
                    # 查找对应的卖家信息
                    seller_info = next((info for info in user_auction_info_list if info['paipin_id'] == paipin_id),
                                       None)
                    if seller_info:
                        seller_id = seller_info['user_id']
                        auction_earnings = int(final_price) * quantity * 0.7
                        sql_message.update_ls(seller_id, auction_earnings, 1)

            # 更新数据库中的拍卖物品信息
            async with AsyncSessionLocal() as session:
                stmt = (
                    update(XiuxianAuctionItems)
                    .where(XiuxianAuctionItems.paipin_id == paipin_id)
                    .values(is_sold=True, highest_bidder_id=user_id, current_price=final_price, bid_time=datetime.now())
                )
                await session.execute(stmt)
                await session.commit()

        else:
            end_msg += f"{idx + 1}号拍卖品：{item_name}x{quantity} - 流拍了\n"

    for gid in enabled_groups:
        bot = await assign_bot_group(group_id=gid)
        if bot is None:
            logger.opt(colors=True).error(f"<red>未找到群组 {gid} 对应的 bot 实例。</red>")
            continue
        try:
            await bot.send_group_msg(group_id=int(gid), message=end_msg)
        except ActionFailed:  # 发送群消息失败
            logger.opt(colors=True).error(f"<red>发送群消息失败，群组ID：{gid}</red>")
            continue

    # 归档拍卖记录
    try:
        await archive_auction(auction_id)
    except Exception as e:
        logger.opt(colors=True).error(f"<red>归档拍卖记录时发生错误：{e}</red>")

    return


# 创建拍卖会
async def create_auction(session: AsyncSession, groups: list, total_items: int) -> int:
    initiator_id = 1  # 假设系统发起
    is_system_auction = True
    start_time = datetime.now()
    status = 'ongoing'
    current_item_index = 0

    auction = {
        "initiator_id": initiator_id,
        "is_system_auction": is_system_auction,
        "start_time": start_time,
        "status": status,
        "total_items": total_items,
        "current_paipin_index": current_item_index
    }

    # 添加日志输出，检查 initiator_id
    logger.opt(colors=True).info(f"<blue>Creating auction with initiator_id: {initiator_id}</blue>")

    stmt = insert(XiuxianAuction).values(**auction)
    result = await session.execute(stmt)
    await session.commit()
    return result.inserted_primary_key[0]


# 归档拍卖记录
async def archive_auction(auction_id: int):
    async with AsyncSessionLocal() as session:
        try:
            # 归档拍卖会记录
            auction_query = select(XiuxianAuction).where(XiuxianAuction.auction_id == auction_id)
            auction_result = await session.execute(auction_query)
            auction_record = auction_result.scalar_one_or_none()

            if auction_record is None:
                logger.error(f"No auction record found with ID {auction_id}")
                return

            if auction_record.initiator_id is None or auction_record.initiator_id == "":
                logger.error(f"Initiator ID is empty or invalid for auction_id {auction_id}")
                await session.rollback()
                return

            # 归档拍卖基本信息
            auction_archive = {
                "auction_id": auction_record.auction_id,
                "initiator_id": auction_record.initiator_id,
                "is_system_auction": auction_record.is_system_auction,
                "start_time": auction_record.start_time,
                "end_time": datetime.now(),
                "status": auction_record.status,
                "total_items": auction_record.total_items,
                "current_paipin_index": auction_record.current_paipin_index,
                "archive_time": datetime.now()
            }
            auction_archive_stmt = insert(XiuxianAuctionArchive).values(**auction_archive)
            await session.execute(auction_archive_stmt)

            # 归档拍卖物品记录
            items_query = select(XiuxianAuctionItems).where(XiuxianAuctionItems.auction_id == auction_id)
            items_result = await session.execute(items_query)
            items_records = items_result.scalars().all()

            for item_record in items_records:
                # 确保 item_id 不为空
                if item_record.item_id is None:
                    logger.error(f"Item ID is None for paipin_id {item_record.paipin_id}")
                    continue

                item_archive = {
                    "auction_id": item_record.auction_id,
                    "paipin_id": item_record.paipin_id,
                    "quantity": item_record.quantity,
                    "start_price": item_record.start_price,
                    "current_price": item_record.current_price,
                    "highest_bidder_id": item_record.highest_bidder_id,
                    "bid_time": item_record.bid_time,
                    "is_sold": item_record.is_sold,
                    "is_user_auction": item_record.is_user_auction,
                    "archive_time": datetime.now(),
                    "item_id": item_record.item_id  # 添加 item_id
                }
                item_archive_stmt = insert(XiuxianAuctionItemsArchive).values(**item_archive)
                await session.execute(item_archive_stmt)

            # 归档出价记录
            bids_query = select(XiuxianAuctionBids).where(
                XiuxianAuctionBids.item_id.in_([r.item_id for r in items_records]))
            bids_result = await session.execute(bids_query)
            bids_records = bids_result.scalars().all()

            for bid_record in bids_records:
                bid_archive = {
                    "item_id": bid_record.item_id,
                    "user_id": bid_record.user_id,
                    "bid_amount": bid_record.bid_amount,
                    "bid_time": bid_record.bid_time,
                    "archive_time": datetime.now()
                }
                bid_archive_stmt = insert(XiuxianAuctionBidsArchive).values(**bid_archive)
                await session.execute(bid_archive_stmt)

            # 删除原表中的记录
            delete_auction_stmt = delete(XiuxianAuction).where(XiuxianAuction.auction_id == auction_id)
            delete_items_stmt = delete(XiuxianAuctionItems).where(XiuxianAuctionItems.auction_id == auction_id)
            delete_bids_stmt = delete(XiuxianAuctionBids).where(
                XiuxianAuctionBids.item_id.in_([r.item_id for r in items_records]))

            await session.execute(delete_auction_stmt)
            await session.execute(delete_items_stmt)
            await session.execute(delete_bids_stmt)

            await session.commit()

        except Exception as e:
            logger.error(f"<red>归档拍卖记录时发生错误：{e}</red>")
            await session.rollback()


auction_added = on_command("提交拍卖品", aliases={"拍卖品提交"}, priority=10, permission=GROUP, block=True)


@auction_added.handle(parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GROUP)])
async def auction_added_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """用户提交拍卖品"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    group_id = str(event.group_id)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    if not sql_message.is_auction_enabled(group_id):
        msg = '本群尚未开启拍卖会功能，请联系管理员开启！'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    user_id = user_info['user_id']
    args = args.extract_plain_text().strip().split()
    if len(args) < 1:
        msg = "请输入正确指令！例如：提交拍卖品 物品 可选参数为(金额 数量)"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    goods_name = args[0]
    price_str = args[1] if len(args) > 1 else "1"
    quantity_str = args[2] if len(args) > 2 else "1"

    back_msg = sql_message.get_back_msg(user_id)  # 获取背包信息
    if not back_msg:
        msg = "道友的背包空空如也！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    # 物品是否存在于背包中
    goods_details = next((back for back in back_msg if back['goods_name'] == goods_name), None)
    if not goods_details:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    try:
        price = int(price_str)
        quantity = int(quantity_str)
        if price <= 0 or quantity <= 0 or quantity > goods_details['goods_num']:
            raise ValueError("价格和数量必须为正数，或者超过了你拥有的数量!")
    except ValueError as e:
        msg = f"请输入正确的金额和数量: {str(e)}"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    if goods_details['goods_type'] == "装备" and int(goods_details['state']) == 1 and int(
            goods_details['goods_num']) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法提交！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    if int(goods_details['goods_num']) <= int(goods_details['bind_num']):
        msg = "该物品是绑定物品，无法提交！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    if goods_details['goods_type'] in ["聚灵旗", "炼丹炉"] and user_info['root'] != "器师":
        msg = "道友职业无法上架此类物品！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()

    # 将物品添加到拍卖数据库中
    async with AsyncSessionLocal() as session:
        try:
            new_auction_item = AuctionWupin(
                item_id=goods_details['goods_id'],
                user_id=user_id,
                min_start_price=price,
                quantity=quantity,
                is_user_provided=True,
                added_time=datetime.utcnow()
            )
            session.add(new_auction_item)
            await session.commit()
        except Exception as e:
            logger.error(f"插入拍卖物品时发生错误: {e}")
            await session.rollback()
            await bot.send_group_msg(group_id=int(send_group_id), message="提交拍卖品失败，请稍后再试。")
            await auction_added.finish()

    # 更新用户的背包信息
    sql_message.update_back_j(user_id, goods_details['goods_id'], num=-quantity)

    msg = f'''道友的拍卖品：{goods_name}成功提交!
底价：{price}枚灵石
数量：{quantity}
下次拍卖将优先拍卖道友的拍卖品！！！'''
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await auction_added.finish()


auction_withdraw = on_command("撤回拍卖品", aliases={"拍卖品撤回"}, priority=10, permission=GROUP, block=True)


@auction_withdraw.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def auction_withdraw_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """用户撤回拍卖品"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_withdraw.finish()

    group_id = str(event.group_id)
    if not sql_message.is_auction_enabled(group_id):
        msg = '本群尚未开启拍卖会功能，请联系管理员开启！'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_withdraw.finish()

    arg = args.extract_plain_text().strip()
    if not arg.isdigit():
        msg = f"请输入正确的编号"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_withdraw.finish()

    auction_index = int(arg) - 1

    # 查询当前用户的所有拍卖品
    async with AsyncSessionLocal() as session:
        try:
            query = select(AuctionWupin).where(AuctionWupin.user_id == user_info['user_id'])
            result = await session.execute(query)
            user_auctions = result.scalars().all()

            if not user_auctions:
                msg = f"您没有提交任何拍卖品！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await auction_withdraw.finish()

            if auction_index < 0 or auction_index >= len(user_auctions):
                msg = f"请输入正确的编号"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await auction_withdraw.finish()

            auction = user_auctions[auction_index]

            if auction.user_id != user_info['user_id']:
                msg = f"这不是您的拍卖品！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await auction_withdraw.finish()

            # 撤回拍卖品
            await session.delete(auction)
            await session.commit()

            # 更新用户的背包信息
            goods_details = sql_message.get_back_msg(user_info['user_id'])
            if not goods_details:
                msg = f"无法找到对应的物品信息！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await auction_withdraw.finish()

            goods = next((item for item in goods_details if item['goods_id'] == auction.item_id), None)
            if not goods:
                msg = f"无法找到对应的物品信息！"
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await auction_withdraw.finish()

            # 插入物品到背包
            sql_message.send_back(user_info['user_id'], auction.item_id, goods['goods_name'], goods['goods_type'],
                                  auction.quantity)

            msg = f"成功撤回拍卖品：{goods['goods_name']} x {auction.quantity}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)

            await auction_withdraw.finish()

        except Exception as e:
            logger.error(f"撤回拍卖品时发生错误: {e}")
            await session.rollback()
            await bot.send_group_msg(group_id=int(send_group_id), message="撤回拍卖品失败，请稍后再试。")
            await auction_withdraw.finish()


offer_auction = on_command("拍卖", priority=5, permission=GROUP, block=True)


@offer_auction.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GLOBAL)])
async def offer_auction_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """拍卖"""
    group_id = str(event.group_id)
    bot = await assign_bot_group(group_id=group_id)
    isUser, user_info, msg = check_user(event)
    global auction_info, auction_offer_flag, auction_offer_all_count, auction_offer_time_count

    if not isUser:
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()

    if not sql_message.is_auction_enabled(group_id):
        msg = '本群尚未开启拍卖会功能，请联系管理员开启！'
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()

    if not auction_info:
        msg = "当前不存在拍卖会，请等待拍卖会开启！"
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()

    enabled_groups = sql_message.get_enabled_auction_groups()
    price = args.extract_plain_text().strip()
    try:
        price = int(price)
    except ValueError:
        msg = "请发送正确的灵石数量"
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()

    now_price = auction_info['now_price']
    min_price = int(now_price * 0.05)  # 最低加价5%
    if price <= 0 or price <= auction_info['now_price'] or price > user_info['stone']:
        msg = "走开走开,灵石不够，别捣乱！小心清空你灵石捏"
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()
    if price - now_price < min_price:
        msg = f"拍卖不得少于当前竞拍价的5%，目前最少加价为：{min_price}灵石，目前竞拍价为：{now_price}!"
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()

    auction_offer_flag = True  # 有人拍卖
    auction_offer_time_count += 1
    auction_offer_all_count += 1

    # 使用当前拍卖品的 paipin_id
    paipin_id = auction_info['id']

    auction_info['user_id'] = user_info['user_id']
    auction_info['now_price'] = price
    auction_info['group_id'] = group_id
    auction_info['paipin_id'] = paipin_id

    logger.opt(colors=True).info(f"<green>{user_info['user_name']}({auction_info['user_id']})竞价了！！</green>")

    now_time = datetime.now()
    dif_time = (now_time - auction_info['start_time']).total_seconds()
    remaining_time = int(AUCTIONSLEEPTIME - dif_time + AUCTIONOFFERSLEEPTIME * auction_offer_time_count)
    msg = (
            f"来自群{group_id}的{user_info['user_name']}道友拍卖：{price}枚灵石！" +
            f"竞拍时间增加：{AUCTIONOFFERSLEEPTIME}秒，竞拍剩余时间：{remaining_time}秒"
    )

    async with AsyncSessionLocal() as session:
        try:
            # 更新当前拍卖品的信息
            stmt = (
                update(XiuxianAuctionItems)
                .where(XiuxianAuctionItems.paipin_id == paipin_id)
                .values(current_price=price, highest_bidder_id=user_info['user_id'], bid_time=datetime.now())
            )
            await session.execute(stmt)

            # 插入新的出价记录
            bid = {
                "item_id": paipin_id,  # 使用 paipin_id 代替 item_id
                "user_id": user_info['user_id'],
                "bid_amount": price,
                "bid_time": datetime.now()
            }
            stmt = insert(XiuxianAuctionBids).values(**bid)
            await session.execute(stmt)

            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error in offer_auction_: {e}")
            msg = "数据库操作失败，请稍后再试！"
            await bot.send_group_msg(group_id=int(group_id), message=msg)
            await offer_auction.finish()

    error_msg = None
    for gid in enabled_groups:
        bot = await assign_bot_group(group_id=gid)
        try:
            await bot.send_group_msg(group_id=int(gid), message=msg)
        except ActionFailed:
            error_msg = f"消息发送失败，可能被风控，当前拍卖物品金额为：{auction_info['now_price']}！"
            continue
    logger.opt(colors=True).info(
        f"<green>有人拍卖，拍卖标志：{auction_offer_flag}，当前等待时间：{auction_offer_all_count * AUCTIONOFFERSLEEPTIME}，总计拍卖次数：{auction_offer_time_count}</green>")
    if error_msg is None:
        await offer_auction.finish()
    else:
        msg = error_msg
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await offer_auction.finish()


auction_view = on_command("拍卖品查看", aliases={"查看拍卖品"}, priority=8, permission=GROUP, block=True)


@auction_view.handle(parameterless=[Cooldown(at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def auction_view_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看拍卖会物品"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    group_id = str(event.group_id)

    if not isUser:
        logger.error(f"用户未注册: {event.user_id}")
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_view.finish()
        return

    if not sql_message.is_auction_enabled(group_id):
        logger.error(f"拍卖会功能未开启: {group_id}")
        msg = '本群尚未开启拍卖会功能，请联系管理员开启！'
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        await auction_view.finish()
        return

    # 查询所有用户提交的拍卖品
    async with AsyncSessionLocal() as session:
        # 构建查询语句
        query = select(AuctionWupin).where(
            AuctionWupin.is_user_provided == True
        )

        # 执行查询
        result = await session.execute(query)
        auctions = result.scalars().all()

        if not auctions:
            logger.info("当前没有用户提交的拍卖品")
            msg = "当前没有用户提交的拍卖品！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await auction_view.finish()
            return

        # 构建拍卖品信息列表
        auction_list_msg = "拍卖会物品列表:\n"

        for idx, auction in enumerate(auctions):
            # 获取用户信息
            user_info = sql_message.get_user_info_with_id(auction.user_id)
            if user_info is None:
                user_info = {'user_name': '未知用户'}
                logger.warning(f"用户信息未找到: {auction.user_id}")

            # 获取物品信息
            items_info = items.get_data_by_item_id(auction.item_id)
            if items_info is None:
                items_info = {'name': '未知物品', 'type': '未知类型'}
                logger.warning(f"物品信息未找到: {auction.item_id}")

            auction_list_msg += f"编号: {idx + 1}\n"
            auction_list_msg += f"物品名称: {items_info.get('name', '未知物品')}\n"
            auction_list_msg += f"物品类型: {items_info.get('type', '未知类型')}\n"
            auction_list_msg += f"所有者: {user_info.get('user_name', '未知用户')}\n"
            auction_list_msg += f"底价: {int(auction.min_start_price)} 枚灵石\n"
            auction_list_msg += f"数量: {auction.quantity}\n"
            auction_list_msg += "☆------------------------------☆\n"

        logger.info("发送拍卖品列表")
        await bot.send_group_msg(group_id=int(send_group_id), message=auction_list_msg)
        await auction_view.finish()
