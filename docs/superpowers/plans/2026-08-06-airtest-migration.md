# Airtest Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the project from Selenium/CDP browser cloud gaming to Airtest + MuMu Android emulator native automation.

**Architecture:** Delete all browser-related modules (browser.py, navigator.py, login.py, ui_state.py, ui_loop.py, game_launcher.py, client_launcher.py, screenshotter.py, screenshot_click.py, click_confirm.py, popup_monitor.py, calibrate_coords.json, templates/*.png). Create 4 new modules (airtest_device.py, airtest_tasks.py, airtest_login.py, airtest_keybind.py). Simplify config.py and gui/app.py. Update requirements.txt and packaging configs.

**Tech Stack:** Python 3.12, Airtest (airtest + pocoui), ADB, MuMu 12 Android Emulator, Tkinter, PyInstaller

## Global Constraints

- Python 3.12 minimum
- Airtest >= 1.4.0
- MuMu 12 Android Emulator with ADB port 127.0.0.1:7555
- 王者荣耀 APK pre-installed on emulator
- QQ pre-installed and logged in on emulator
- PyInstaller `--onefile --windowed` for Windows distribution
- All user-facing strings in Chinese
- Follow existing naming conventions: snake_case files, CamelCase classes

---

## File Structure Map

```
Automatic-screenshot/
├── main.py                     # [MODIFY] Update preload imports
├── config.py                   # [MODIFY] Remove browser constants
├── airtest_device.py           # [CREATE] Device connection + template ops
├── airtest_tasks.py            # [CREATE] Task definitions + execution loop
├── airtest_login.py            # [CREATE] In-game QQ auth login
├── airtest_keybind.py          # [CREATE] Keybinding configuration
├── logger.py                   # [KEEP] No changes
├── process_cleanup.py          # [KEEP] No changes
├── gui/
│   ├── __init__.py             # [KEEP] No changes
│   ├── app.py                  # [MODIFY] Rewrite to 2-page GUI
│   └── widgets/
│       ├── __init__.py          # [KEEP] No changes
│       └── log_view.py          # [KEEP] No changes
├── airtest_templates/          # [CREATE] Directory for AirtestIDE templates
├── screenshots/                # [KEEP] Output directory
├── requirements.txt            # [MODIFY] Replace deps
├── AutoScreenshot.spec          # [MODIFY] Update datas
├── .github/workflows/build.yml # [MODIFY] Update build steps
└── (DELETED — see Task 1)       # browser.py, navigator.py, login.py,
                                 # ui_state.py, ui_loop.py, game_launcher.py,
                                 # client_launcher.py, screenshotter.py,
                                 # screenshot_click.py, click_confirm.py,
                                 # popup_monitor.py, calibrate_coords.json,
                                 # calibrate_coords.py, capture_one_coord.py,
                                 # capture_templates.py, probe_dom.py,
                                 # templates/*.png
```

---

### Task 1: Clean up old modules and update project configuration

**Files:**
- Delete: `browser.py`, `navigator.py`, `login.py`, `ui_state.py`, `ui_loop.py`, `game_launcher.py`, `client_launcher.py`, `screenshotter.py`, `screenshot_click.py`, `click_confirm.py`, `popup_monitor.py`
- Delete: `calibrate_coords.json`, `calibrate_coords.py`, `capture_one_coord.py`, `capture_templates.py`, `probe_dom.py`
- Delete: `gui/widgets/qr_display.py`
- Delete: `templates/*.png` (keep `templates/README.md` for reference)
- Modify: `config.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: Nothing
- Produces: Clean project root, updated config constants, updated deps

- [ ] **Step 1: Delete old browser-related modules**

```bash
cd /Users/l/Desktop/Automatic-screenshot
rm -f browser.py navigator.py login.py ui_state.py ui_loop.py
rm -f game_launcher.py client_launcher.py screenshotter.py
rm -f screenshot_click.py click_confirm.py popup_monitor.py
```

- [ ] **Step 2: Delete calibration tools and coordinate files**

```bash
rm -f calibrate_coords.json calibrate_coords.py capture_one_coord.py capture_templates.py probe_dom.py
```

- [ ] **Step 3: Delete QR display widget (no longer needed)**

```bash
rm -f gui/widgets/qr_display.py
```

- [ ] **Step 4: Delete old browser templates**

```bash
rm -f templates/*.png
```

- [ ] **Step 5: Verify deletions — confirm project is clean**

```bash
ls browser.py navigator.py login.py ui_state.py ui_loop.py 2>&1
# Expected: No such file or directory for each
ls game_launcher.py client_launcher.py screenshotter.py 2>&1
# Expected: No such file or directory for each
ls screenshot_click.py click_confirm.py popup_monitor.py 2>&1
# Expected: No such file or directory for each
ls calibrate_coords.json calibrate_coords.py 2>&1
# Expected: No such file or directory for each
ls gui/widgets/qr_display.py 2>&1
# Expected: No such file or directory
ls templates/*.png 2>&1
# Expected: No matches found
```

- [ ] **Step 6: Rewrite `config.py` — remove browser constants, keep path/utility config**

Write the entire file:

```python
"""全局配置常量。"""

# ---------------------------------------------------------------------------
# Airtest / MuMu 模拟器
# ---------------------------------------------------------------------------
DEVICE_URI = "Android://127.0.0.1:7555"

# ---------------------------------------------------------------------------
# 等待时间 (秒)
# ---------------------------------------------------------------------------
CLICK_INTERVAL = 1.5        # 点击后等待
TEMPLATE_TIMEOUT = 10.0     # 模板匹配总超时
SHOT_DELAY = 1.0            # 截图前页面渲染等待

# ---------------------------------------------------------------------------
# 截图间隔随机延迟 (秒)
# ---------------------------------------------------------------------------
SCREENSHOT_DELAY_MIN = 0.5
SCREENSHOT_DELAY_MAX = 1.5

# ---------------------------------------------------------------------------
# 模板匹配
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = 0.7     # Airtest 模板匹配置信度阈值
MAX_RETRIES = 3             # 每个操作最大重试次数
RETRY_INTERVAL = 2          # 重试间隔 (秒)

# ---------------------------------------------------------------------------
# 目录路径 (相对于项目根目录)
# ---------------------------------------------------------------------------
TEMPLATES_DIR = "airtest_templates"
SCREENSHOTS_DIR = "screenshots"

# ---------------------------------------------------------------------------
# 资源路径工具
# ---------------------------------------------------------------------------
import sys
import os


def resource_path(relative_path: str) -> str:
    """获取资源文件绝对路径，兼容开发环境和 PyInstaller 打包。

    PyInstaller 打包后，资源文件解压到 sys._MEIPASS 临时目录。
    """
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def app_dir() -> str:
    """返回运行时可写文件的根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def writable_path(relative_path: str) -> str:
    """获取截图、日志等运行时输出的绝对路径。"""
    return os.path.join(app_dir(), relative_path)
```

- [ ] **Step 7: Verify `config.py` imports work**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "from config import DEVICE_URI, TEMPLATES_DIR, resource_path; print('DEVICE_URI:', DEVICE_URI); print('TEMPLATES_DIR:', TEMPLATES_DIR); print('resource_path ok:', resource_path('config.py'))"
# Expected: DEVICE_URI: Android://127.0.0.1:7555, TEMPLATES_DIR: airtest_templates, resource_path ok: /Users/l/Desktop/Automatic-screenshot/config.py
```

- [ ] **Step 8: Rewrite `requirements.txt`**

Write the entire file:

```
airtest>=1.4.0
pocoui>=1.0
Pillow>=10.0
numpy>=1.24
```

- [ ] **Step 9: Install new dependencies**

```bash
cd /Users/l/Desktop/Automatic-screenshot && pip install airtest pocoui 2>&1 | tail -5
# Expected: Successfully installed airtest pocoui ...
```

- [ ] **Step 10: Verify Airtest imports**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "from airtest.core.api import connect_device, touch, snapshot, wait, exists, keyevent; print('Airtest imports OK')"
# Expected: Airtest imports OK
```

- [ ] **Step 11: Create `airtest_templates/` directory**

```bash
mkdir -p /Users/l/Desktop/Automatic-screenshot/airtest_templates
```

- [ ] **Step 12: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add -A
git commit -m "feat: delete old browser modules, update config and requirements for Airtest migration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Create `airtest_device.py` — device connection and template operations

**Files:**
- Create: `airtest_device.py`

**Interfaces:**
- Consumes: `config.py` (DEVICE_URI, TEMPLATES_DIR, TEMPLATE_TIMEOUT, DEFAULT_THRESHOLD, SCREENSHOTS_DIR, writable_path)
- Produces: `AirtestDevice` class with methods:
  - `__init__(self, device_uri: str = DEVICE_URI)` — connect to emulator
  - `connect(self) -> None` — explicit connect
  - `click_template(self, template_name: str, timeout: float = TEMPLATE_TIMEOUT, threshold: float = DEFAULT_THRESHOLD) -> None` — wait + touch
  - `wait_template(self, template_name: str, timeout: float = TEMPLATE_TIMEOUT, threshold: float = DEFAULT_THRESHOLD) -> None` — wait only
  - `exists_template(self, template_name: str, threshold: float = DEFAULT_THRESHOLD) -> bool` — check existence
  - `take_screenshot(self, filename: str) -> str` — screenshot to file, returns path
  - `swipe_screen(self, direction: str, duration: float = 0.3) -> None` — swipe in direction
  - `press_back(self) -> None` — Android back key
  - `press_home(self) -> None` — Android home key
  - `start_app(self, package: str) -> None` — launch app
  - `stop_app(self, package: str) -> None` — stop app

- [ ] **Step 1: Write `airtest_device.py`**

```python
"""Airtest 设备操作封装。

替代旧 Navigator：提供模板点击、等待、截图、返回键等操作。
"""

from __future__ import annotations

import time
from pathlib import Path

from airtest.core.api import (
    connect_device,
    device,
    exists,
    init_device,
    keyevent,
    snapshot,
    start_app,
    stop_app,
    swipe,
    touch,
    wait,
)
from airtest.core.error import TargetNotFoundError
from airtest.aircv.template_matching import Template

from config import (
    DEFAULT_THRESHOLD,
    DEVICE_URI,
    SCREENSHOTS_DIR,
    TEMPLATES_DIR,
    TEMPLATE_TIMEOUT,
    writable_path,
)
from logger import get_logger

log = get_logger()


class AirtestDevice:
    """封装 Airtest 设备操作，对应旧项目的 Navigator。"""

    def __init__(self, device_uri: str = DEVICE_URI) -> None:
        self._device_uri = device_uri
        self._connected = False
        self._templates_dir = Path(TEMPLATES_DIR)

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """连接 Android 模拟器设备。"""
        if self._connected:
            return
        init_device("Android")
        connect_device(self._device_uri)
        self._connected = True
        log.info(f"设备已连接: {self._device_uri}")

    def disconnect(self) -> None:
        """断开设备连接（Airtest 没有显式 disconnect，此方法为占位）。"""
        self._connected = False
        log.info("设备连接标记已清除")

    # ------------------------------------------------------------------
    # 模板操作
    # ------------------------------------------------------------------

    def _template_path(self, template_name: str) -> str:
        """返回模板文件绝对路径。"""
        p = self._templates_dir / template_name
        if not p.suffix:
            p = p.with_suffix(".png")
        return str(p)

    def click_template(
        self,
        template_name: str,
        timeout: float = TEMPLATE_TIMEOUT,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> bool:
        """等待模板出现后点击，替代 Navigator.find_and_click()。

        Returns:
            bool: 成功点击返回 True，超时返回 False。
        """
        tpl_path = self._template_path(template_name)
        tpl = Template(tpl_path, threshold=threshold)
        try:
            wait(tpl, timeout=timeout)
            touch(tpl)
            log.info(f"点击模板: {template_name}")
            return True
        except TargetNotFoundError:
            log.warning(f"模板未出现 ({timeout}s): {template_name}")
            return False

    def wait_template(
        self,
        template_name: str,
        timeout: float = TEMPLATE_TIMEOUT,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> bool:
        """等待模板出现，不点击。

        Returns:
            bool: 模板出现返回 True，超时返回 False。
        """
        tpl_path = self._template_path(template_name)
        tpl = Template(tpl_path, threshold=threshold)
        try:
            wait(tpl, timeout=timeout)
            log.info(f"模板已出现: {template_name}")
            return True
        except TargetNotFoundError:
            log.warning(f"等待模板超时 ({timeout}s): {template_name}")
            return False

    def exists_template(
        self,
        template_name: str,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> bool:
        """检查模板是否存在（非阻塞）。

        Returns:
            bool: 模板存在返回 True。
        """
        tpl_path = self._template_path(template_name)
        tpl = Template(tpl_path, threshold=threshold)
        return bool(exists(tpl))

    # ------------------------------------------------------------------
    # 截图
    # ------------------------------------------------------------------

    def take_screenshot(self, filename: str) -> str:
        """截图保存到 screenshots 目录，替代 CDP Page.captureScreenshot。

        Returns:
            str: 截图文件绝对路径。
        """
        output_dir = Path(writable_path(SCREENSHOTS_DIR))
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename
        snapshot(filename=str(filepath))
        log.info(f"截图已保存: {filepath}")
        return str(filepath)

    # ------------------------------------------------------------------
    # 手势
    # ------------------------------------------------------------------

    def swipe_screen(
        self,
        direction: str,
        duration: float = 0.3,
        distance: int = 400,
    ) -> None:
        """滑动屏幕，用于列表滚动等场景。

        Args:
            direction: "up" | "down" | "left" | "right"
            duration: 滑动持续时间 (秒)
            distance: 滑动距离 (像素)
        """
        # 以屏幕中心为起点
        w, h = device().get_current_resolution()
        cx, cy = w // 2, h // 2

        offsets = {
            "up": (0, -distance),
            "down": (0, distance),
            "left": (-distance, 0),
            "right": (distance, 0),
        }
        dx, dy = offsets.get(direction, (0, -distance))
        swipe((cx, cy), (cx + dx, cy + dy), duration=duration)
        log.info(f"滑动: {direction} ({distance}px, {duration}s)")

    # ------------------------------------------------------------------
    # 按键
    # ------------------------------------------------------------------

    def press_back(self) -> None:
        """Android 返回键。"""
        keyevent("BACK")
        log.info("按下返回键")

    def press_home(self) -> None:
        """Android Home 键。"""
        keyevent("HOME")
        log.info("按下 Home 键")

    # ------------------------------------------------------------------
    # App 生命周期
    # ------------------------------------------------------------------

    def start_app(self, package: str) -> None:
        """启动应用。"""
        start_app(package)
        log.info(f"启动应用: {package}")

    def stop_app(self, package: str) -> None:
        """停止应用。"""
        stop_app(package)
        log.info(f"停止应用: {package}")
```

- [ ] **Step 2: Verify syntax and imports**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "from airtest_device import AirtestDevice; d = AirtestDevice(); print('AirtestDevice class OK, uri:', d._device_uri)"
# Expected: AirtestDevice class OK, uri: Android://127.0.0.1:7555
```

- [ ] **Step 3: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add airtest_device.py
git commit -m "feat: add AirtestDevice wrapper for template operations

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Create `airtest_tasks.py` — task definitions and execution loop

**Files:**
- Create: `airtest_tasks.py`

**Interfaces:**
- Consumes: `airtest_device.AirtestDevice`, `config.py` (CLICK_INTERVAL, SHOT_DELAY, MAX_RETRIES)
- Produces:
  - `ClickTemplate`, `ClickCoord`, `SwipeAction`, `GuardAction` dataclasses
  - `ScreenshotTask` dataclass
  - `execute_action(device: AirtestDevice, action) -> bool` function
  - `run_screenshot_loop(device: AirtestDevice, tasks: list[ScreenshotTask], on_progress, on_log) -> int` function
  - `POPUP_TEMPLATES` list — popup templates to scan after each task
  - `ALL_TASKS` — ported list of all ScreenshotTask definitions

- [ ] **Step 1: Write `airtest_tasks.py`**

```python
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
    """坐标点击操作（极少场景：点击位置不固定的元素）。"""
    x: int
    y: int
    desc: str = ""


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
    import airtest_device as _ad

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
            ClickTemplate("game_main.png", desc="确认主界面"),
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
            ClickCoord(1377, 366, desc="点击小兵"),
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
```

- [ ] **Step 2: Verify syntax**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "from airtest_tasks import ALL_TASKS, ScreenshotTask, ClickTemplate, GuardAction, SwipeAction, ClickCoord; print(f'Tasks: {len(ALL_TASKS)}'); print(f'First: {ALL_TASKS[0].name}'); print(f'Last: {ALL_TASKS[-1].name}')"
# Expected: Tasks: 19, First: 主页, Last: 贵族
```

- [ ] **Step 3: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add airtest_tasks.py
git commit -m "feat: add task definitions and screenshot execution loop

Ported 19 screenshot tasks from old gui/app.py screenshot_tasks list.
Replaced __coords__, __optional__, __guard__ with ClickCoord, GuardAction.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Create `airtest_login.py` — in-game QQ auth login

**Files:**
- Create: `airtest_login.py`

**Interfaces:**
- Consumes: `airtest_device.AirtestDevice`, `config.py` (CLICK_INTERVAL)
- Produces: `game_login(device: AirtestDevice) -> bool` function

- [ ] **Step 1: Write `airtest_login.py`**

```python
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
```

- [ ] **Step 2: Verify syntax and imports**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "from airtest_login import game_login, HOK_PACKAGE; print('game_login imported OK'); print('HOK_PACKAGE:', HOK_PACKAGE)"
# Expected: game_login imported OK, HOK_PACKAGE: com.tencent.tmgp.sgame
```

- [ ] **Step 3: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add airtest_login.py
git commit -m "feat: add Airtest-based game login (QQ auth in emulator)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Create `airtest_keybind.py` — keybinding configuration

**Files:**
- Create: `airtest_keybind.py`

**Interfaces:**
- Consumes: `airtest_device.AirtestDevice`, `config.py` (CLICK_INTERVAL)
- Produces: `configure_keybinding(device: AirtestDevice) -> bool` function

- [ ] **Step 1: Write `airtest_keybind.py`**

```python
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
```

- [ ] **Step 2: Verify syntax**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "from airtest_keybind import configure_keybinding; print('configure_keybinding imported OK')"
# Expected: configure_keybinding imported OK
```

- [ ] **Step 3: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add airtest_keybind.py
git commit -m "feat: add Airtest-based keybinding configuration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Rewrite `gui/app.py` — simplified 2-page GUI

**Files:**
- Modify: `gui/app.py`

**Interfaces:**
- Consumes: `airtest_device.AirtestDevice`, `airtest_login.game_login`, `airtest_keybind.configure_keybinding`, `airtest_tasks.ALL_TASKS`, `airtest_tasks.run_screenshot_loop`, `config.py` (TEMPLATES_DIR, SCREENSHOTS_DIR, writable_path, resource_path), `logger.get_logger`
- Produces: `App(tk.Tk)` class with 2 pages (idle, progress), Queue-based thread communication

- [ ] **Step 1: Read current `gui/app.py` to understand existing patterns**

(Already read — use existing LogView widget, Queue polling pattern, _send/_handle_message pattern)

- [ ] **Step 2: Write the rewritten `gui/app.py`**

Write the entire file:

```python
"""Tkinter GUI 主应用 — Airtest 版本。

管理页面切换、后台任务调度、跨线程通信。
2 个页面：空闲页（启动模拟器/开始运行）、进度页（日志 + 进度）。
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue
import time

from gui.widgets.log_view import LogView


class App(tk.Tk):
    """GUI 主窗口，2 个页面：空闲、进度。"""

    def __init__(self):
        super().__init__()

        self.title("王者荣耀自动截图 (Airtest)")
        self.geometry("480x620")
        self.resizable(True, True)
        self.minsize(400, 500)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- 跨线程通信 ----
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = None

        # ---- 模拟器设备 ----
        self._device = None

        # ---- 账号输入 ----
        self._account_var = tk.StringVar(value="")

        # ---- 构建 UI ----
        self._build_ui()

        # ---- 启动队列轮询 ----
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _build_ui(self):
        """构建所有页面框架。"""

        # ---- 顶部标题栏 ----
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(
            header, text="王者荣耀自动截图 (Airtest)",
            font=("", 16, "bold")
        ).pack(side="left")

        # ---- 页面容器 ----
        self._page_container = ttk.Frame(self)
        self._page_container.pack(fill="both", expand=True, padx=10, pady=5)

        # ---- 页面 1: 空闲页 ----
        self._page_idle = ttk.Frame(self._page_container)
        ttk.Label(
            self._page_idle, text="就绪",
            font=("", 14, "bold")
        ).pack(pady=(20, 5))
        ttk.Label(
            self._page_idle,
            text="连接 MuMu 模拟器并启动截图任务",
            font=("", 11)
        ).pack(pady=(0, 10))

        # 模拟器状态
        emu_frame = ttk.LabelFrame(self._page_idle, text="模拟器", padding=10)
        emu_frame.pack(pady=5, fill="x", padx=10)
        ttk.Label(
            emu_frame,
            text="MuMu 12 Android Emulator\nADB: 127.0.0.1:7555",
            font=("", 10)
        ).pack(anchor="w")

        # 账号输入
        account_frame = ttk.LabelFrame(
            self._page_idle, text="账号（作为截图文件夹名）", padding=10
        )
        account_frame.pack(pady=5, fill="x", padx=10)
        ttk.Entry(
            account_frame, textvariable=self._account_var, width=30
        ).pack(fill="x")

        ttk.Button(
            self._page_idle, text="启 动",
            command=self._on_start, width=20
        ).pack(pady=10)

        # ---- 页面 2: 进度页 ----
        self._page_progress = ttk.Frame(self._page_container)
        self._log_view = LogView(self._page_progress)
        self._log_view.pack(fill="both", expand=True)

        # ---- 底部按钮 ----
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))
        self._rerun_btn = ttk.Button(
            bottom, text="再执行一轮", command=self._on_start
        )
        self._exit_btn = ttk.Button(
            bottom, text="退 出", command=self._on_close
        )
        self._exit_btn.pack(side="right")

        # 默认显示空闲页
        self._show_page("idle")

    # ------------------------------------------------------------------
    # 页面切换
    # ------------------------------------------------------------------

    def _show_page(self, name: str):
        """显示指定页面，隐藏其余。"""
        for page in [self._page_idle, self._page_progress]:
            page.pack_forget()

        mapping = {
            "idle": self._page_idle,
            "progress": self._page_progress,
        }
        page = mapping.get(name)
        if page:
            page.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # 按钮事件
    # ------------------------------------------------------------------

    def _on_start(self):
        """点击启动按钮。"""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._log_view.clear()
        self._show_page("progress")
        self._log_view.add_log("启动任务...", "info")
        self._exit_btn.config(state="normal")
        self._rerun_btn.pack_forget()

        self._worker_thread = threading.Thread(
            target=self._run_workflow, daemon=True
        )
        self._worker_thread.start()

    def _on_close(self):
        """关闭窗口。"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        import process_cleanup
        process_cleanup.cleanup_all()
        self.destroy()

    # ------------------------------------------------------------------
    # 队列轮询
    # ------------------------------------------------------------------

    def _poll_queue(self):
        """定时从队列取出消息并更新 UI。"""
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_message(self, msg: dict):
        """处理来自后台线程的消息。"""
        msg_type = msg.get("type")

        if msg_type == "log":
            self._log_view.add_log(msg["text"], msg.get("level", "info"))

        elif msg_type == "progress":
            self._log_view.update_progress(msg["current"], msg["total"])

        elif msg_type == "page":
            self._show_page(msg["name"])

        elif msg_type == "done":
            self._send({"type": "log", "text": msg["text"], "level": "success"})
            self._show_page("idle")
            self._rerun_btn.pack(side="left", padx=(0, 5))

    # ------------------------------------------------------------------
    # 线程安全消息发送
    # ------------------------------------------------------------------

    def _send(self, msg: dict):
        """线程安全地向 GUI 队列发送消息。"""
        self._queue.put(msg)

    # ------------------------------------------------------------------
    # 后台工作流
    # ------------------------------------------------------------------

    def _run_workflow(self):
        """后台线程：执行完整的登录 → 截图工作流。"""
        from logger import get_logger
        import os

        _log = get_logger()

        try:
            _log.info("工作流线程启动 (Airtest)")
            self._send({"type": "log", "text": "正在加载组件..."})

            from airtest_device import AirtestDevice
            from airtest_login import game_login
            from airtest_keybind import configure_keybinding
            from airtest_tasks import ALL_TASKS, run_screenshot_loop
            from config import DEVICE_URI

            _log.info("工作流模块就绪")

            # ====== 阶段 1: 连接模拟器 ======
            if self._stop_event.is_set():
                return

            _log.info("[阶段1] 连接 MuMu 模拟器")
            self._send({"type": "log", "text": f"正在连接模拟器: {DEVICE_URI}..."})

            try:
                device = AirtestDevice(DEVICE_URI)
                device.connect()
            except Exception as e:
                _log.exception("[阶段1] 连接模拟器失败")
                self._send({
                    "type": "log",
                    "text": f"❌ 连接模拟器失败: {e}\n请确认 MuMu 12 已启动且 ADB 端口为 7555",
                    "level": "error",
                })
                self._send({"type": "done", "text": "❌ 连接模拟器失败"})
                return

            self._device = device
            self._send({"type": "log", "text": "✅ 模拟器已连接", "level": "success"})

            # ====== 阶段 2: 游戏登录 ======
            if self._stop_event.is_set():
                return

            _log.info("[阶段2] 开始游戏登录")
            self._send({"type": "log", "text": "正在启动王者荣耀并登录..."})

            if not game_login(device, timeout=120.0):
                _log.error("[阶段2] 游戏登录失败")
                self._send({"type": "log", "text": "❌ 游戏登录失败", "level": "error"})
                self._send({"type": "done", "text": "❌ 游戏登录失败"})
                return

            self._send({"type": "log", "text": "✅ 游戏登录成功", "level": "success"})

            # ====== 阶段 3: 键位配置 ======
            if self._stop_event.is_set():
                return

            _log.info("[阶段3] 键位配置")
            self._send({"type": "log", "text": "正在配置键位..."})

            if not configure_keybinding(device):
                _log.warning("[阶段3] 键位配置失败，继续截图")
                self._send({
                    "type": "log",
                    "text": "⚠️ 键位配置失败，继续截图",
                    "level": "warn",
                })
            else:
                self._send({
                    "type": "log",
                    "text": "✅ 键位配置完成",
                    "level": "success",
                })

            # ====== 阶段 4: 截图循环 ======
            if self._stop_event.is_set():
                return

            _log.info("[阶段4] 开始截图循环")
            self._send({"type": "log", "text": "开始截图循环..."})

            def _on_log(text, level="info"):
                self._send({"type": "log", "text": text, "level": level})

            def _on_progress(cur, tot):
                self._send({"type": "progress", "current": cur, "total": tot})

            success = run_screenshot_loop(
                device=device,
                tasks=ALL_TASKS,
                on_progress=_on_progress,
                on_log=_on_log,
            )

            self._send({
                "type": "log",
                "text": f"完成: {success}/{len(ALL_TASKS)} 张截图成功",
                "level": "success",
            })

            self._send({
                "type": "done",
                "text": f"✅ 本轮完成: {success}/{len(ALL_TASKS)} 张截图"
            })

        except Exception as e:
            import traceback
            _log.exception(f"工作流异常: {e}")
            self._send({"type": "log", "text": f"异常: {e}", "level": "error"})
            self._send({"type": "done", "text": f"❌ 运行异常: {e}"})
            traceback.print_exc()
        finally:
            # 断开设备连接
            if self._device is not None:
                try:
                    self._device.disconnect()
                except Exception:
                    pass
                self._device = None

    # ------------------------------------------------------------------
    # 启动
    # ------------------------------------------------------------------

    def run(self):
        """启动 GUI 主循环。"""
        self.mainloop()
```

- [ ] **Step 2: Verify Tkinter imports and syntax**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "
import sys
sys.path.insert(0, '.')
# Don't actually start the GUI, just verify imports
import ast
with open('gui/app.py') as f:
    ast.parse(f.read())
print('gui/app.py syntax OK')
"
# Expected: gui/app.py syntax OK
```

- [ ] **Step 3: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add gui/app.py
git commit -m "feat: rewrite GUI to 2-page Airtest version

Removed QR scan page, platform selection, login type selection.
Simplified workflow to: connect emulator -> game login -> keybind -> screenshot loop.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Update `main.py` — revise preload imports

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `airtest_device`, `airtest_login`, `airtest_keybind`, `airtest_tasks` (for preload)
- Produces: Same entry point: `python main.py` launches GUI

- [ ] **Step 1: Rewrite `main.py`**

Write the entire file:

```python
#!/usr/bin/env python3
"""王者荣耀自动截图 —— GUI 入口 (Airtest 版本)。

启动 Tkinter 控制面板，连接 MuMu 模拟器，自动登录并截图。

使用方法:
    python main.py

前置条件:
    1. MuMu 12 模拟器已启动
    2. 模拟器内 QQ 已登录
    3. 王者荣耀 APK 已安装
"""

import multiprocessing
import sys


def _preload_runtime():
    """在主线程预加载重量级依赖。

    PyInstaller 打包后，若在后台线程首次 import airtest，
    Windows 上可能卡死，表现为点启动后无法操作。
    """
    from logger import setup_logger, get_logger

    setup_logger()
    log = get_logger()
    log.info("预加载运行时依赖 (airtest / cv2 / numpy)...")
    import airtest.core.api  # noqa: F401
    import airtest.aircv.template_matching  # noqa: F401
    import cv2  # noqa: F401
    import numpy  # noqa: F401
    from PIL import Image  # noqa: F401
    import airtest_device  # noqa: F401
    import airtest_login  # noqa: F401
    import airtest_keybind  # noqa: F401
    import airtest_tasks  # noqa: F401
    log.info("运行时依赖预加载完成")


if __name__ == "__main__":
    import atexit
    import process_cleanup

    multiprocessing.freeze_support()

    # 清扫上次残留进程
    process_cleanup.cleanup_orphans()

    # 正常退出兜底
    atexit.register(process_cleanup.cleanup_all)

    try:
        _preload_runtime()
    except Exception:
        from logger import get_logger
        get_logger().exception("预加载失败")

    from gui.app import App

    app = App()
    app.run()
```

- [ ] **Step 2: Verify syntax**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "
import ast
with open('main.py') as f:
    ast.parse(f.read())
print('main.py syntax OK')
"
# Expected: main.py syntax OK
```

- [ ] **Step 3: Verify all imports resolve**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "
from airtest_device import AirtestDevice
from airtest_login import game_login
from airtest_keybind import configure_keybinding
from airtest_tasks import ALL_TASKS, run_screenshot_loop, ScreenshotTask, ClickTemplate, GuardAction
from config import DEVICE_URI, TEMPLATES_DIR, SCREENSHOTS_DIR, resource_path, writable_path
print('All project imports OK')
"
# Expected: All project imports OK
```

- [ ] **Step 4: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add main.py
git commit -m "feat: update main.py preload for Airtest imports

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Update packaging configs — PyInstaller spec and GitHub Actions

**Files:**
- Modify: `AutoScreenshot.spec`
- Modify: `.github/workflows/build.yml`

**Interfaces:**
- Consumes: Project structure with `airtest_templates/` directory
- Produces: Working PyInstaller build on Windows

- [ ] **Step 1: Read current `AutoScreenshot.spec`**

```bash
cat /Users/l/Desktop/Automatic-screenshot/AutoScreenshot.spec
```

- [ ] **Step 2: Rewrite `AutoScreenshot.spec`**

Update the `datas` section to include Airtest templates and Airtest ADB binaries:

```python
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


block_cipher = None

# 收集 Airtest 数据文件（ADB 二进制等）
airtest_datas = collect_data_files('airtest')
pocoui_datas = collect_data_files('pocoui') if _has_pocoui() else []

# 模板目录
template_datas = []
templates_dir = Path('airtest_templates')
if templates_dir.is_dir():
    template_datas = [(str(p), str(p.relative_to('.'))) for p in templates_dir.rglob('*.png')]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('airtest_templates', 'airtest_templates'),
    ],
    hiddenimports=[
        'airtest',
        'airtest.core',
        'airtest.core.api',
        'airtest.aircv',
        'airtest.aircv.template_matching',
        'pocoui',
        'cv2',
        'numpy',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'test',
        'pydoc',
        'distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoScreenshot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
```

- [ ] **Step 3: Read current build workflow**

```bash
cat /Users/l/Desktop/Automatic-screenshot/.github/workflows/build.yml
```

- [ ] **Step 4: Update `.github/workflows/build.yml`**

Update the install step to use new dependencies:

```yaml
name: Build Windows EXE

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install airtest pocoui Pillow numpy
          pip install pyinstaller

      - name: Build EXE
        run: |
          pyinstaller AutoScreenshot.spec --onefile --windowed --clean

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: AutoScreenshot-Windows
          path: dist/AutoScreenshot.exe
```

- [ ] **Step 5: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add AutoScreenshot.spec .github/workflows/build.yml
git commit -m "build: update packaging configs for Airtest dependencies

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Final verification — project-wide import check and structure validation

**Files:**
- None (verification only)

- [ ] **Step 1: Verify project structure is correct**

```bash
cd /Users/l/Desktop/Automatic-screenshot
echo "=== Expected files ==="
for f in main.py config.py airtest_device.py airtest_tasks.py airtest_login.py airtest_keybind.py gui/app.py logger.py process_cleanup.py requirements.txt; do
    if [ -f "$f" ]; then echo "✓ $f"; else echo "✗ MISSING: $f"; fi
done

echo ""
echo "=== Deleted files (should NOT exist) ==="
for f in browser.py navigator.py login.py ui_state.py ui_loop.py game_launcher.py client_launcher.py screenshotter.py screenshot_click.py click_confirm.py popup_monitor.py calibrate_coords.json calibrate_coords.py; do
    if [ -f "$f" ]; then echo "✗ STILL EXISTS: $f"; else echo "✓ $f (deleted)"; fi
done
```

Expected: All new files exist, all old files deleted.

- [ ] **Step 2: Run full import verification**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "
# Verify all project modules import successfully
import config
import logger
import process_cleanup
import airtest_device
import airtest_tasks
import airtest_login
import airtest_keybind

# Verify dataclass instantiation
from airtest_tasks import (
    ScreenshotTask, ClickTemplate, ClickCoord,
    SwipeAction, GuardAction, ALL_TASKS
)

# Verify ALL_TASKS is well-formed
assert len(ALL_TASKS) == 19, f'Expected 19 tasks, got {len(ALL_TASKS)}'
for task in ALL_TASKS:
    assert isinstance(task.name, str) and task.name, f'Task has no name: {task}'
    assert isinstance(task.setup, list), f'Task {task.name} setup is not a list'
    for action in task.setup:
        assert isinstance(action, (ClickTemplate, ClickCoord, SwipeAction, GuardAction)), \
            f'Task {task.name}: unknown action type {type(action)}'

# Verify config constants
from config import DEVICE_URI, DEFAULT_THRESHOLD, TEMPLATES_DIR

print(f'All checks passed: {len(ALL_TASKS)} tasks, config OK')
"
# Expected: All checks passed: 19 tasks, config OK
```

- [ ] **Step 3: Verify entry point can be parsed**

```bash
cd /Users/l/Desktop/Automatic-screenshot && python -c "
import ast
for f in ['main.py', 'gui/app.py', 'airtest_device.py', 'airtest_tasks.py', 'airtest_login.py', 'airtest_keybind.py', 'config.py']:
    with open(f) as fh:
        ast.parse(fh.read())
    print(f'{f}: syntax OK')
"
# Expected: Each file reports syntax OK
```

- [ ] **Step 4: Commit**

```bash
cd /Users/l/Desktop/Automatic-screenshot
git add -A
git commit -m "chore: final verification — all imports resolve, 19 tasks ported

Co-Authored-By: Claude <noreply@anthropic.com>"
```
