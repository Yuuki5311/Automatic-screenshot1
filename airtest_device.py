"""Airtest 设备操作封装。

替代旧 Navigator：提供模板点击、等待、截图、返回键等操作。
截屏使用 adb exec-out screencap -p（绕过 Airtest snapshot，MuMu 12 兼容）。
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from airtest.core.api import (
    Template,
    device,
    exists,
    init_device,
    keyevent,
    start_app,
    stop_app,
    swipe,
    touch,
    wait,
)
from airtest.aircv.error import FileNotExistError
from airtest.core.error import TargetNotFoundError

from config import (
    CAP_METHOD,
    DEFAULT_THRESHOLD,
    DEVICE_SERIAL,
    SCREENSHOTS_DIR,
    TEMPLATES_DIR,
    TEMPLATE_TIMEOUT,
    writable_path,
)
from logger import get_logger

log = get_logger()

# MuMu 12 默认 ADB 端口
_MUMU_ADB_ADDR = "127.0.0.1:5555"


def _auto_detect_device() -> str | None:
    """从 adb devices 自动获取第一个设备序列号。

    如果未检测到设备，会尝试 adb connect 到 MuMu 12 默认端口。
    """
    from airtest.core.android.adb import ADB
    adb = ADB()
    devices = adb.devices(state="device")
    if not devices:
        adb.cmd(f"connect {_MUMU_ADB_ADDR}", device=False)
        devices = adb.devices(state="device")
    if devices:
        return devices[0][0]
    return None


class AirtestDevice:
    """封装 Airtest 设备操作，对应旧项目的 Navigator。"""

    def __init__(self) -> None:
        self._connected = False
        self._serial: str = ""
        self._templates_dir = Path(TEMPLATES_DIR)

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """连接 Android 模拟器设备，自动检测设备并选用兼容的截屏方式。"""
        if self._connected:
            return
        serial = DEVICE_SERIAL or _auto_detect_device()
        if not serial:
            raise RuntimeError("未检测到 Android 设备，请确认 MuMu 12 已启动")
        init_device("Android", serial, cap_method=CAP_METHOD)
        self._serial = serial
        self._connected = True
        log.info(f"设备已连接: {serial} (截屏: adb screencap)")

    def disconnect(self) -> None:
        """断开设备连接（Airtest 没有显式 disconnect，此方法为占位）。"""
        self._connected = False
        self._serial = ""
        log.info("设备连接标记已清除")

    # ------------------------------------------------------------------
    # 截屏（绕过 Airtest snapshot，直接使用 adb screencap）
    # ------------------------------------------------------------------

    def _raw_screencap(self) -> "PIL.Image.Image | None":
        """使用 adb exec-out screencap 截取 PNG 到内存，返回 PIL Image。

        Airtest 的 snapshot() 在 MuMu 12 上所有 cap_method 均返回 None，
        因此直接调用 adb 命令截屏。
        """
        import io
        from PIL import Image

        try:
            proc = subprocess.run(
                ["adb", "-s", self._serial, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if proc.returncode != 0 or not proc.stdout:
                log.warning(f"adb screencap 失败 (rc={proc.returncode})")
                return None
            return Image.open(io.BytesIO(proc.stdout))
        except Exception as e:
            log.warning(f"adb screencap 异常: {e}")
            return None

    def take_screenshot(self, filename: str) -> str:
        """截图保存到 screenshots 目录。

        Returns:
            str: 截图文件绝对路径。
        """
        img = self._raw_screencap()
        if img is None:
            log.error(f"截图失败: {filename}")
            return ""
        output_dir = Path(writable_path(SCREENSHOTS_DIR))
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename
        img.save(str(filepath))
        log.info(f"截图已保存: {filepath}")
        return str(filepath)

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
        except (TargetNotFoundError, FileNotExistError, OSError):
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
        except (TargetNotFoundError, FileNotExistError, OSError):
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
        try:
            return bool(exists(tpl))
        except (TargetNotFoundError, FileNotExistError, OSError):
            log.warning(f"模板检查失败 (文件缺失或错误): {template_name}")
            return False

    # ------------------------------------------------------------------
    # OCR 文字操作  (替代模板匹配，无需模板图)
    # ------------------------------------------------------------------

    def _get_ocr(self):
        """懒加载 EasyOCR 单例，首次调用需下载模型（10-30s）。"""
        if not hasattr(self, "_ocr") or self._ocr is None:
            import easyocr
            log.info("初始化 EasyOCR (首次加载较慢，约 10-30s)...")
            self._ocr = easyocr.Reader(["ch_sim"], gpu=False)
            log.info("EasyOCR 初始化完成")
        return self._ocr

    def _ocr_screen(self) -> list[tuple[str, float, int, int]]:
        """对当前画面运行 OCR，返回 [(文字, 置信度, 中心x, 中心y), ...] 列表。"""
        import numpy as np

        img = self._raw_screencap()
        if img is None:
            log.warning("OCR 截图失败")
            return []

        ocr = self._get_ocr()
        results = ocr.readtext(np.array(img))
        if not results:
            return []

        detections: list[tuple[str, float, int, int]] = []
        for detection in results:
            box = detection[0]    # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = detection[1]   # 'text'
            conf = detection[2]   # confidence
            cx = int((box[0][0] + box[2][0]) / 2)
            cy = int((box[0][1] + box[2][1]) / 2)
            detections.append((text, conf, cx, cy))
        return detections

    def find_text(
        self,
        keyword: str,
        threshold: float = 0.8,
    ) -> tuple[int, int] | None:
        """在当前画面查找包含 keyword 的文字，返回其包围盒中心坐标。

        匹配规则：OCR 识别文字包含 keyword（子串匹配）。
        多个匹配时取置信度最高的。

        Returns:
            (x, y) | None
        """
        detections = self._ocr_screen()
        best = None
        best_conf = 0
        for text, conf, cx, cy in detections:
            if keyword in text and conf >= threshold and conf > best_conf:
                best = (cx, cy)
                best_conf = conf
        if best:
            log.info(f"OCR 找到 '{keyword}' → ({best[0]}, {best[1]}) 置信度={best_conf:.2f}")
        else:
            log.debug(f"OCR 未找到 '{keyword}' (共识别 {len(detections)} 条文字)")
        return best

    def click_text(
        self,
        keyword: str,
        timeout: float = 10.0,
        threshold: float = 0.8,
    ) -> bool:
        """循环 OCR 直到找到 keyword 文字并点击。

        每 0.5s 重新截图 + OCR，直到超时。

        Returns:
            bool: 成功点击返回 True。
        """
        import time as _time
        from airtest.core.api import touch

        deadline = _time.time() + timeout
        while _time.time() < deadline:
            pos = self.find_text(keyword, threshold=threshold)
            if pos is not None:
                touch(pos)
                log.info(f"OCR 点击: '{keyword}' @ ({pos[0]}, {pos[1]})")
                return True
            _time.sleep(0.5)
        log.warning(f"OCR 点击超时 ({timeout}s): '{keyword}'")
        return False

    def wait_text(
        self,
        keyword: str,
        timeout: float = 10.0,
        threshold: float = 0.8,
    ) -> bool:
        """等待文字出现，不点击。

        Returns:
            bool: 文字出现返回 True。
        """
        import time as _time

        deadline = _time.time() + timeout
        while _time.time() < deadline:
            pos = self.find_text(keyword, threshold=threshold)
            if pos is not None:
                log.info(f"OCR 文字已出现: '{keyword}'")
                return True
            _time.sleep(0.5)
        log.warning(f"OCR 等待超时 ({timeout}s): '{keyword}'")
        return False

    def exists_text(
        self,
        keyword: str,
        threshold: float = 0.8,
    ) -> bool:
        """非阻塞检查文字是否存在。

        Returns:
            bool: 文字存在返回 True。
        """
        pos = self.find_text(keyword, threshold=threshold)
        return pos is not None

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
