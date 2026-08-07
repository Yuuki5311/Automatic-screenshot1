# 模拟器连接修复设计

**日期**: 2026-08-07
**状态**: 待实施
**关联**: [[2026-08-06-airtest-migration-design]]

## 背景

Airtest 迁移后，连接 MuMu 12 模拟器存在两个问题：

1. **设备序列号硬编码为 `emulator-5554`** — MuMu 重启后 `adb devices` 可能返回不同的序列号，导致 `wait-for-device` 超时
2. **截屏方式默认 MINICAP** — `snapshot()` 返回 None，OCR 无法获取画面，每帧都输出「OCR 截图失败」

本设计解决这两个问题：设备自动检测 + 截屏方式固定为 JAVACAP。

## 方案

- `config.py`：`DEVICE_SERIAL = None` 表示自动检测，新增 `CAP_METHOD = "JAVACAP"`
- `airtest_device.py`：`connect()` 方法中调用 `_auto_detect_device()` 自动获取设备序列号；`init_device` 传入 `cap_method="JAVACAP"`

### 自动检测

`_auto_detect_device()` 调用 Airtest 内置的 ADB 接口 (`ADB().devices()`)，过滤 `state == "device"`，返回第一个设备的序列号。未检测到设备时抛出明确的 `RuntimeError`。

### 截屏方式

| 方式 | 原理 | MuMu 12 |
|------|------|---------|
| MINICAP（默认）| 推送 C 二进制截屏 | 不兼容（snapshot 返回 None） |
| **JAVACAP** | 设备 Java API 截屏 | 兼容 |
| ADBCAP | `adb shell screencap -p` | 兼容但最慢 |

选择 JAVACAP，基于 Android 系统原生 Yosemite 截屏服务。

## 改动文件

### `config.py`

```python
DEVICE_SERIAL = None          # None = 从 adb devices 自动检测
CAP_METHOD = "JAVACAP"        # MuMu 12 兼容的截屏方式
```

### `airtest_device.py`

```python
class AirtestDevice:
    def connect(self):
        if self._connected:
            return
        serial = DEVICE_SERIAL or self._auto_detect_device()
        if not serial:
            raise RuntimeError("未检测到 Android 设备，请确认 MuMu 12 已启动")
        init_device("Android", serial, cap_method=CAP_METHOD)
        self._connected = True
        log.info(f"设备已连接: {serial} (截屏: {CAP_METHOD})")

    @staticmethod
    def _auto_detect_device() -> str | None:
        from airtest.core.android.adb import ADB
        devices = ADB().devices(state="device")
        if devices:
            return devices[0][0]
        return None
```

### 错误处理

- 无设备 → `RuntimeError("未检测到 Android 设备，请确认 MuMu 12 已启动")`
- 截屏失败 → 保持现有 `snapshot() is None` 的 warn 日志，不崩溃

## 不涉及的改动

- OCR 逻辑、登录流程、截图任务 — 均不变
- GUI — 不变
- `take_screenshot()` — 不变，仍用 `snapshot(filename=...)` 保存到文件
