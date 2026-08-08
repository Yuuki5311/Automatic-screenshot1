"""模拟器内王者荣耀 QQ 授权登录 (OCR 版本)。

替代旧 login.py（浏览器网页扫码/手动登录）和旧的模板匹配登录。

前置条件：
    1. MuMu 模拟器已安装 QQ 并保持登录
    2. QQ 已首次授权王者荣耀
    3. 王者荣耀 APK 已安装

流程：
    启动王者荣耀 → 等待 10s → 轮询 3 轮(开始游戏 → QQ登录) → QQ 授权 → 关闭公告 → 确认大厅
    每轮先查「开始游戏」3s，再查「QQ登录」3s，3 轮都失败则报错退出
"""

from __future__ import annotations

import time

from airtest.core.api import touch

from config import CLICK_INTERVAL
from logger import get_logger

log = get_logger()

# 王者荣耀包名
HOK_PACKAGE = "com.tencent.tmgp.sgame"

# 登录流程 OCR 关键词
LOGIN_QQ_KEYWORD = "QQ登录"       # QQ 登录按钮
QQ_AUTH_KEYWORD = "授权"           # QQ 授权按钮
POPUP_CLOSE_KEYWORDS = ["关闭", "确定"]  # 公告弹窗关闭
MAIN_HALL_KEYWORD = "定制"  # 主界面才有此按钮，用于验证已进入大厅


def _close_popup_if_present(device) -> bool:
    """检测并关闭弹窗（模板 + OCR）。返回是否关闭了弹窗。"""
    # 模板只在右上半屏搜索 (x: 右半, y: 上半)，避免匹配到左边假目标
    pos = device.find_template("popup_close.png", threshold=0.7,
                               bounds=(960, 0, 960, 540))
    if pos is not None:
        log.info(f"检测到弹窗关闭按钮 (模板) @ ({pos[0]}, {pos[1]})，关闭中...")
        touch(pos)
        time.sleep(1.5)
        return True
    for kw in POPUP_CLOSE_KEYWORDS:
        if device.exists_text(kw, threshold=0.8):
            log.info(f"检测到弹窗关键词: '{kw}'，关闭中...")
            device.click_text(kw, timeout=3.0, threshold=0.8)
            time.sleep(1.5)
            return True
    return False


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
    time.sleep(10)  # 等待游戏冷启动

    # 2. 轮询检测「开始游戏」或「QQ登录」（3 轮，每轮各 3 秒）
    ENTER_GAME_KEYWORD = "开始游戏"
    MAX_ROUNDS = 3
    ROUND_TIMEOUT = 3.0

    for round_num in range(1, MAX_ROUNDS + 1):
        log.info(f"第 {round_num}/{MAX_ROUNDS} 轮检测...")

        # 每轮先扫弹窗，避免弹窗遮挡按钮
        _close_popup_if_present(device)

        # 2a. 先查「开始游戏」
        if device.wait_text(ENTER_GAME_KEYWORD, timeout=ROUND_TIMEOUT, threshold=0.8):
            log.info("检测到「进入游戏」按钮，直接进入")
            device.click_text(ENTER_GAME_KEYWORD, timeout=3.0, threshold=0.8)
            time.sleep(3)
            break  # 跳过 QQ 登录流程

        # 2b. 再查「QQ登录」
        if device.wait_text(LOGIN_QQ_KEYWORD, timeout=ROUND_TIMEOUT, threshold=0.8):
            log.info("检测到「QQ登录」按钮，走 QQ 登录流程")
            device.click_text(LOGIN_QQ_KEYWORD, timeout=3.0, threshold=0.8)
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
            break
    else:
        # 3 轮都没检测到任何按钮
        log.error("登录失败：3 轮检测未发现「进入游戏」或「QQ登录」按钮")
        return False

    # 5. 关闭公告弹窗（可能存在多层公告，弹窗可能延迟出现）
    log.info("关闭公告弹窗 (模板 + OCR)...")
    deadline = time.time() + 20
    while time.time() < deadline:
        if _close_popup_if_present(device):
            continue
        time.sleep(2)  # 没找到弹窗，等 2s 再试

    # 6. 验证进入游戏大厅（检测主界面独有的「定制」按钮）
    log.info("验证进入游戏大厅 (检测「定制」)...")
    deadline = time.time() + 30
    while time.time() < deadline:
        if device.wait_text(MAIN_HALL_KEYWORD, timeout=3.0, threshold=0.8):
            log.info(f"✅ 已进入游戏大厅 (检测到「{MAIN_HALL_KEYWORD}」)")
            return True
        # 仍可能有弹窗
        if _close_popup_if_present(device):
            continue
        time.sleep(2)

    log.error("登录超时：未检测到游戏大厅")
    return False
