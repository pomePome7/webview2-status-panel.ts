# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import PyQt6.QtCore import QLibraryInfo

# PyQt6のリソースパスを取得
qt_dir = os.path.join(os.path.dirname(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath)), "Qt")
resources_path = os.path.join(qt_dir, "resources")
translations_path = os.path.join(qt_dir, "translations")
qtwebengine_resources_path = os.path.join(qt_dir, "resources", "qtwebengine_resources.pak")

# 追加する必要のあるデータファイル
datas = [
    (resources_path, "PyQt6/Qt6/resources"),
    (translations_path, "PyQt6/Qt6/translations"),
]
if os.path.exists(qtwebengine_resources_path):
    datas.append((qtwebengine_resources_path, "PyQt6/Qt6/resources"))

# WebEngineに必要な隠れた依存関係
hidden_imports = [
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtNetwork',
]

a = Analysis(
    ['mein.py'],
    pathex=[],
    binaries=[],
    datas=datas,  # 修正：データファイルを追加
    hiddenimports=hidden_imports,  # 修正：隠れた依存関係を追加
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='mein',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 修正：デバッグ中はコンソールを表示する
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
