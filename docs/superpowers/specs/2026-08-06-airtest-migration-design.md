# Airtest Migration Design

**Date:** 2026-08-06
**Status:** Approved
**Summary:** 将项目从 Selenium + CDP 驱动浏览器云游戏方案，切换为 Airtest + MuMu Android 模拟器原生方案。

---

## 目标

1. **增强图像识别精度** — 用 Airtest mstpl 多尺度匹配替代 OpenCV 单尺度模板匹配
2. **降低模板维护成本** — 用 AirtestIDE 可视化录制/裁剪替代手工截图管理
3. **切换到 Android 模拟器原生方案** — 不再依赖浏览器云游戏（gamer.qq.com）

---

## 架构

```
Tkinter GUI (保留，2 页：空闲 + 进度)
    │
Workflow Orchestrator (port from gui/app.py:_run_workflow)
    阶段1: 启动模拟器 + 连接设备
    阶段2: 启动王者荣耀 + 登录 + 跳过公告
    阶段3: 键位配置
    阶段4: 截图循环
    │
Airtest Device Layer (connect_device("Android://127.0.0.1:7555"))
    Template matching / touch() / swipe() / snapshot() / wait() / exists()
    │
MuMu Android Emulator (王者荣耀 .apk installed)
```

---

## 模块变更

### 删除的模块

| 文件 | 原因 |
|---|---|
| `browser.py` | Selenium/CDP 浏览器驱动，不再需要 |
| `navigator.py` | OpenCV 模板匹配 + CDP 鼠标注入，Airtest 替代 |
| `login.py` | 网页 QQ 扫码登录，Airtest 原生 app 内授权登录替代 |
| `ui_state.py` | FSM 状态分类器，Airtest wait/exists 替代 |
| `ui_loop.py` | FSM 感知循环，线性截图循环替代 |
| `game_launcher.py` | gamer.qq.com 云游戏启动，模拟器直接启动 app 替代 |
| `client_launcher.py` | GamerUFO 桌面客户端，不再需要 |
| `screenshotter.py` | Selenium 截图，Airtest snapshot() 替代 |
| `screenshot_click.py` | 两阶段点击确认，Airtest wait + assert 替代 |
| `click_confirm.py` | ROI 效果验证，Airtest assert_exists 替代 |
| `popup_monitor.py` | 异步弹窗关闭，Airtest exists + touch 替代 |
| `calibrate_coords.json` | 坐标回退，Airtest 模板定位不需要坐标 |
| `templates/*.png` | 浏览器截取的模板，模拟器上重新截取 |

### 新增的模块

| 文件 | 职责 |
|---|---|
| `airtest_device.py` | 封装 Airtest 设备连接、模板点击、等待、截图、返回键等操作 |
| `airtest_tasks.py` | ScreenshotTask/ClickTemplate/GuardAction/SwipeAction 数据类 + 截图循环执行器 |
| `airtest_login.py` | 模拟器内王者荣耀 QQ 授权登录流程 |
| `airtest_keybind.py` | 4 步键位配置（编辑→定位→保存→关闭） |
| `airtest_templates/*.png` | AirtestIDE 截取的 40-50 张模板，覆盖登录、导航、弹窗关闭 |

### 保留并精简的模块

| 文件 | 改动 |
|---|---|
| `main.py` | 不变 |
| `config.py` | 删除浏览器相关常量（CDP 配置、反检测参数），保留路径/超时/截图配置 |
| `gui/app.py` | 删除扫码页，精简为 2 页（空闲 + 进度），工作流线程替换后端 |
| `process_cleanup.py` | 保留（Windows 进程清理逻辑不变） |

---

## 核心实现

### 模板管理

- 所有模板在模拟器上用 AirtestIDE 重新截取
- 模板按页面分组：`login/`、`hall/`、`hero/`、`skin/`、`popup/` 等
- Airtest `Template(threshold=0.7)` 内联阈值，不再需要集中式阈值配置

### 任务定义格式

```python
@dataclass
class ScreenshotTask:
    name: str
    setup: list[Action]
    shot_delay: float = 1.0
    teardown_back: int = 0

class ClickTemplate:      # 模板点击
    template: str
    desc: str = ""
    timeout: float = 10.0

class GuardAction:         # 条件弹窗关闭，对应旧 __guard__
    template: str
    dismiss_template: str

class SwipeAction:         # 列表滚动
    direction: str
    duration: float = 0.3
```

### 可靠性机制

| 旧机制 | Airtest 等价 |
|---|---|
| ROI 两阶段确认 (ROI 前后对比 ≥0.90) | `wait(Template, timeout)` + `assert_exists(Template)` |
| FSM 回退 (rewind_to_previous_step) | `try/except TargetNotFoundError` → `keyevent("BACK")` → 重试 |
| UI 状态分类器 (UiState enum + 优先级链) | `exists(Template)` 逐个检查 — 原生 app 比云游戏视频流更确定 |

### 登录流程

```
启动王者荣耀 → 点击 QQ 登录 → QQ 授权 → 关闭公告 → 进入大厅
```

依赖前置条件：MuMu 模拟器内预装 QQ 并保持登录状态，首次需手动授权。

### 截图执行循环

```python
def run_screenshot_loop(device, tasks):
    for task in tasks:
        # 1. 执行前置操作
        for action in task.setup:
            execute_action(device, action)
        # 2. 等待渲染
        sleep(task.shot_delay)
        # 3. 截图
        device.take_screenshot(f"{task.name}.png")
        # 4. 回退
        for _ in range(task.teardown_back):
            device.press_back()
        # 5. 弹窗扫描
        scan_popups(device)
```

### GUI

- 删除扫码页
- 空闲页：启动 MuMu 按钮 + 开始运行按钮
- 进度页：不变（当前任务 + 日志输出）
- 通过 Queue 接收进度消息，100ms 轮询

### PyInstaller 打包

- 保留 GitHub Actions Windows 构建
- `datas` 更新：`airtest_templates/` + Airtest ADB 工具链
- `requirements.txt`：`selenium`、`opencv-python` 替换为 `airtest`、`pocoui`

---

## 前置依赖

1. MuMu 12 模拟器安装
2. 模拟器内安装王者荣耀 APK + QQ 并登录
3. QQ 首次授权王者荣耀
4. `pip install airtest pocoui`
