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
