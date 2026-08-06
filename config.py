"""全局配置常量。"""

# ---------------------------------------------------------------------------
# Airtest / MuMu 模拟器
# ---------------------------------------------------------------------------
DEVICE_URI = "Android://127.0.0.1:5037/127.0.0.1:7555"

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
