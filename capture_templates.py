"""模板图采集工具 — 截取全屏后交互式框选 ROI 保存为模板图。

使用方法:
    python capture_templates.py              # 截取全部 3 张模板图
    python capture_templates.py --only back_arrow.png  # 只截指定模板
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from airtest_device import AirtestDevice, _auto_detect_device
from config import DEVICE_SERIAL, TEMPLATES_DIR

# 需要采集的模板图清单
TEMPLATES = [
    "back_arrow.png",
    "nobility_icon.png",
    "popup_close.png",
]

TEMPLATES_DIR = Path(TEMPLATES_DIR)


def select_roi(img: np.ndarray, name: str) -> tuple[int, int, int, int] | None:
    """用 OpenCV selectROI 交互式框选区域。

    Returns:
        (x, y, w, h) | None (用户取消)
    """
    # 缩小大图以便屏幕上显示
    h, w = img.shape[:2]
    scale = min(800 / max(w, h), 1.0)
    if scale < 1.0:
        display = cv2.resize(img, (int(w * scale), int(h * scale)))
    else:
        display = img.copy()
        scale = 1.0

    roi = cv2.selectROI(f"框选: {name}  (按 Enter 确认，按 Esc 跳过)", display, False)
    cv2.destroyAllWindows()

    x, y, rw, rh = roi
    if rw == 0 and rh == 0:
        return None  # 用户取消

    # 还原到原始分辨率
    x = int(x / scale)
    y = int(y / scale)
    rw = int(rw / scale)
    rh = int(rh / scale)
    return x, y, rw, rh


def capture_templates(device: AirtestDevice, only: list[str] | None = None) -> list[str]:
    """交互式采集模板图。返回成功采集的文件名列表。"""
    targets = only or TEMPLATES
    captured = []

    # 截取全屏
    print("正在截取当前画面...")
    img = device._raw_screencap()
    if img is None:
        print("❌ 截屏失败")
        return captured

    # OpenCV 需要 BGR 格式
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    for name in targets:
        print(f"\n--- 框选: {name} ---")
        roi = select_roi(frame, name)
        if roi is None:
            print(f"  ⏭ 跳过 {name}")
            continue

        x, y, w, h = roi
        crop = frame[y:y + h, x:x + w]
        filepath = TEMPLATES_DIR / name
        cv2.imwrite(str(filepath), crop)
        size_kb = filepath.stat().st_size / 1024
        print(f"  ✅ 已保存: {filepath} ({w}x{h}, {size_kb:.1f} KB)")
        captured.append(name)

    return captured


def main():
    parser = argparse.ArgumentParser(description="模板图采集工具")
    parser.add_argument(
        "--only", nargs="+",
        help="只采集指定模板，例如: --only back_arrow.png popup_close.png"
    )
    args = parser.parse_args()

    # 连接设备
    print("连接设备...")
    try:
        device = AirtestDevice()
        device.connect()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)

    captured = capture_templates(device, only=args.only)

    if captured:
        print(f"\n✅ 采集完成: {len(captured)}/{len(args.only or TEMPLATES)} 张模板图")
    else:
        print("\n⚠ 未采集任何模板图")


if __name__ == "__main__":
    main()
