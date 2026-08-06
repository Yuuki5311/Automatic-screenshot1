"""截图任务定义与执行引擎。

数据类定义截图工作流，run_screenshot_loop 线性执行。
替代旧 ui_loop.py 的 FSM 感知循环和 gui/app.py 的 screenshot_tasks 列表。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Union

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


@dataclass
class ClickCoord:
    """坐标点击操作（极少场景：点击位置不固定的元素）。

    Attributes:
        x: 点击横坐标。
        y: 点击纵坐标。
        desc: 操作描述。
        verify_template: 点击后等待出现的模板（如加载缓慢的目标页）。
        verify_timeout: 等待 verify_template 的超时秒数。
    """
    x: int
    y: int
    desc: str = ""
    verify_template: str = ""
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
Action = Union[ClickTemplate, ClickCoord, SwipeAction, GuardAction]


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

POPUP_TEMPLATES = [
    "popup_close.png",
    "popup_x.png",
    "after_play_popup.png",
]


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
    """带重试的模板点击。"""
    for attempt in range(1, MAX_RETRIES + 1):
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


def _execute_click_coord(device, action: ClickCoord) -> bool:
    """坐标点击。使用 Airtest touch() 坐标模式。"""
    from airtest.core.api import touch
    touch((action.x, action.y))
    log.info(f"坐标点击: ({action.x}, {action.y}) {action.desc}")
    time.sleep(CLICK_INTERVAL)
    if action.verify_template:
        log.info(f"等待验证模板: {action.verify_template} (最多 {action.verify_timeout}s)")
        if not device.wait_template(action.verify_template, timeout=action.verify_timeout):
            log.error(f"验证模板未出现 ({action.verify_timeout}s): {action.verify_template}")
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
    """扫描并关闭已知弹窗。返回关闭的弹窗数量。"""
    closed = 0
    for tpl_name in POPUP_TEMPLATES:
        if device.exists_template(tpl_name, threshold=0.7):
            log.info(f"扫描到弹窗: {tpl_name}")
            if device.click_template(tpl_name, timeout=3.0, threshold=0.7):
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
            ClickCoord(379, 249, desc="点击左上角头像进入个人主页"),
            ClickTemplate("tab_home.png", desc="点击主页标签"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="英雄",
        setup=[
            ClickTemplate("tab_hero.png", desc="点击英雄标签"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="万象图鉴首页",
        setup=[
            ClickTemplate("tab_illustrated.png", desc="点击图鉴标签"),
            GuardAction("back_arrow.png", "back_arrow.png", desc="返回箭头守卫"),
            ClickTemplate("universal_illustrated.png", desc="点击万象图鉴"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="万象图鉴-灵宝",
        setup=[
            ClickTemplate("lingbao.png", desc="点击灵宝"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="按键",
        setup=[
            ClickTemplate("in_game_btn.png", desc="点击局内按钮"),
            ClickTemplate("keybind_btn.png", desc="点击按键按钮"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="天幕",
        setup=[
            ClickTemplate("tianmu.png", desc="点击天幕"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="星典藏",
        setup=[
            ClickTemplate("xingyuan.png", desc="点击星元"),
            ClickTemplate("xing_collection.png", desc="点击星典藏"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="星传说",
        setup=[
            ClickTemplate("xing_legend.png", desc="点击星传说"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="皮肤图鉴",
        setup=[
            ClickTemplate("skin_illustrated.png", desc="点击皮肤图鉴"),
        ],
        teardown_back=0,
    ),
    ScreenshotTask(
        name="珍品无双",
        setup=[
            ClickTemplate("skin_treasure_wushuang.png", desc="点击珍品无双"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="荣耀典藏",
        setup=[
            ClickTemplate("skin_glory_collection.png", desc="点击荣耀典藏"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="无双",
        setup=[
            ClickTemplate("skin_wushuang.png", desc="点击无双"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="珍品传说",
        setup=[
            ClickTemplate("skin_treasure_legend.png", desc="点击珍品传说"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="传说",
        setup=[
            ClickTemplate("skin_legend.png", desc="点击传说"),
        ],
        teardown_back=2,
    ),
    ScreenshotTask(
        name="积分夺宝",
        setup=[
            ClickTemplate("shop_icon.png", desc="点击商城"),
            ClickTemplate("lottery_tab.png", desc="点击夺宝"),
            ClickTemplate("points_lottery.png", desc="点击积分夺宝"),
        ],
        teardown_back=2,
    ),
    ScreenshotTask(
        name="货币背包",
        setup=[
            ClickTemplate("bag.png", desc="点击背包"),
            ClickTemplate("currency_bag.png", desc="点击货币背包"),
        ],
        teardown_back=2,
    ),
    ScreenshotTask(
        name="小兵",
        setup=[
            ClickTemplate("customize_icon.png", desc="点击定制"),
            ClickTemplate("skin_customize.png", desc="点击皮肤定制"),
            ClickCoord(1377, 366, desc="点击小兵", verify_template="back_arrow.png", verify_timeout=120.0),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="个性戳戳",
        setup=[
            ClickTemplate("customize_icon.png", desc="点击定制"),
            ClickTemplate("personal_customize.png", desc="点击个性定制"),
            ClickTemplate("poke.png", desc="点击个性戳戳"),
        ],
        teardown_back=1,
    ),
    ScreenshotTask(
        name="贵族",
        setup=[
            ClickTemplate("nobility_icon.png", desc="点击贵族图标"),
        ],
        teardown_back=1,
    ),
]
