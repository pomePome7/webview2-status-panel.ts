# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import PyQt6
import PyQt6.QtCore import QLibraryInfo

# PyQt6 のインストールパスを取得
pyqt6_dir = os.path.dirname(PyQt6.__file__)

# Qt6の基本ディレクトリを取得（環境によって異なる可能性がある）
# Qt関連のフォルダパスを構築 (Qt6 の場合)
try:
    qt_base_dir = os.path.dirname(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath))
    qt6_dir = os.path.join(qt_base_dir, "Qt6")
    if not os.path.exists(qt6_dir):
        qt6_dir = os.path.join(pyqt6_path, "Qt6")
    print(f"Qt6ディレクトリ: {qt6_dir}")
except Exception as e:
    print(f"Qt6パス検出エラー: {e}")
    # フォールバック
    qt6_dir = os.path.join(pyqt6_path, "Qt6")

# WebEngineProcess.exeの位置を確認
webengine_process = None
possible_locations = [
    os.path.join(qt6_dir, "bin", "QtWebEngineProcess.exe"),
    os.path.join(qt6_dir, "libexec", "QtWebEngineProcess.exe")
]
for location in possible_locations:
    if os.path.exists(location):
        webengine_process = location
        break

if webengine_process:
    print(f"QtWebEngineProcess.exe を発見: {webengine_process}")
else:
    print("警告: QtWebEngineProcess.exe が見つかりませんでした")

# 追加するファイルのリストを作成
added_files = []

# リソースディレクトリの確認と追加
resources_dir = os.path.join(qt6_dir, "resources)
if os.path.exists(resources_dir):
    added_files.append((resources_dir, "PyQt6/Qt6/resources"))

# 翻訳ファイルの確認と追加
translations_dir = os.path.join(qt6_dir, "translations")
if os.path.exists(translations_dir):
    added_files.append((translations_dir, "PyQt6/Qt6/translations"))

# プラグインの確認と追加
plugins_dir = os.path.join(qt6_dir, "plugins")
if os.path.exists(plugins_dir):
    added_files.append((plugins_dir, "PyQt6/Qt6/plugins"))

# WebEngineProcess.exeの追加
if webengine_process:
    target_dir = os.path.dirname(webengine_process).replace(qt6_dir, "PyQt6/Qt6")
    added_files.append((webengine_process, os.path.join(target_dir, "QtWebEngineProcess.exe")))

# 設定ファイルのパスを現在の作業ディレクトリに基づいて修正
settings_path = os.path.join(os.getcwd(), "settings.py")
if not os.path.exists(settings_path):
    settings_path = "settings.py"

# ChromeDriverのパスを動的に検出
chromedriver_path = None
possible_driver_paths = [
    "chromedriver.exe",
    os.path.join(os.getcwd(), "chromedriver.exe")
]
for path in possible_driver_paths:
    if os.path.exists(path):
        chromedriver_path = path
        break

datas = added_files
if chromedriver_path:
    datas.append((chromedriver_path, '.'))
datas.append((settings_path, '.'))
    


added_files = [
    # Qt resources (pak ファイルなど)
    (os.path.join(qt_base_dir, "resources"), "PyQt6/Qt6/resources"),
    # Qt translations (ロケールファイルなど)
    (os.path.join(qt_base_dir, "translations"), "PyQt6/Qt6/translations"),
    # Qt plugins (プラットフォームプラグインなど、必要に応じて)
    (os.path.join(qt_base_dir, "plugins"), "PyQt6/Qt6/plugins"),
    # QtWebEngineProcess.exe (場所は環境により異なる場合あり bin or libexec)
    (os.path.join(qt_base_dir, "bin", "QtWebEngineProcess.exe"), "PyQt6/Qt6/bin"),
    # もし libexec にあるなら:
    # (os.path.join(qt_base_dir, "libexec", "QtWebEngineProcess.exe"), "PyQt6/Qt6/libexec"),
]


a = Analysis(
    ['mein.py', 'settings.py'],
    pathex=[],
    binaries=[],
    datas=[('path/to/your/chromedriver.exe', '.'), ('settings.py', '.')],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtNetwork', # Cookie操作などで必要
        'PyQt6.sip', # 念のため
        'PyQt6.QtCore.QSettings',
        'selenium',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.common.exceptions',
        'encodings.utf_8',     # 日本語サポート用
        'encodings.ascii',     # 基本エンコーディング
        'encodings.idna',      # URL処理用
        'requests',            # ChromeDriver自動ダウンロード用
        'zipfile',             # ChromeDriver自動ダウンロード用
        'io',                  # BytesIO用
        'selenium.webdriver.common.keys',  # Keys クラス用
        'platform',             # OS検出用
        're',                   # 正規表現処理用
        'subprocess',           # プロセス実行用
        'winreg',               # Windowsレジストリ操作用（Chrome検出）
        'urllib3',              # requests の依存関係
        'certifi',              # SSL証明書（requests関連）
        'idna',                 # 国際化ドメイン名（requests関連）
        'charset_normalizer',   # 文字セット正規化（requests関連）
    ],
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
    [],
    exclude_binaries=True,
    name='myapp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # デバッグ中はTrueにして問題を確認しやすくする
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries += [('PyQt6/Qt6/bin/QtWebEngineProcess.exe', 'env/Lib/site-packages/PyQt6/Qt6/bin/QtWebEngineProcess.exe', 'BINARY')],
    a.datas += Tree('env/Lib/site-packages/PyQt6/Qt6/resources', prefix='PyQt6/Qt6/resources'),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='myapp',
)
