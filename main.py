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
