"""坐标获取工具 — 截取画面后鼠标定位 + Enter 保存坐标。

使用方法:
    python get_coords.py
    鼠标移动定位 → 看到十字准心 → Enter 保存 → 继续下一个 → Esc 退出
"""

import sys

import cv2
import numpy as np

from airtest_device import AirtestDevice

coords: list[tuple[int, int]] = []
_cursor: tuple[int, int] = (0, 0)


def on_mouse(event, x, y, flags, param):
    """鼠标回调：只跟踪光标位置。"""
    global _cursor
    if event == cv2.EVENT_MOUSEMOVE:
        _cursor = (x, y)


def main():
    global _cursor

    # 连接设备
    print("连接设备...")
    try:
        device = AirtestDevice()
        device.connect()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)

    # 截屏
    print("截取当前画面...")
    img = device._raw_screencap()
    if img is None:
        print("❌ 截屏失败")
        sys.exit(1)

    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # 缩放大图以便显示
    h, w = frame.shape[:2]
    scale = min(1200 / max(w, h), 1.0)
    if scale < 1.0:
        display = cv2.resize(frame, (int(w * scale), int(h * scale)))
        print(f"画面已缩放: {w}x{h} → {int(w * scale)}x{int(h * scale)}")
    else:
        display = frame.copy()
        scale = 1.0

    print("\n鼠标定位 → Enter 保存 → 继续下一个 → Esc 退出\n")

    win_name = "坐标获取 — 鼠标定位, Enter 保存, Esc 退出"
    cv2.namedWindow(win_name)
    cv2.setMouseCallback(win_name, on_mouse)

    while True:
        # 绘制画面 + 十字准心 + 已保存坐标
        canvas = display.copy()

        # 已保存的坐标 (红点 + 序号)
        for i, (cx, cy) in enumerate(coords):
            sx, sy = int(cx * scale), int(cy * scale)
            cv2.circle(canvas, (sx, sy), 6, (0, 0, 255), -1)
            cv2.putText(canvas, f"#{i + 1}", (sx + 12, sy - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 当前光标位置 (绿色十字准心)
        cx, cy = _cursor
        real_x, real_y = int(cx / scale), int(cy / scale)
        cv2.line(canvas, (cx - 12, cy), (cx + 12, cy), (0, 255, 0), 1)
        cv2.line(canvas, (cx, cy - 12), (cx, cy + 12), (0, 255, 0), 1)
        cv2.putText(canvas, f"({real_x},{real_y})",
                    (cx + 15, cy - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        cv2.imshow(win_name, canvas)
        key = cv2.waitKey(50) & 0xFF

        if key == 13:  # Enter — 保存当前坐标
            real = (int(cx / scale), int(cy / scale))
            coords.append(real)
            print(f"  #{len(coords)} ({real[0]}, {real[1]}) 已保存")
        elif key == 8:  # Backspace — 撤销上一个
            if coords:
                removed = coords.pop()
                print(f"  撤销 #{len(coords) + 1} ({removed[0]}, {removed[1]})")
        elif key == 27:  # Esc — 退出
            break

    cv2.destroyAllWindows()

    if coords:
        print(f"\n✅ 已记录 {len(coords)} 个坐标:")
        for i, (cx, cy) in enumerate(coords):
            print(f"  ClickCoord({cx}, {cy}, desc=\"\"),")
    else:
        print("\n⚠ 未记录任何坐标")


if __name__ == "__main__":
    main()
