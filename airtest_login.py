"""模拟器内王者荣耀 QQ 授权登录 (OCR 版本)。

替代旧 login.py（浏览器网页扫码/手动登录）和旧的模板匹配登录。

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

# 登录流程 OCR 关键词
LOGIN_QQ_KEYWORD = "QQ登录"       # QQ 登录按钮
QQ_AUTH_KEYWORD = "授权"           # QQ 授权按钮
POPUP_CLOSE_KEYWORDS = ["关闭", "确定"]  # 公告弹窗关闭
MAIN_HALL_KEYWORDS = ["开始游戏", "大厅"]  # 验证已进入大厅


def game_login(device, timeout: float = 120.0) -> bool:
    """模拟器内王者荣耀 QQ 授权登录 (OCR)。

    Args:
        device: AirtestDevice 实例。
        timeout: 登录总超时 (秒)。

    Returns:
        bool: 成功进入游戏大厅返回 True。
    """
    log.info("开始游戏登录（Android 模拟器 / QQ 授权 / OCR）")

    # 1. 启动王者荣耀
    log.info(f"启动王者荣耀: {HOK_PACKAGE}")
    device.start_app(HOK_PACKAGE)
    time.sleep(5)  # 等待游戏冷启动

    # 2. 等待 QQ 登录按钮并点击
    log.info("等待 QQ 登录按钮 (OCR)...")
    if not device.click_text(LOGIN_QQ_KEYWORD, timeout=60.0, threshold=0.8):
        log.warning("未检测到 QQ 登录按钮，可能已自动登录")
    else:
        time.sleep(3)

    # 3. QQ 授权按钮
    log.info("等待 QQ 授权按钮 (OCR)...")
    if device.exists_text(QQ_AUTH_KEYWORD, threshold=0.8):
        if not device.click_text(QQ_AUTH_KEYWORD, timeout=15.0, threshold=0.8):
            log.error("QQ 授权失败")
            return False
        time.sleep(3)
    else:
        log.info("未检测到 QQ 授权按钮，可能已授权")

    # 4. 关闭公告弹窗（可能存在多层公告）
    log.info("关闭公告弹窗 (OCR)...")
    for _ in range(5):
        closed_any = False
        for kw in POPUP_CLOSE_KEYWORDS:
            if device.exists_text(kw, threshold=0.8):
                device.click_text(kw, timeout=3.0, threshold=0.8)
                closed_any = True
                time.sleep(1.5)
                break
        if not closed_any:
            break

    # 5. 验证进入游戏大厅
    log.info("验证进入游戏大厅 (OCR)...")
    deadline = time.time() + 30
    while time.time() < deadline:
        for kw in MAIN_HALL_KEYWORDS:
            if device.wait_text(kw, timeout=3.0, threshold=0.8):
                log.info(f"✅ 已进入游戏大厅 (检测到 '{kw}')")
                return True
        # 仍可能有弹窗
        for kw in POPUP_CLOSE_KEYWORDS:
            if device.exists_text(kw, threshold=0.8):
                device.click_text(kw, timeout=3.0, threshold=0.8)
        time.sleep(2)

    log.error("登录超时：未检测到游戏大厅")
    return False
