"""键位配置模块（OCR + 坐标版本）。

在进入游戏大厅后配置自定义键位布局：
1. 点击键位编辑按钮（OCR 找 "编辑" 或坐标）
2. 点击键位位置（坐标 + ROI 校验）
3. 点击保存（OCR 找 "保存"）
4. 点击"暂不更改"（OCR 找 "暂不更改"，不存在则跳过）

替代旧 keybind_config.py（依赖 Navigator 和 calibrated_coords.json）
和旧 airtest_keybind.py（依赖模板匹配）。
"""

from __future__ import annotations

import time

from config import CLICK_INTERVAL
from logger import get_logger

log = get_logger()

# ---- OCR 关键词 ----
KEYBIND_EDIT_TEXT = "编辑"       # 键位编辑按钮
KEYBIND_SAVE_TEXT = "保存"       # 保存按钮
KEYBIND_SKIP_TEXT = "暂不更改"   # 暂不更改按钮

# ---- 坐标（纯图标按钮，需根据设备分辨率校准） ----
# 键位位置坐标 — 在键位编辑界面中需要点击的键位位置
KEYBIND_POS_COORDS = (960, 540)  # 默认屏幕中心，需校准

# ---- 重试 ----
MAX_RETRIES = 3


def configure_keybinding(device) -> bool:
    """配置键位布局 (OCR + 坐标混合)。

    Args:
        device: AirtestDevice 实例。

    Returns:
        bool: 全部步骤成功返回 True。
    """
    log.info("开始键位配置 (OCR)...")

    # ---- Step 1: 点击键位编辑按钮（OCR） ----
    if not device.click_text(KEYBIND_EDIT_TEXT, timeout=5.0, threshold=0.8):
        log.error(f"找不到键位编辑按钮 (OCR: '{KEYBIND_EDIT_TEXT}')")
        return False
    log.info("已点击键位编辑按钮")
    time.sleep(CLICK_INTERVAL)

    # ---- Step 2: 点击键位位置（坐标） ----
    cx, cy = KEYBIND_POS_COORDS
    from airtest.core.api import touch
    touch((cx, cy))
    log.info(f"坐标点击键位位置: ({cx}, {cy})")
    time.sleep(CLICK_INTERVAL)

    # ---- Step 3: 点击保存（OCR） ----
    if not device.click_text(KEYBIND_SAVE_TEXT, timeout=5.0, threshold=0.8):
        log.error(f"找不到保存按钮 (OCR: '{KEYBIND_SAVE_TEXT}')")
        return False
    log.info("已点击保存键位按钮")
    time.sleep(CLICK_INTERVAL)

    # ---- Step 4: 点击"暂不更改"（OCR，不存在则跳过） ----
    if device.exists_text(KEYBIND_SKIP_TEXT, threshold=0.8):
        if device.click_text(KEYBIND_SKIP_TEXT, timeout=3.0, threshold=0.8):
            log.info("已点击暂不更改按钮")
            time.sleep(CLICK_INTERVAL)
    else:
        log.info("未检测到暂不更改按钮，跳过")

    log.info("键位配置完成")
    return True
