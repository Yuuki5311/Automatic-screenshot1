"""Airtest 设备操作封装。

替代旧 Navigator：提供模板点击、等待、截图、返回键等操作。
"""

from __future__ import annotations

import time
from pathlib import Path

from airtest.core.api import (
    Template,
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
