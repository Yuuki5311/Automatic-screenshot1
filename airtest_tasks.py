"""截图任务定义与执行引擎。

数据类定义截图工作流，run_screenshot_loop 线性执行。
替代旧 ui_loop.py 的 FSM 感知循环和 gui/app.py 的 screenshot_tasks 列表。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Union

from airtest.core.api import touch

from config import CLICK_INTERVAL, MAX_RETRIES, SHOT_DELAY
from logger import get_logger

log = get_logger()

# ------------------------------------------------------------------
# Action 数据类
# ------------------------------------------------------------------


@dataclass
class ClickTemplate:
    """模板点击操作。"""
    template: str
    desc: str = ""
    timeout: float = 10.0
    threshold: float = 0.7
    bounds: tuple = ()  # (x, y, w, h) 搜索区域，空则全屏


@dataclass
class ClickText:
    """OCR 文字点击操作 — 替代 ClickTemplate，无需模板图。"""
    text: str
    desc: str = ""
    timeout: float = 10.0
    threshold: float = 0.8


@dataclass
class ClickCoord:
    """坐标点击操作（极少场景：点击位置不固定的元素）。

    Attributes:
        x: 点击横坐标。
        y: 点击纵坐标。
        desc: 操作描述。
        verify_template: 点击后等待出现的模板（如加载缓慢的目标页）。
        verify_text: 点击后等待出现的 OCR 文字（与 verify_template 二选一）。
        verify_timeout: 等待超时秒数。
    """
    x: int
    y: int
    desc: str = ""
    verify_template: str = ""
    verify_text: str = ""
    verify_timeout: float = 30.0


@dataclass
class SwipeAction:
    """滑动操作。"""
    direction: str          # "up" | "down" | "left" | "right"
    desc: str = ""
    duration: float = 0.3


@dataclass
class GuardAction:
    """条件弹窗关闭。如果弹窗出现就关闭，不存在就跳过（对应旧 __guard__）。"""
    template: str           # 检测弹窗的模板
    dismiss_template: str   # 关闭弹窗的模板
    desc: str = ""


# Union type for task setup actions
Action = Union[ClickTemplate, ClickText, ClickCoord, SwipeAction, GuardAction]


@dataclass
class ScreenshotTask:
    """单个截图任务。

    Attributes:
        name: 任务名（用作截图文件名）。
        setup: 前置操作序列。
        shot_delay: 前置操作完成后等待渲染的秒数。
        teardown_back: 截图后按几次返回键退出。
    """
    name: str
    setup: list[Action] = field(default_factory=list)
    shot_delay: float = SHOT_DELAY
    teardown_back: int = 0


# ------------------------------------------------------------------
# 弹窗模板列表（每轮截图后快速扫描）
# ------------------------------------------------------------------

POPUP_KEYWORDS = ["关闭", "确定", "取消"]


# ------------------------------------------------------------------
# Action 执行器
# ------------------------------------------------------------------

def execute_action(device, action: Action) -> bool:
    """执行单个 Action。返回 True 表示成功。

    Args:
        device: AirtestDevice 实例。
        action: ClickTemplate / ClickCoord / SwipeAction / GuardAction。
    """
    if isinstance(action, ClickTemplate):
        return _execute_click_template(device, action)

    elif isinstance(action, ClickText):
        return _execute_click_text(device, action)

    elif isinstance(action, ClickCoord):
        return _execute_click_coord(device, action)

    elif isinstance(action, SwipeAction):
        return _execute_swipe(device, action)

    elif isinstance(action, GuardAction):
        return _execute_guard(device, action)

    else:
        log.warning(f"未知 Action 类型: {type(action)}")
        return False


def _execute_click_template(device, action: ClickTemplate) -> bool:
    """带重试的模板点击。有 bounds 时走 find_template+坐标点击，无 bounds 走 Airtest 原生路径。"""
    for attempt in range(1, MAX_RETRIES + 1):
        if action.bounds:
            # 区域搜索 → 坐标点击 (与 popup_close 同路径)
            bounds = action.bounds if len(action.bounds) == 4 else None
            pos = device.find_template(
                action.template,
                threshold=action.threshold,
                bounds=bounds,
            )
            if pos is not None:
                touch(pos)
                log.info(f"点击模板 {action.template} @ ({pos[0]}, {pos[1]})")
                time.sleep(CLICK_INTERVAL)
                return True
        else:
            # 全屏搜索，Airtest 原生路径
            if device.click_template(
                action.template,
                timeout=action.timeout,
                threshold=action.threshold,
            ):
                time.sleep(CLICK_INTERVAL)
                return True
        if attempt < MAX_RETRIES:
            log.warning(f"重试 {action.desc or action.template} ({attempt}/{MAX_RETRIES})")
            time.sleep(1)
    log.error(f"点击失败 ({MAX_RETRIES}次重试): {action.desc or action.template}")
    return False


def _execute_click_text(device, action: ClickText) -> bool:
    """带重试的 OCR 文字点击。"""
    for attempt in range(1, MAX_RETRIES + 1):
        if device.click_text(
            action.text,
            timeout=action.timeout,
            threshold=action.threshold,
        ):
            time.sleep(CLICK_INTERVAL)
            return True
        if attempt < MAX_RETRIES:
            log.warning(f"重试 OCR 点击 {action.desc or action.text} ({attempt}/{MAX_RETRIES})")
            time.sleep(1)
    log.error(f"OCR 点击失败 ({MAX_RETRIES}次重试): {action.desc or action.text}")
    return False


def _execute_click_coord(device, action: ClickCoord) -> bool:
    """坐标点击。使用 Airtest touch() 坐标模式。"""
    touch((action.x, action.y))
    log.info(f"坐标点击: ({action.x}, {action.y}) {action.desc}")
    time.sleep(CLICK_INTERVAL)
    if action.verify_template:
        log.info(f"等待验证模板: {action.verify_template} (最多 {action.verify_timeout}s)")
        if not device.wait_template(action.verify_template, timeout=action.verify_timeout):
            log.error(f"验证模板未出现 ({action.verify_timeout}s): {action.verify_template}")
            return False
    if action.verify_text:
        log.info(f"等待验证文字: '{action.verify_text}' (最多 {action.verify_timeout}s)")
        if not device.wait_text(action.verify_text, timeout=action.verify_timeout):
            log.error(f"验证文字未出现 ({action.verify_timeout}s): '{action.verify_text}'")
            return False
    return True


def _execute_swipe(device, action: SwipeAction) -> bool:
    """滑动操作。"""
    device.swipe_screen(action.direction, duration=action.duration)
    time.sleep(CLICK_INTERVAL)
    return True


def _execute_guard(device, action: GuardAction) -> bool:
    """条件弹窗关闭：存在则关闭，不存在则跳过。"""
    if device.exists_template(action.template, threshold=0.7):
        log.info(f"检测到弹窗 {action.desc or action.template}，关闭中...")
        success = device.click_template(action.dismiss_template, timeout=5.0)
        if success:
            log.info(f"弹窗已关闭: {action.desc or action.template}")
            time.sleep(CLICK_INTERVAL)
        return success
    else:
        log.debug(f"未检测到弹窗，跳过: {action.desc or action.template}")
        return True  # 不存在不算失败


# ------------------------------------------------------------------
# 弹窗扫描
# ------------------------------------------------------------------

def scan_popups(device) -> int:
    """扫描并关闭已知弹窗。优先用模板匹配，再 OCR 兜底。返回关闭的弹窗数量。"""
    closed = 0

    # 1. 模板匹配: popup_close.png → 只搜右上半屏，坐标点击
    pos = device.find_template("popup_close.png", threshold=0.7,
                               bounds=(960, 0, 960, 540))
    if pos is not None:
        log.info(f"扫描到弹窗关闭按钮 (模板) @ ({pos[0]}, {pos[1]})")
        touch(pos)
        closed += 1
        time.sleep(CLICK_INTERVAL)

    # 2. OCR 兜底: 关闭/确定/取消
    for keyword in POPUP_KEYWORDS:
        if device.exists_text(keyword, threshold=0.8):
            log.info(f"扫描到弹窗关键词: '{keyword}'")
            if device.click_text(keyword, timeout=3.0, threshold=0.8):
                closed += 1
                time.sleep(CLICK_INTERVAL)
    return closed


# ------------------------------------------------------------------
# 截图执行循环
# ------------------------------------------------------------------

def run_screenshot_loop(
    device,
    tasks: list[ScreenshotTask],
    on_progress: Callable[[int, int], None] | None = None,
    on_log: Callable[[str, str], None] | None = None,
) -> int:
    """执行截图任务循环。

    Args:
        device: AirtestDevice 实例。
        tasks: 截图任务列表。
        on_progress: 进度回调 (current, total)。
        on_log: 日志回调 (text, level)。

    Returns:
        int: 成功截图数量。
    """
    total = len(tasks)
    success = 0

    def _emit(text: str, level: str = "info") -> None:
        if on_log:
            on_log(text, level)
        log.info(text)

    _emit(f"开始截图循环，共 {total} 个任务")

    for idx, task in enumerate(tasks):
        _emit(f"[{idx + 1}/{total}] {task.name}")

        # 1. 执行前置操作
        for action in task.setup:
            desc = getattr(action, "desc", "") or getattr(action, "template", str(action))
            _emit(f"  → {desc}")
            # 点击前扫描弹窗，避免弹窗拦截下一次点击
            scan_popups(device)
            if not execute_action(device, action):
                _emit(f"  ✗ 前置操作失败: {desc}", "warn")
                # 失败不中止，继续尝试后续操作

        # 2. 等待渲染
        time.sleep(task.shot_delay)

        # 3. 截图
        filename = f"{task.name}.png"
        filepath = device.take_screenshot(filename)
        if filepath:
            _emit(f"  ✓ 截图: {filename}", "success")
            success += 1
        else:
            _emit(f"  ✗ 截图失败: {filename}", "error")

        # 4. 回退
        for i in range(task.teardown_back):
            device.press_back()
            time.sleep(0.5)

        # 5. 弹窗扫描
        closed = scan_popups(device)
        if closed:
            _emit(f"  弹窗关闭: {closed} 个")

        # 6. 进度回调
        if on_progress:
            on_progress(idx + 1, total)

    _emit(f"截图循环完成: {success}/{total} 成功")
    return success


# ------------------------------------------------------------------
# 截图任务定义（从旧 gui/app.py:741-811 移植）
# ------------------------------------------------------------------

ALL_TASKS: list[ScreenshotTask] = [
    ScreenshotTask(
        name="主页",
        setup=[
            ClickCoord(72, 64, desc="点击左上角头像进入个人主页"),
            ClickText("主页", desc="点击主页标签"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="英雄",
        setup=[
            ClickText("英雄", desc="点击英雄标签"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="万象图鉴首页",
        setup=[
            ClickText("图鉴", desc="点击图鉴标签"),
            ClickTemplate("back_arrow.png", threshold=0.7, bounds=(0, 0, 960, 540), desc="点击返回按钮"),
            ClickText("万象图鉴", desc="点击万象图鉴"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="万象图鉴-灵宝",
        setup=[
            ClickText("灵宝", desc="点击灵宝"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="按键",
        setup=[
            ClickText("局内", desc="点击局内按钮"),
            ClickText("按键", desc="点击按键按钮"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="天幕",
        setup=[
            ClickText("天幕", desc="点击天幕"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="星典藏",
        setup=[
            ClickText("星元", desc="点击星元"),
            ClickText("星典藏", desc="点击星典藏"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="星传说",
        setup=[
            ClickText("星传说", desc="点击星传说"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="皮肤图鉴",
        setup=[
            ClickText("皮肤图鉴", desc="点击皮肤图鉴"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="珍品无双",
        setup=[
            ClickText("珍品无双", desc="点击珍品无双"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="荣耀典藏",
        setup=[
            ClickText("荣耀典藏", desc="点击荣耀典藏"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="无双",
        setup=[
            ClickText("无双", desc="点击无双"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="珍品传说",
        setup=[
            ClickText("珍品传说", desc="点击珍品传说"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="传说",
        setup=[
            ClickText("传说", desc="点击传说"),
        ],
        teardown_back=2,
    ),
    ScreenshotTask(
        name="积分夺宝",
        setup=[
            ClickText("商城", desc="点击商城"),
            ClickText("夺宝", desc="点击夺宝"),
            ClickText("积分夺宝", desc="点击积分夺宝"),
        ],
        teardown_back=2,
    ),
    ScreenshotTask(
        name="货币背包",
        setup=[
            ClickText("背包", desc="点击背包"),
            ClickText("货币背包", desc="点击货币背包"),
        ],
        teardown_back=2,
    ),
    ScreenshotTask(
        name="小兵",
        setup=[
            ClickText("定制", desc="点击定制"),
            ClickText("皮肤定制", desc="点击皮肤定制"),
            ClickCoord(1702, 283, desc="点击小兵", verify_text="返回", verify_timeout=120.0),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="个性戳戳",
        setup=[
            ClickText("定制", desc="点击定制"),
            ClickText("个性定制", desc="点击个性定制"),
            ClickText("个性戳戳", desc="点击个性戳戳"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="贵族",
        setup=[
            ClickTemplate("nobility_icon.png", threshold=0.7, bounds=(0, 0, 1920, 540), desc="点击贵族图标"),
        ],
        teardown_back=1,
    ),
]
