"""模拟器内王者荣耀 QQ 授权登录。

替代旧 login.py（浏览器网页扫码/手动登录）。

前置条件：
    1. MuMu 模拟器已安装 QQ 并保持登录
    2. QQ 已首次授权王者荣耀
    3. 王者荣耀 APK 已安装

流程：
    启动王者荣耀 → 等待加载 → 点击 QQ 登录 → QQ 授权 → 关闭公告 → 确认大厅
"""

from __future__ import annotations

import time

from config import CLICK_INTERVAL
from logger import get_logger

log = get_logger()

# 王者荣耀包名
HOK_PACKAGE = "com.tencent.tmgp.sgame"

# 登录流程模板
LOGIN_QQ_BTN = "login_qq_btn.png"
QQ_AUTH_BTN = "qq_auth_btn.png"
POPUP_CLOSE = "popup_close.png"
MAIN_HALL_AVATAR = "main_hall_avatar.png"
GAME_MAIN = "game_main.png"


def game_login(device, timeout: float = 120.0) -> bool:
    """模拟器内王者荣耀 QQ 授权登录。

    Args:
        device: AirtestDevice 实例。
        timeout: 登录总超时 (秒)。

    Returns:
        bool: 成功进入游戏大厅返回 True。
    """
    log.info("开始游戏登录（Android 模拟器 / QQ 授权）")

    # 1. 启动王者荣耀
    log.info(f"启动王者荣耀: {HOK_PACKAGE}")
    device.start_app(HOK_PACKAGE)
    time.sleep(5)  # 等待游戏冷启动

    # 2. 等待 QQ 登录按钮并点击
    log.info("等待 QQ 登录按钮...")
    if not device.click_template(LOGIN_QQ_BTN, timeout=60.0, threshold=0.7):
        log.warning("未检测到 QQ 登录按钮，可能已自动登录")
    else:
        time.sleep(3)

    # 3. QQ 授权按钮（如果模拟器 QQ 已登录，只需点授权）
    log.info("等待 QQ 授权按钮...")
    if device.exists_template(QQ_AUTH_BTN, threshold=0.7):
        if not device.click_template(QQ_AUTH_BTN, timeout=15.0, threshold=0.7):
            log.error("QQ 授权失败")
            return False
        time.sleep(3)
    else:
        log.info("未检测到 QQ 授权按钮，可能已授权")

    # 4. 关闭公告弹窗（可能存在多层公告）
    log.info("关闭公告弹窗...")
    for _ in range(5):
        if device.exists_template(POPUP_CLOSE, threshold=0.7):
            device.click_template(POPUP_CLOSE, timeout=3.0, threshold=0.7)
            time.sleep(1.5)
        else:
            break

    # 5. 验证进入游戏大厅
    log.info("验证进入游戏大厅...")
    deadline = time.time() + 30
    while time.time() < deadline:
        if device.wait_template(GAME_MAIN, timeout=3.0, threshold=0.7):
            log.info("✅ 已进入游戏大厅")
            return True
        if device.exists_template(MAIN_HALL_AVATAR, threshold=0.7):
            log.info("✅ 检测到大厅头像，登录成功")
            return True
        # 仍可能有弹窗
        if device.exists_template(POPUP_CLOSE, threshold=0.7):
            device.click_template(POPUP_CLOSE, timeout=3.0, threshold=0.7)
        time.sleep(2)

    log.error("登录超时：未检测到游戏大厅")
    return False
