import httpx
from nonebot.log import logger
import asyncio
import hashlib
import os
from PIL import Image
import io
from pathlib import Path


async def download_url(url: str) -> bytes:
    # 使用异步客户端发起请求
    async with httpx.AsyncClient() as client:
        # 尝试最多三次下载
        for i in range(3):
            try:
                # 异步发起 GET 请求
                resp = await client.get(url, timeout=20)
                # 检查响应状态码是否为 200 OK
                resp.raise_for_status()
                # 返回响应内容的字节形式
                return resp.content
            except Exception as e:
                # 记录下载错误信息，并等待 3 秒后重试
                logger.opt(colors=True).warning(f"<red>下载错误 {url}, 重试 {i}/3: {e}</red>")
                await asyncio.sleep(3)
    # 如果三次都失败，抛出异常
    raise Exception(f"{url} 下载失败！")


async def download_avatar(user_id: str) -> bytes:
    """下载用户头像"""
    # 构造头像 URL
    url = f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    # 尝试下载头像
    data = await download_url(url)

    # 检查 MD5 校验是否通过
    if hashlib.md5(data).hexdigest() == "acef72340ac0e914090bd35799f5594e":
        # 如果校验失败，尝试下载另一个尺寸的头像
        url = f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100"
        data = await download_url(url)

    # 返回头像数据
    return data


async def get_avatar_by_user_id_and_save(user_id):
    """下载用户头像并保存"""
    # 将 user_id 转换为字符串
    user_id = str(user_id)

    # 定义路径变量
    PLAYERSDATA = Path() / "data" / "xiuxian" / "players"
    USER_AVATAR_PATH = PLAYERSDATA / user_id / 'AVATAR.png'
    INIT_PATH = Path() / "data" / "xiuxian" / "info_img" / "init.png"

    try:
        # 记录开始下载头像的日志
        logger.opt(colors=True).info(f"<green>开始下载用户头像！</green>")

        # 下载头像数据
        image_bytes = await download_avatar(user_id)

        # 使用 PIL 库打开图像，并调整大小和转换为 RGBA 模式
        im = Image.open(io.BytesIO(image_bytes)).resize((280, 280)).convert("RGBA")

        # 如果用户目录不存在，则创建
        if not os.path.exists(PLAYERSDATA / user_id):
            os.makedirs(PLAYERSDATA / user_id)

        # 保存图像到本地
        im.save(USER_AVATAR_PATH, "PNG")
    except Exception as e:
        # 如果下载或保存过程中出现错误，则记录错误信息
        logger.opt(colors=True).error(f"<red>获取头像出错,{e}</red>")

        # 使用默认图片
        im = Image.open(INIT_PATH).resize((280, 280)).convert("RGBA")

    # 返回处理后的图像
    return im


