"""键位配置模块（Airtest 版本）。

在进入游戏大厅后配置自定义键位布局：
1. 点击键位编辑按钮
2. 点击键位位置
3. 点击保存
4. 点击"暂不更改"（不存在则跳过）

替代旧 keybind_config.py（依赖 Navigator 和 calibrated_coords.json）。
"""

from __future__ import annotations

import time

from config import CLICK_INTERVAL
from logger import get_logger

log = get_logger()

# ---- 模板名 ----
KEYBIND_EDIT_BTN = "keybind_edit.png"
KEYBIND_POS_TARGET = "keybind_pos_target.png"
KEYBIND_SAVE_BTN = "keybind_save.png"
KEYBIND_SKIP_BTN = "keybind_skip.png"

# ---- 重试 ----
MAX_RETRIES = 3


def configure_keybinding(device) -> bool:
    """配置键位布局。

    Args:
        device: AirtestDevice 实例。

    Returns:
        bool: 全部步骤成功返回 True。
    """
    log.info("开始键位配置...")

    # ---- Step 1: 点击键位编辑按钮 ----
    if not device.click_template(KEYBIND_EDIT_BTN, timeout=5.0):
        log.error("找不到键位编辑按钮")
        return False
    log.info("已点击键位编辑按钮")
    time.sleep(CLICK_INTERVAL)

    # ---- Step 2: 点击键位位置 ----
    if not device.click_template(KEYBIND_POS_TARGET, timeout=5.0):
        log.error("找不到键位位置模板")
        return False
    log.info("已点击键位位置")
    time.sleep(CLICK_INTERVAL)

    # ---- Step 3: 点击保存 ----
    if not device.click_template(KEYBIND_SAVE_BTN, timeout=5.0):
        log.error("找不到保存键位按钮")
        return False
    log.info("已点击保存键位按钮")
    time.sleep(CLICK_INTERVAL)

    # ---- Step 4: 点击"暂不更改"（不存在则跳过） ----
    if device.exists_template(KEYBIND_SKIP_BTN, threshold=0.7):
        if device.click_template(KEYBIND_SKIP_BTN, timeout=3.0, threshold=0.55):
            log.info("已点击暂不更改按钮")
            time.sleep(CLICK_INTERVAL)
    else:
        log.info("未检测到暂不更改按钮，跳过")

    log.info("键位配置完成")
    return True
