# 模板图准备指南

> **当前架构（Airtest 迁移后）：导航以 OCR 文字识别为主，模板匹配仅用于少量纯图标按钮。**

模板图存放在 `airtest_templates/` 目录（不是本 `templates/` 目录）。

## 所需模板图清单（仅 2 张）

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `back_arrow.png` | 返回箭头 | 万象图鉴首页点击返回（[airtest_tasks.py:323](../airtest_tasks.py#L323)） |
| `nobility_icon.png` | 贵族图标 | 主界面点击进入贵族页（[airtest_tasks.py:445](../airtest_tasks.py#L445)） |

其余所有导航操作（进入图鉴、切换标签、点击商城等）均使用 **EasyOCR 文字识别**（`ClickText`），不需要模板图。

## 截取方法

### 方式一：AirtestIDE（推荐）

1. 打开 AirtestIDE，连接 MuMu 模拟器
2. 用 AirtestIDE 的「截屏」获取游戏画面
3. 在截图上框选目标按钮，右键 →「保存选中区域」
4. 保存到 `airtest_templates/` 目录，命名为对应文件名

### 方式二：手动截取

1. 用 MuMu 模拟器截图功能截取游戏画面
2. 用画图工具裁剪出目标按钮，周围保留 30~50px 游戏 UI 背景以增加匹配唯一性
3. 保存到 `airtest_templates/` 目录

### 匹配阈值

- 默认 `threshold=0.7`（在 [airtest_tasks.py](../airtest_tasks.py) 中设定）
- 模板图越精确，匹配成功率越高

## 截图输出

脚本运行后截图保存在 [`screenshots/`](../screenshots/) 目录，文件名按任务名命名（如 `skin_illustrated.png`、`lottery_tab.png` 等）。

> **注意：** `screenshots/` 中的截图是本项目的**产物**（游戏截图），不是模板图，不要混淆。
