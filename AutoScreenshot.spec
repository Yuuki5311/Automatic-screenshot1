# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


def _has_pocoui() -> bool:
    """检测 pocoui 是否已安装（pocoui 为可选依赖，未安装时跳过收集）。"""
    try:
        import pocoui  # noqa: F401
    except ImportError:
        return False
    return True


# 收集 Airtest 数据文件（ADB 二进制等）
airtest_datas = collect_data_files('airtest')
pocoui_datas = collect_data_files('pocoui') if _has_pocoui() else []

# 模板目录
template_datas = []
templates_dir = Path('airtest_templates')
if templates_dir.is_dir():
    template_datas = [(str(p), str(p.relative_to('.'))) for p in templates_dir.rglob('*.png')]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=airtest_datas + pocoui_datas + template_datas,
    hiddenimports=[
        'airtest',
        'airtest.core',
        'airtest.core.api',
        'airtest.aircv',
        'airtest.aircv.template_matching',
        'pocoui',
        'cv2',
        'numpy',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'test',
        'pydoc',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AutoScreenshot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
