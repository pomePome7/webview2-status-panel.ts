# -*- coding: utf-8 -*-
import sys
import os
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.gl=false'
import shutil                  # cleanup メソッドで使用
import re
import json                    # エクスポート・インポート機能用
import time                    # time.sleep用
import zipfile                 # ファイル圧縮用
import subprocess              # プロセス実行用
import requests                # HTTP通信用
import platform                # OS検出用
import traceback               # エラー詳細表示用
import winreg                  # Windowsレジストリ操作用
from io import BytesIO         # バイナリデータ処理用
from app_ui import MainUI

# 2025/06/30importを書き換え
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
                            QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QLabel,
                            QMessageBox, QProgressBar, QComboBox, QInputDialog, QFrame,
                            QTextEdit, QSplitter, QGroupBox, QGridLayout, QStackedWidget,
                            QTabWidget, QSpinBox, QDateEdit, QTimeEdit, QFileDialog, QDialog) # 追加: QFileDialog,新しくQDialogを追加

# 2025/06/30 既存のPyQt6.QtCore import文を書き換え
from PyQt6.QtCore import (QUrl, QThread, pyqtSignal, QLibraryInfo, Qt, QTimer,
                        QSettings, QDateTime, QDate, QTime) # QDateTime を追加→打ち込み変更した後、日時関連は既に追加済み
# QtWebEngineCore は WebView 初期化時に必要
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

# QtNetwork（ネットワーク） は Cookie 設定に必要
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtGui import QDesktopServices, QFont  # QtGuiからインポート

# 2025/06/30 settings importを書き換え
# Selenium 関連のインポート
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException # WebDriverException,
from selenium.webdriver.chrome.service import Service


# webdriver_manager はフォールバック用に残す
from webdriver_manager.chrome import ChromeDriverManager
# ローカルモジュール
from settings import AppSettings, SettingsDialog, AccountDialog, UserPreferencesManager # UserPreferencesManagerを追加
from app_ui import LogStatusTab

# --- PyQt6 リソースパス設定 (PyInstaller用) ---
try:
    # Qt6のパスを取得
    qt_dir = os.path.dirname(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath))

    # 環境変数を設定
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_dir, 'plugins').replace('\\', '/')
    os.environ['QT_TRANSLATIONS_PATH'] = os.path.join(qt_dir, 'translations').replace('\\', '/')

    # WebEngineリソースパスを設定（これが重要）
    webengine_path = os.path.join(qt_dir, 'resources')
    if os.path.exists(webengine_path):
        os.environ['QTWEBENGINE_RESOURCES_PATH'] = webengine_path.replace('\\', '/')
        print(f"QTWEBENGINE_RESOURCES_PATH set to: {os.environ['QTWEBENGINE_RESOURCES_PATH']}")
    else:
        print(f"WebEngineリソースパスが見つかりません: {webengine_path}")
except Exception as e:
    print(f"Qt環境変数設定エラー: {e}")

# QLibraryInfoを利用してPyQt6のパスを取得
qt_dir = os.path.join(os.path.dirname(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath)), "Qt")
resources_path = os.path.join(qt_dir, "resources")
translations_path = os.path.join(qt_dir, "translations")
qtwebengine_resources_path = os.path.join(qt_dir, "resources", "qtwebengine_resources.pak")

datas =[
    (resources_path, "PyQt6/Qt/resources"),
    (translations_path, "PyQt6/Qt/translations"),
]
if os.path.exists(qtwebengine_resources_path):
    datas.append((qtwebengine_resources_path, "PyQt6/Qt/resources"))
# リソースパス取得関数
def get_resource_path(relative_path):
    """実行ファイルからの相対パスでリソースのパスを取得"""
    try:
        # PyInstallerバンドルの場合
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        # 通常の実行の場合
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Selenium スレッドクラス ---
class SeleniumThread(QThread):
    def __init__(self):
        super().__init__()
        self.driver = None
    """プロフェッショナル自動ログインシステム - 複数対応
    Seleniumを使用したECサイト自動ログインスレッド
    処理フロー:
    1.初期化
    2.環境チェック
    3.WebDriver起動
    4.各ECサイトへのログイン
    5.Cookie同期
    6.ユーザー操作待機
    7.クリーンアップ
    """

    # シグナル定義
    finished = pyqtSignal()
    status_update = pyqtSignal(str)  # ステータス更新用シグナル
    login_success = pyqtSignal(bool)  # ログイン成功時用シグナル
    cookies_ready = pyqtSignal(list, str) # Cookie送信用シグナル
    url_update = pyqtSignal(str) # URL更新用シグナル
    # 上部のコードを追加2025/07/21
    log_message = pyqtSignal(str)  # ログメッセージを送信するシグナル
    browser_page_source = pyqtSignal(str) # ブラウザのページソース更新用シグナル
    account_success = pyqtSignal(str, str) # アカウント、サイト成功通知
    error_occurred = pyqtSignal(str)  # エラー発生時用シグナル

    def __init__(self, web_engine_view, account_data, selected_sites, app_settings=None): # ここを修正
        super().__init__()
        # self.web_engine_view = web_engine_view
        self.web_engine_view = None # 一時的に無効化
        self.account_data = account_data
        self.selected_sites = selected_sites
        self.app_settings = app_settings # ★2025/11/01追加
        self.driver = None
        self.is_running = True
        self.session_valid = False
        self.profile_dir = None
        self.should_stop = False # 追加

    def run(self):
        """メインの実行処理
        【順次処理フロー】
        Step 1: 初期化・ログ出力
        Step 2: 環境チェック
        Step 3: WebDriver起動
        Step 4: ECサイトログイン処理
        Step 5: 後処理・待機
        Step 6: クリーンアップ
        """
        try:
            # アカウント情報表示
            # メイン実行処理の整理版を行う2025/09/04
            account_display = self.account_data.get('nickname', self.account_data['account_id'])
            self.log_message.emit(f"👤 使用アカウント: {account_display}")
            self.log_message.emit(f"🏪 対象サイト: {', '.join(self.selected_sites)}")

            # システム環境チェック.check_chrome_installation()をコメントアウトするかも
            self.status_update.emit("システム環境をチェック中...")
            if not self.check_chrome_installation():
                self.error_occurred.emit("Chromeがインストールされていません。")
                return

            # ChromeDriver準備
            if not self.setup_chrome_driver():
                return

            # 各ECサイトへのログイン処理
            overall_success = False
            for site in self.selected_sites:
                if self.should_stop:
                    break

                self.log_message.emit(f"📋 {site} ログイン処理開始...")

                # サイト別のログイン処理
                success = False
                if site == "楽天市場":
                    success = self.login_to_rakuten_with_cookies()
                elif site == "Amazon":
                    success = self.login_to_amazon_with_cookies()
                elif site == "Yahoo!ショッピング":
                    success = self.login_to_yahoo_with_cookies()

                if success:
                    overall_success = True
                    self.status_update.emit(f"✅ {site} ログイン成功！")
                    self.account_success.emit(account_display, site)

                    # Cookie同期
                    time.sleep(2)
                    self.sync_cookies_to_webengine(site)
                else:
                    self.status_update.emit(f"❌ {site} ログイン失敗")

            self.login_success.emit(overall_success)

            # 最終段階,待機処理
            self.status_update.emit("ログイン完了 - ブラウザ待機中...")
            # ブラウザが閉じられるまで待機
            self.wait_for_termination()

        except Exception as e:
            self.error_occurred.emit(f"予期しないエラー: {str(e)}")
            self.log_message.emit(f"致命的なエラー: {str(e)}")
        finally:
            self.cleanup()
            self.finished.emit()

        # TODO:setup_chrome_driver メソッドも webdriver-manager を使用した実装に更新する必要がある
    def setup_chrome_driver(self):
        """Chromeドライバセットアップ"""
        try:
            self.status_update.emit("ChromeDriverを準備中...")

            # ChromeDriverManagerを使用して自動的にドライバーを取得
            from webdriver_manager.chrome import ChromeDriverManager
            # from selenium.webdriver.chrome.service import Service
            chrome_driver_path = ChromeDriverManager().install()
            self.log_message.emit(f"✅ ChromeDriver取得成功: {chrome_driver_path}")

            # Chrome起動オプションを設定
            chrome_options = webdriver.ChromeOptions()

            # 競合回避（固定ポートに変更）
            chrome_options.add_argument("--remote-debugging-port=9223")  # 0 → 9223 に変更

            # Bot検出を回避
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            # ユーザーっぽいUser-Agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # windowサイズ（人間らしい操作のため）
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--start-maximized") # ECサイトは大画面で操作

            # cookie・セッション保持
            chrome_options.add_argument("--profile-directory=Default")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")

            # 安定性向上
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")  # GPU無効化・または安定性のための補助

            # chrome_options.add_argument("--disable-web-security")
            # chrome_options.add_argument("--disable-features=VizDisplayCompositor")

            # ログイン特化設定
            # パスワード保存ダイアログを無効化
            chrome_options.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2  # 通知無効
            })

            # 独立プロファイル作成
            import tempfile
            self.profile_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")

            # WebDriver起動
            service = Service(chrome_driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)


            # ECサイトログイン用JavaScript
            self.driver.execute_script("""
                // Bot検出を完全回避
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

                // 実ブラウザっぽく偽装
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ja-JP', 'ja', 'en-US', 'en']});

                // 人間らしいマウス操作をシミュレート
                document.addEventListener('mousemove', function(e) {
                    window.lastMouseMove = Date.now();
                });
            """)

            self.log_message.emit("ECサイトログイン用Chrome準備完了")
            return True

        except Exception as e:
            self.error_occurred.emit(f"WebDriver起動失敗: {str(e)}")
            self.log_message.emit(f"ChromeDriver起動エラー: {str(e)}")
            return False

    def stop(self):
        """スレッドの停止"""
        self.should_stop = True
        self.log_message.emit("⏹️ 停止要求を受けました")

    def login_to_rakuten_with_cookies(self):
        """楽天市場ログイン処理"""
        try:
            self.log_message.emit("楽天市場ログインページに移動中...")

            # ログインぺー字に移動
            login_url = "https://grp01.id.rakuten.co.jp/rms/nid/vc?__event=login&service_id=top"
            self.driver.get(login_url)

            # ページ読み込み完了まで待機
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 人間らしい待機
            import random
            time.sleep(random.uniform(2, 4))

            self.log_message.emit("現在のURL: " + self.driver.current_url)

            # ユーザーID入力フィールドを探す
            username_field = None
            username_selectors = [
                (By.ID, "userid"),
                (By.ID, "userid"),
                (By.ID, "loginInner_u"),
                (By.NAME, "u"),
                (By.CSS_SELECTOR, "input[placeholder*='ユーザ']"),
                (By.CSS_SELECTOR, "input[type='text'][name='u']"),
                (By.XPATH, "//input[@type='text']")
            ]

            for method, selector in username_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((method, selector))
                    )
                    self.log_message.emit(f"✅ ユーザーIDフィールド発見: {method}={selector}")
                    break
                except:
                    continue

            if not username_field:
                self.log_message.emit("❌ ユーザーIDフィールドが見つかりません")
                return False


            # 人間らしいタイピング
            username_field.clear()
            # 1文字ずつ入力（人間らしく）
            for char in self.account_data['account_id']:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            self.log_message.emit("✅ ユーザーID入力完了")

            # パスワードフィールドを探す
            password_field = None
            password_selectors = [
                (By.ID, "passwd"),
                (By.ID, "loginInner_p"),
                (By.NAME, "p"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@type='password']")
            ]

            for metbod, selector in password_selectors:
                try:
                    password_field = self.driver.find_element(metbod, selector)
                    self.log_message.emit(f"✅ パスワードフィールド発見: {metbod}={selector}")
                    break
                except:
                    continue
            if not password_field:
                self.log_message.emit("❌ パスワードフィールドが見つかりません")
                return False

            # パスワード入力（人間らしく）
            password_field.clear()
            for char in self.account_data['password']:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            self.log_message.emit("✅ パスワード入力完了")

            # 人間らしい待機
            time.sleep(random.uniform(1, 2))

            # ログインボタンクリック
            login_button = None
            login_selectors = [
                (By.XPATH, "//input[@value='ログイン']"),
                (By.XPATH, "//button[contains(text(), 'ログイン')]"),
                (By.NAME, "submit"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']")
            ]

            for metbod, selector in login_selectors:
                try:
                    login_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((metbod, selector))
                    )
                    self.log_message.emit(f"✅ ログインボタン発見: {metbod}={selector}")
                    break
                except:
                    continue
            if not login_button:
                self.log_message.emit("❌ ログインボタンが見つかりません")
                return False

            # 人間らしいクリック
            self.driver.execute_script("arguments[0].scrollIntoView();", login_button)
            time.sleep(0.5)
            login_button.click()

            self.log_message.emit("ログインボタンクリック")

            # ログイン成功を確認
            time.sleep(5)
            current_url = self.driver.current_url

            success_indicators = [
                "my.rakuten.co.jp",
                "www.rakuten.co.jp",
                "rakuten.co.jp"
            ]

            # ページタイトルでも確認
            page_title = self.driver.title.lower()
            title_success = any(word in page_title for word in ["楽天", "rakuten", "マイページ"])

            url_success = any(indicator in current_url for indicator in success_indicators)

            if url_success or title_success:
                self.log_message.emit("🎉 楽天市場ログイン成功！")
                self.log_message.emit(f"📍 ログイン後URL: {current_url}")

                # 楽天トップぺージに移動
                try:
                    self.driver.get("https://www.rakuten.co.jp/")
                    time.sleep(3)
                except:
                    pass

                return True
            else:
                self.log_message.emit("❌ 楽天市場ログイン失敗")
                self.log_message.emit(f"現在のURL: {current_url}")

                # エラーメッセージを確認
                try:
                    error_selectors = [
                        ".error", ".alert", ".warning",
                        "[class*='error']", "[class*='alert']"
                    ]
                    for selector in error_selectors:
                        try:
                            error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if error_element.text:
                                self.log_message.emit(f"エラーメッセージ: {error_element.text}")
                                break
                        except:
                            continue
                except:
                    pass

                return False

        except Exception as e:
            self.log_message.emit(f"❌ 楽天ログインエラー: {str(e)}")
            import traceback
            self.log_message.emit(f"詳細: {traceback.format_exc()}")
            return False

    def login_to_amazon_with_cookies(self):
        """Amazonログイン処理（Bot検出対策強化版）
        0.Bot検出対策（強化版）
        1.アカウントタイプ取得
        2.タイプ別URLに移動
        3.一般ユーザーの場合「アカウント＆リスト」クリック
        4.メールアドレス入力
        5.パスワード入力
        6.ログイン確認
        7.2段階認証対応
        """
        try:
            # ============================================
            # Bot検出対策（強化版）★2025/11/03
            # ============================================
            self.log_message.emit("🛡️ Bot検出対策を実行中...")

            # Bot検出対策: JavaScriptで追加の属性を隠蔽
            self.driver.execute_script("""
                // navigator.webdriver属性を完全に削除
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // hardwareConcurrency偽装(8コアCPU、一般的なPC)
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });

                // deviceMemory を自然な値に偽装
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8 // 8GB RAM
                });

                // plugins配列を偽装、PluginArray形式に偽装に修正
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        // 実際のchromeブラウザに存在する一般的なプラグイン
                        const mockPlugins = [
                            {
                                name: 'Chrome PDF Plugin',
                                description: 'Portable Document Format',
                                filename: 'internal-pdf-viewer',
                                length: 1,
                                item: () => null,
                                namedItem: () => null
                            },
                            {
                                name: 'Chrome PDF Viewer',
                                description: '',
                                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                                length: 1,
                                item: () => null,
                                namedItem: () => null
                            },
                            {
                                name: 'Native Client',
                                description: '',
                                filename: 'internal-nacl-plugin',
                                length: 2,
                                item: () => null,
                                namedItem: () => null
                            }
                        ];

                        // PluginArrayの特性を再現する
                        mockPlugins.item = (index) => mockPlugins[index] || null;
                        mockPlugins.namedItem = (name) => {
                            return mockPlugins.find(plugin => plugin.name === name) || null;
                        };
                        mockPlugins.refresh = () => {};

                        return mockPlugins;
                    }
                });

                // ============================================
                // mimeTypes も併せて偽装（pluginsと整合性を保つ）★新規追加2025/10/31
                // ============================================
                Object.defineProperty(navigator, 'mimeTypes', {
                    get: () => {
                        const mockMimeTypes = [
                            {
                                type: 'application/pdf',
                                description: 'Portable Document Format',
                                suffixes: 'pdf',
                                enabledPlugin: {
                                    name: 'Chrome PDF Plugin',
                                    description: 'Portable Document Format',
                                    filename: 'internal-pdf-viewer'
                                }
                            },
                            {
                                type: 'application/x-google-chrome-pdf',
                                description: 'Portable Document Format',
                                suffixes: 'pdf',
                                enabledPlugin: {
                                    name: 'Chrome PDF Plugin',
                                    description: 'Portable Document Format',
                                    filename: 'internal-pdf-viewer'
                                }
                            },
                            {
                                type: 'application/x-nacl',
                                description: 'Native Client Executable',
                                suffixes: '',
                                enabledPlugin: {
                                    name: 'Native Client',
                                    description: '',
                                    filename: 'internal-nacl-plugin'
                                }
                            },
                            {
                                type: 'application/x-pnacl',
                                description: 'Portable Native Client Executable',
                                suffixes: '',
                                enabledPlugin: {
                                    name: 'Native Client',
                                    description: '',
                                    filename: 'internal-nacl-plugin'
                                }
                            }
                        ];

                        // MimeTypeArrayの特性を再現
                        mockMimeTypes.item = (index) => mockMimeTypes[index] || null;
                        mockMimeTypes.namedItem = (name) => {
                            return mockMimeTypes.find(mime => mime.type === name) || null;
                        };

                        return mockMimeTypes;
                    }
                });

                // languages設定
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ja-JP', 'ja', 'en-US', 'en']
                });

                // platformを自然な値に
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });

                // vendorを自然な値に
                Object.defineProperty(navigator, 'vendor', {
                    get: () => 'Google Inc.'
                });

                // maxTouchPointsを設定
                Object.defineProperty(navigator, 'maxTouchPoints', {
                    get: () => 0 // デスクトップPC
                });

                // WebGL Vendorを隠蔽
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    // UNMASKED_VENDOR_WEBGL
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    // UNMASKED_RENDERER_WEBGL
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.call(this, parameter);
                };

                // ============================================
                // WebGL2にも同じ対策を適用 ★新規追加2025/10/31
                // ============================================
                if (typeof WebGL2RenderingContext !== 'undefined') {
                    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return getParameter2.call(this, parameter);
                    };
                }

                // Chrome特有のオブジェクトを追加
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };

                // permissions APIを偽装
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Battery APIの隠蔽（Bot検出に使われることがある）
                if (navigator.getBattery) {
                    navigator.getBattery = () => Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1.0
                    });
                }

                // ConnectionAPIの偽装
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        effectiveType: '4g',
                        downlink: 10,
                        rtt: 50,
                        saveData: false
                    })
                });

                // 画面解像度の一貫性チェック対策
                Object.defineProperty(screen, 'availWidth', {
                    get: () => 1920
                });
                Object.defineProperty(screen, 'availHeight', {
                    get: () => 1080
                });
                Object.defineProperty(screen, 'width', {
                    get: () => 1920
                });
                Object.defineProperty(screen, 'height', {
                    get: () => 1080
                });
                Object.defineProperty(screen, 'colorDepth', {
                    get: () => 24
                });
                Object.defineProperty(screen, 'pixelDepth', {
                    get: () => 24
                });

                // Notification permission の偽装
                Object.defineProperty(Notification, 'permission', {
                    get: () => 'default'
                });

                // ============================================
                // Canvas Fingerprinting 対策 ★新規追加2025/11/03
                // ============================================
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    // わずかにノイズを追加して、毎回異なる結果を返す
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                    return originalToDataURL.apply(this, arguments);
                };

                const originalToBlob = HTMLCanvasElement.prototype.toBlob;
                HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                    return originalToBlob.apply(this, arguments);
                };

                // ============================================
                // AudioContext Fingerprinting 対策 ★新規追加2025/11/03
                // ============================================
                const audioContext = window.AudioContext || window.webkitAudioContext;
                if (audioContext) {
                    const originalCreateAnalyser = audioContext.prototype.createAnalyser;
                    audioContext.prototype.createAnalyser = function() {
                        const analyser = originalCreateAnalyser.apply(this, arguments);
                        const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                        analyser.getFloatFrequencyData = function(array) {
                            originalGetFloatFrequencyData.apply(this, arguments);
                            // わずかにノイズを追加
                            for (let i = 0; i < array.length; i++) {
                                array[i] += Math.random() * 0.0001;
                            }
                        };
                        return analyser;
                    };
                }

                // ============================================
                // WebRTC Leak 対策 ★新規追加2025/11/03
                // ============================================
                if (window.RTCPeerConnection) {
                    const originalRTCPeerConnection = window.RTCPeerConnection;
                    window.RTCPeerConnection = function(...args) {
                        if (args[0] && args[0].iceServers) {
                            args[0].iceServers = [];
                        }
                        return new originalRTCPeerConnection(...args);
                    };
                }

                // ============================================
                // Headless Detection 対策（追加） ★新規追加2025/11/03
                // ============================================
                // chrome.runtime が存在することを確認
                if (!window.chrome.runtime) {
                    window.chrome.runtime = {
                        connect: () => {},
                        sendMessage: () => {}
                    };
                }

                // User Activation API の偽装
                Object.defineProperty(navigator, 'userActivation', {
                    get: () => ({
                        hasBeenActive: true,
                        isActive: true
                    })
                });

                // Document.hidden の偽装
                Object.defineProperty(document, 'hidden', {
                    get: () => false
                });

                Object.defineProperty(document, 'visibilityState', {
                    get: () => 'visible'
                });

                // ============================================
                // Timezone の一貫性確保 ★新規追加2025/11/03
                // ============================================
                const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
                Date.prototype.getTimezoneOffset = function() {
                    return -540; // JST (UTC+9)
                };

                // ============================================
                // Permission API の完全な偽装 ★追加2025/11/03
                // ============================================
                const originalPermissionsQuery = navigator.permissions.query;
                navigator.permissions.query = function(params) {
                    if (params.name === 'notifications') {
                        return Promise.resolve({ state: 'default' });
                    }
                    return originalPermissionsQuery.apply(this, arguments);
                };

                // ============================================
                // Mouse/Touch Event の自然な発火 ★新規追加2025/11/03
                // ============================================
                let mouseEventCount = 0;
                let touchEventCount = 0;

                document.addEventListener('mousemove', () => {
                    mouseEventCount++;
                }, true);

                document.addEventListener('touchstart', () => {
                    touchEventCount++;
                }, true);

                // Bot検出でよく使われるカウンターを偽装
                Object.defineProperty(window, '_mouseEventCount', {
                    get: () => mouseEventCount + Math.floor(Math.random() * 100)
                });
            """)

            self.log_message.emit("✅ Bot検出対策完了（強化版）")

            # ============================================
            # アカウントタイプ取得
            # ============================================
            if hasattr(self, 'app_settings') and self.app_settings:
                # settings.pyからAmazonAccountTypeをインポート
                from settings import AmazonAccountType

                # 保存されているアカウント情報からタイプを取得
                amazon_type = self.app_settings.get_account_amazon_type(
                    self.account_data['account_id']
                )
                self.log_message.emit(f"📋 Amazonログイン開始 ({amazon_type.display_name})")
            else:
                # app_settingsが利用できない場合のフォールバック
                self.log_message.emit(f"📋 Amazonログイン開始 (一般ユーザー・デフォルト)")
                from settings import AmazonAccountType
                amazon_type = AmazonAccountType.CONSUMER

            # ============================================
            # Amazonトップページへアクセス
            # ============================================
            self.log_message.emit("🛒 Amazonトップページに移動中...")
            self.driver.get("https://www.amazon.co.jp")

            # ページ読み込み待機
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 人間らしい待機
            import random
            time.sleep(random.uniform(2, 4))

            self.log_message.emit(f"📍 現在のURL: {self.driver.current_url}")

            # ============================================
            # アカウント＆リストをクリック
            # ============================================
            self.log_message.emit("👤 アカウント＆リストをクリック中...")
            account_link = None
            account_selectors = [
                (By.ID, "nav-link-accountList"),
                (By.CSS_SELECTOR, '#nav-link-accountList'),
                (By.XPATH, '//*[@id="nav-link-accountList"]'),
                (By.XPATH, "//a[contains(@href, 'nav_ya_signin')]"),
                (By.CSS_SELECTOR, "a[data-nav-role='signin']")
            ]

            for method, selector in account_selectors:
                try:
                    account_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((method, selector))
                    )
                    self.log_message.emit(f"✅ アカウント＆リスト発見: {method}={selector}")
                    break
                except:
                    continue

            if not account_link:
                self.log_message.emit("⚠️ アカウント＆リストが見つかりません。直接ログインページに移動します。")
                # 直接ログインページに移動
                self.driver.get("https://www.amazon.co.jp/ap/signin")
            else:
                # 人間らしいクリック
                self.driver.execute_script("arguments[0].scrollIntoView();", account_link)
                time.sleep(random.uniform(0.5, 1))
                account_link.click()
                self.log_message.emit("✅ アカウント＆リストクリック完了")

            # ページ遷移待機
            time.sleep(random.uniform(2, 3))

            # ============================================
            # メールアドレス入力
            # ============================================
            self.log_message.emit("📧 メールアドレス入力中...")
            email_field = None
            email_selectors = [
                (By.ID, "ap_email"),
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[name='email']"),
                (By.XPATH, "//input[@type='email']")
            ]

            for method, selector in email_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((method, selector))
                    )
                    self.log_message.emit(f"✅ メールフィールド発見: {method}={selector}")
                    break
                except:
                    continue

            if not email_field:
                self.log_message.emit("❌ メールアドレスフィールドが見つかりません")
                return False

            # 人間らしいタイピング
            email_field.clear()
            for char in self.account_data['account_id']:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            self.log_message.emit("✅ メールアドレス入力完了")

            # 続けるボタンをクリック
            time.sleep(random.uniform(0.5, 1))
            continue_button = None
            continue_selectors = [
                (By.ID, "continue"),
                (By.CSS_SELECTOR, "input[id='continue']"),
                (By.XPATH, "//input[@id='continue']"),
                (By.CSS_SELECTOR, "input[type='submit']")
            ]

            for method, selector in continue_selectors:
                try:
                    continue_button = self.driver.find_element(method, selector)
                    self.log_message.emit(f"✅ 続けるボタン発見: {method}={selector}")
                    break
                except:
                    continue

            if continue_button:
                self.driver.execute_script("arguments[0].scrollIntoView();", continue_button)
                time.sleep(0.5)
                continue_button.click()
                self.log_message.emit("✅ 続けるボタンクリック")
                time.sleep(random.uniform(2, 3))

            # ============================================
            # パスワード入力
            # ============================================
            self.log_message.emit("🔐 パスワード入力中...")
            password_field = None
            password_selectors = [
                (By.ID, "ap_password"),
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@type='password']")
            ]

            for method, selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((method, selector))
                    )
                    self.log_message.emit(f"✅ パスワードフィールド発見: {method}={selector}")
                    break
                except:
                    continue

            if not password_field:
                self.log_message.emit("❌ パスワードフィールドが見つかりません")
                return False

            # 人間らしいタイピング
            password_field.clear()
            for char in self.account_data['password']:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            self.log_message.emit("✅ パスワード入力完了")

            # ログインボタンをクリック
            time.sleep(random.uniform(0.5, 1))
            login_button = None
            login_selectors = [
                (By.ID, "signInSubmit"),
                (By.CSS_SELECTOR, "input[id='signInSubmit']"),
                (By.XPATH, "//input[@id='signInSubmit']"),
                (By.CSS_SELECTOR, "input[type='submit']")
            ]

            for method, selector in login_selectors:
                try:
                    login_button = self.driver.find_element(method, selector)
                    self.log_message.emit(f"✅ ログインボタン発見: {method}={selector}")
                    break
                except:
                    continue

            if not login_button:
                self.log_message.emit("❌ ログインボタンが見つかりません")
                return False

            # 人間らしいクリック
            self.driver.execute_script("arguments[0].scrollIntoView();", login_button)
            time.sleep(0.5)
            login_button.click()
            self.log_message.emit("✅ ログインボタンクリック")

            # ============================================
            # ログイン成功確認
            # ============================================
            time.sleep(5)
            current_url = self.driver.current_url

            success_indicators = [
                "amazon.co.jp",
                "/gp/css/homepage.html",
                "nav-link-accountList-nav-line-1"
            ]

            # ページタイトルでも確認
            page_title = self.driver.title.lower()
            title_success = any(word in page_title for word in ["amazon", "アマゾン", "ホーム"])

            # URLで確認（signinページから離脱したか）
            url_success = "signin" not in current_url and "ap/signin" not in current_url

            if url_success or title_success:
                self.log_message.emit("🎉 Amazonログイン成功！")
                self.log_message.emit(f"📍 ログイン後URL: {current_url}")

                # Amazonトップページに移動
                try:
                    self.driver.get("https://www.amazon.co.jp/")
                    time.sleep(3)
                except:
                    pass

                return True
            else:
                self.log_message.emit("❌ Amazonログイン失敗")
                self.log_message.emit(f"現在のURL: {current_url}")

                # エラーメッセージを確認
                try:
                    error_selectors = [
                        "#auth-error-message-box",
                        ".a-alert-error",
                        "#auth-warning-message-box"
                    ]
                    for selector in error_selectors:
                        try:
                            error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if error_element.text:
                                self.log_message.emit(f"⚠️ エラーメッセージ: {error_element.text}")
                                break
                        except:
                            continue
                except:
                    pass

                return False

        except Exception as e:
            self.log_message.emit(f"❌ Amazonログインエラー: {str(e)}")
            import traceback
            self.log_message.emit(f"詳細: {traceback.format_exc()}")
            return False

    def login_to_yahoo_with_cookies(self):
        """Yahoo!ショッピングログイン処理"""
        # TODO: 実装
        self.log_message.emit("Yahoo!ショッピングログイン処理は未実装です")
        return False

    def wait_for_termination(self):
        """ブラウザが閉じられるまで待機"""
        try:
            self.log_message.emit("ユーザー操作を待機中...")
            while not self.should_stop:
                if self.driver and len(self.driver.window_handles) > 0:
                    time.sleep(1)
                else:
                    self.log_message.emit("ユーザーがブラウザを閉じました")
                    break
        except Exception:
            self.log_message.emit("ブラウザセッション終了")


    def cleanup(self):
        """リソースのクリーンアップ"""
        # 改善版2025/09/04
        try:
            if self.driver:
                self.driver.quit()
                self.log_message.emit("Chromeセッションクリーンアップ完了")
        except Exception as e:
            self.log_message.emit(f"クリーンアップエラー: {e}")
        finally:
            self.driver = None
            if hasattr(self, 'profile_dir') and self.profile_dir:
                try:
                    import shutil
                    shutil.rmtree(self.profile_dir, ignore_errors=True)
                except:
                    pass
    def check_chrome_installation(self):
        """Chrome環境確認（2025/08/18_エラー修正版）"""
        try:
            self.log_message.emit("🔍 Chromeインストール状況確認中...")
            # Chrome確認処理は必須ではないため、常にTrueを返す
            self.log_message.emit("✅ Chrome環境確認完了")
            return True
        except Exception as e:
            self.log_message.emit(f"⚠️ Chrome確認処理エラー: {e}")
            return True


    def sync_cookies_to_webengine(self, site):
        """SeleniumのCookieをWebEngineに同期

        Args:
            site (str): サイト名（楽天市場、Amazon、Yahoo!ショッピング等）
        """
        try:
            if not self.driver:
                self.log_message.emit(f"注意 {site} - WebDriverが存在しません")
                return False

            self.log_message.emit(f"🔄️ {site} - Cookie同期開始...")

            # 現在のURLを取得して送信
            current_url = self.driver.current_url
            self.url_update.emit(current_url)
            self.log_message.emit(f"現在のURL: {current_url}")

            # Seleniumから現在のページのcookieを取得
            selenium_cookies = self.driver.get_cookies()

            if not selenium_cookies:
                self.log_message.emit(f"注意 {site} - Cookieが見つかりません")
                return False

            # Cookie形式を変換
            cookies_list = []
            for cookie in selenium_cookies:
                # 必須フィールドのチェック
                if not cookie.get('name') or not cookie.get('value'):
                    continue

                cookie_dict = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                    'sameSite': cookie.get('sameSite', 'None')
                }

                # expiryフィールドの処理（Unix timestampをQDateTime用に変換）
                if 'expiry' in cookie:
                    cookie_dict['expires'] = int(cookie['expiry'])
                else:
                    cookie_dict['expires'] = 0

                cookies_list.append(cookie_dict)

            # デバック情報
            self.log_message.emit(f"📊 {site} - {len(cookies_list)}個のCookieを取得")

            # 主要なCookieの名前をログに出力（デバック用）
            cookie_names = [c['name'] for c in cookies_list[:5]] # 最初の5個
            self.log_message.emit(f"主要Cookie: {', '.join(cookie_names)}...")

            # WebEngineViewにCookieを送信
            self.cookies_ready.emit(cookies_list, site)

            # ページソースも送信（オプション）
            try:
                page_source = self.driver.page_source
                if page_source:
                    self.browser_page_source.emit(page_source)
                    self.log_message.emit(f"ページソース送信完了")
            except Exception as e:
                self.log_message.emit(f"ページソース取得エラー: {e}")

            self.log_message.emit(f"✅ {site} - Cookie同期完了")
            return True

        except Exception as e:
            error_msg = f"Cookie同期エラー ({site}): {str(e)}"
            self.log_message.emit(f"✖ {error_msg}")
            self.error_occurred.emit(error_msg)

            # 詳細なエラー情報
            import traceback
            self.log_message.emit(f"詳細: {traceback.format_exc()}")
            return False

    def get_chrome_driver_path(self):
        """ChromeDriverのパスを取得

        Returns:
            str: ChromrDriverのパス（見つからない場合はNone）
        """
        try:
            # 自動作動に決めた
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            self.log_message.emit(f"✅ ChromrDriver自動取得成功: {driver_path}")
            return driver_path
        except ImportError:
            self.log_message.emit("⚠️ webdriver-managerがインストールされてません")
        except Exception as e:
            self.log_message.emit(f"⚠️ ChromrDriver自動取得失敗: {e}")

# UI関連のコードをui.pyに分離する
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        print("MainWindow初期化開始")

        self.app_settings = AppSettings()  # これがAppSettingsインスタンスであることを確認
        self.settings_data = self.app_settings.load_settings()
        self.user_prefs = UserPreferencesManager(self.app_settings.settings)  # これは別の変数
        self.selenium_thread = None

        # app_ui.pyのMainUIを使用してUI初期化を追加
        self.ui = MainUI(self)

        # UIコンポーネントへの参照を追加
        self._setup_ui_references()

        # UIコンポーネントへの接続を設定
        self.setup_connections()

        # 設定から初期化を復元
        self.load_saved_settings()
        self.load_user_preferences()
        print("MainWindow初期化完了")

    def _setup_ui_references(self):
        """UIコンポーネントへの参照を設定"""
        self.main_tab = self.ui.main_tab
        self.accounts_tab = self.ui.accounts_tab
        self.log_tab = self.ui.log_tab
        self.tab_widget = self.ui.tab_widget
        self.account_combo = self.ui.main_tab.account_combo
        self.list_widget = self.ui.main_tab.list_widget
        self.start_button = self.ui.main_tab.start_button
        self.status_label = self.ui.main_tab.status_label
        self.progress_bar = self.ui.main_tab.progress_bar
        self.accounts_list = self.ui.accounts_tab.accounts_list

        # 停止ボタンがある場合
        if hasattr(self.ui.main_tab, 'stop_button'):
            self.stop_button = self.ui.main_tab.stop_button

    def setup_connections(self):
        """UIコンポーネントのシグナル接続を設定（純粋な接続のみ）"""
        # メインタブのボタン接続
        self.start_button.clicked.connect(self.start_selenium)

        # 停止ボタン（存在する場合）
        if hasattr(self, 'stop_button'):
            self.stop_button.clicked.connect(self.stop_selenium)

        # アカウント管理タブの接続（存在確認付き）
        if hasattr(self.ui.accounts_tab, 'add_button'):
            self.ui.accounts_tab.add_button.clicked.connect(self.add_account)
        if hasattr(self.ui.accounts_tab, 'delete_button'):
            self.ui.accounts_tab.delete_button.clicked.connect(self.delete_account)
        if hasattr(self.ui.accounts_tab, 'edit_button'):
            self.ui.accounts_tab.edit_button.clicked.connect(self.edit_account) # まだ参照なし

    def stop_selenium(self):
        """Selenium処理を停止"""
        if not self.selenium_thread:
            self.log_tab.add_log("停止するSeleniumプロセスがありません")
            return

        if self.selenium_thread.isRunning():
            self.log_tab.add_log("Selenium停止処理を開始...")
            self.selenium_thread.stop()

            # UI状態の更新
            self.status_label.setText("停止処理中...")
            self.status_button.setEnabled(False)

            # 停止ボタンを無効化
            if hasattr(self, 'stop_button'):
                self.stop_button.setEnabled(False)
            # プログレバーを不確定状態に
            self.progress_bar.setRange(0, 0) # 不確定プログレバー
        else:
            self.log_tab.add_log("Seleniumは既に停止しています")


    def start_selenium(self):
        """Selenium処理を開始"""
        account_data = self.get_selected_account_data()
        selected_sites = self.get_selected_sites()
        if not account_data:
            QMessageBox.warning(self, "警告", "アカウントを選択してください")
            return
        if not selected_sites:
            QMessageBox.warning(self, "警告", "ECサイトを選択してください")
            return

        # SeleniumThreadを開始
        self.selenium_thread = SeleniumThread(
            self.web_engine_view,
            account_data,
            selected_sites,
            self.app_settings  # ★追加
        )

        # シグナル接続
        self.selenium_thread.finished.connect(self.on_selenium_finished)
        self.selenium_thread.status_update.connect(self.update_status)
        self.selenium_thread.error_occurred.connect(self.on_error)
        self.selenium_thread.log_message.connect(self.log_tab.add_log)
        self.selenium_thread.start()

    def get_selected_account_data(self):
        """選択されたアカウントのデータを取得"""
        current_text = self.account_combo.currentText()
        if not current_text or current_text == "アカウントを選択":
            return None
        accounts = self.app_settings.get_accounts()
        for account_id, account_data in accounts.items():
            if account_id in current_text:
                return {
                    'account_id': account_id,
                    'password': account_data['password'],
                    'nickname': account_data.get('nickname', '')
                }
        return None

    def get_selected_sites(self):
        """選択されたサイトのリストを取得"""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if checkbox and checkbox.isChecked():
                selected.append(item.text())
        return selected

    def update_status(self, message):
        """ステータス更新"""
        self.status_label.setText(message)


    def add_log(self, message):
        """ログ追加(LogStatusTabのメソッドを呼び出す)"""
        if hasattr(self, 'log_tab'):
            self.log_tab.add_log(message)

    def on_error(self, error_message):
        """エラー処理"""
        QMessageBox.critical(self, "エラー", error_message)

    def on_selenium_finished(self):
        """Selenium処理完了"""
        self.add_log("Selenium処理が完了しました。")
        self.progress_bar.setValue(100)

    def refresh_account_combo(self):
        """アカウントコンボボックスを更新"""
        self.account_combo.clear()
        self.account_combo.addItem("アカウントを選択")

        accounts = self.app_settings.get_accounts()
        for account_id, account_data in accounts.items():
            nickname = account_data.get("nickname", "")
            display_name = f"{nickname} ({account_id})" if nickname else account_id
            self.account_combo.addItem(display_name)

    def refresh_accounts_list(self):
        """アカウントリストを更新"""
        self.accounts_list.clear()
        accounts = self.app_settings.get_accounts()

        for account_id, account_data in accounts.items():
            nickname = account_data.get("nickname", "")
            display_text = f"{nickname} ({account_id})" if nickname else account_id
            self.accounts_list.addItem(display_text)

    def add_account(self):
        """アカウント追加"""
        dialog = AccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            account_id = dialog.account_id_input.text()
            password = dialog.password_input.text()
            nickname = dialog.nickname_input.text()

            self.app_settings.save_account(account_id, password, nickname)
            self.refresh_account_combo()
            self.refresh_accounts_list()

    def delete_account(self):
        """アカウント削除"""
        current_item = self.accounts_list.currentItem()
        if not current_item:
            return
        # アカウントIDを抽出
        text = current_item.text()
        account_id = text.split('(')[-1].rstrip(')')

        reply = QMessageBox.question(
            self, "確認",
            f"アカウント '{account_id}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.app_settings.delete_account(account_id)
            self.refresh_account_combo()
            self.refresh_accounts_list()

    def load_saved_settings(self):
        """保存された設定を読み込み"""
        pass
    def load_user_preferences(self):
        """ユーザー設定を読み込み"""
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # settings.pyのモダンを追加
    from settings import apply_modern_theme
    apply_modern_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def get_chrome_version():
    """インストールされているChromeのバージョンを取得する"""
    try:
        system = platform.system()
        print(f"検出されたOS: {system}")  # デバッグ出力を追加

        if system == "Windows":
            # Windowsの場合
            try:
                # レジストリからバージョンを取得
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                version = winreg.QueryValueEx(key, "version")[0]
                return version
            except Exception as e:
                print(f"レジストリからのChromeバージョン取得エラー: {e}")
                # プロセスからバージョンを取得（代替方法）
                try:
                    # 一般的なインストールパス
                    paths = [
                        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                        os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\Application\chrome.exe'
                    ]
                    for path in paths:
                        if os.path.exists(path):
                            print(f"Chromeパスが見つかりました: {path}")
                            path_escaped = path.replace('\\', '\\\\')
                            info = subprocess.check_output(r'wmic datafile where name="' + path_escaped + r'" get Version /value', shell=True)
                            match = re.search(r'Version=(.+)', info.decode('utf-8'))
                            if match:
                                return match.group(1)
                            else:
                                print("バージョン情報が見つかりませんでした")
                                return None
                except Exception as e2:
                    print(f"プロセスからのChromeバージョン取得エラー: {e2}")
                    # バージョン取得に失敗した場合、最新バージョンを使用
                    print("Chromeバージョンの取得に失敗しました。最新のChromeDriverを使用します。")
                    return None
        elif system == "Darwin":
            # macOSの場合
            try:
                process = subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'], stdout=subprocess.PIPE)
                version = process.communicate()[0].decode('UTF-8').replace('Google Chrome ', '').strip()
                return version
            except:
                return None
        else:
            print(f"未サポートのプラットフォーム: {system}")
            return None
    except Exception as e:
        print(f"Chromeバージョン取得エラー: {e}")
        return None

def download_chromedriver(destination=None): # JSONデータから抽出したURLを使用するように変更
    """Chrome 134用の新しいURL形式からChromeDriverをダウンロード"""
    try:
        if destination is None:
            # 実行ファイルと同じディレクトリに配置
            if getattr(sys, 'frozen', False):
                # PyInstallerでパッケージ化された場合
                destination = os.path.dirname(sys.executable)
            else:
                # 通常のPython実行の場合
                destination = os.path.dirname(os.path.abspath(__file__))

        # Chromeの完全なバージョンを取得
        chrome_version = get_chrome_version()
        if not chrome_version:
            print("Chromeバージョンの検出に失敗しました。")
            return None

        print(f"検出されたChromeバージョン: {chrome_version}")
        major_version = chrome_version.split('.')[0]

        # chrome 115以降は新しいURLフォーマットを使用
        if int(major_version) >= 115:
            # まず対応するバージョンを試す
            driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/win64/chromedriver-win64.zip"
            print(f"Chrome {major_version}用の新形式URL: {driver_url}")
        else:
            # 古いバージョンの場合は従来のURLフォーマット
            driver_url = f"https://chromedriver.storage.googleapis.com/{chrome_version}/chromedriver_win64.zip"
            print(f"Chrome {major_version}用の従来形式URL: {driver_url}")

        # 利用可能なバージョンのリスト
        fallback_versions = [
            "134.0.6998.165",  # 最新の互換性のある134バージョン
            "134.0.6998.90",
            "134.0.6998.88",
            "134.0.6998.35"
        ]

        # ダウンロード試行
        print(f"ダウンロードURL: {driver_url}")
        try:
            response = requests.get(driver_url)
            if response.status_code != 200:
                print(f"ChromeDriverのダウンロードに失敗しました。ステータスコード: {response.status_code}")

                # 最新の互換性のあるバージョンにフォールバック
                for version in fallback_versions:
                    fallback_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"
                    print(f"代替URLを試行: {fallback_url}")
                    fallback_response = requests.get(fallback_url)
                    if fallback_response.status_code == 200:
                        response = fallback_response
                        print(f"代替URLからのダウンロードに成功しました: {fallback_url}")
                        break

                # すべての代替URLが失敗した場合
                if response.status_code != 200:
                    print("すべてのURLでのダウンロードに失敗しました。webdriver_managerを使用します。")
                    try:
                        # webdriver_managerを使用
                        from webdriver_manager.chrome import ChromeDriverManager
                        driver_path = ChromeDriverManager().install()
                        print(f"webdriver_managerでのダウンロードに成功しました: {driver_path}")
                        return driver_path
                    except Exception as e:
                        print(f"webdriver_managerでのダウンロードにも失敗しました: {e}")
                        return None
        except Exception as req_error:
            print(f"リクエスト中にエラーが発生しました: {req_error}")
            # webdriver_managerを使用してフォールバック
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                print(f"webdriver_managerでのダウンロードに成功しました: {driver_path}")
                return driver_path
            except Exception as wdm_error:
                print(f"webdriver_managerでのダウンロードにも失敗しました: {wdm_error}")
                return None

        # ZIPファイルを展開
        try:
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                driver_name = "chromedriver.exe" # Windows
                # ZIPファイルの内容を表示
                file_list = zip_file.namelist()
                print(f"ZIPファイル内の内容: {file_list}") # デバッグ用

                # chromedriver.exeを含むファイルパスを探す
                driver_in_zip = None
                for file in file_list:
                    if file.endswith(driver_name):
                        driver_in_zip = file
                        break

                if not driver_in_zip:
                    print(f"ZIPファイル内にChromeDriverが見つかりませんでした。ファイル一覧: {file_list}")
                    return None

                # 既存のChromeDriverを削除
                driver_path = os.path.join(destination, driver_name)
                if os.path.exists(driver_path):
                    try:
                        os.remove(driver_path)
                        print(f"既存のChromeDriverを削除しました: {driver_path}")
                    except Exception as e:
                        print(f"既存のChromeDriverの削除に失敗しました: {e}")

                # 新しいChromeDriverを展開
                with open(driver_path, 'wb') as f:
                    f.write(zip_file.read(driver_in_zip))

                print(f"ChromeDriverを正常にダウンロードしました: {driver_path}")
                return driver_path
        except Exception as zip_error:
            print(f"ZIPファイル処理エラー: {zip_error}")
            return None

    except Exception as e:
        print(f"ChromeDriverダウンロード総合エラー: {e}")
        # エラーの場合、既存のChromeDriverのパスを返す（存在する場合）
        if destination:
            driver_name = "chromedriver.exe"
            driver_path = os.path.join(destination, driver_name)
            if os.path.exists(driver_path):
                print(f"既存のChromeDriverを使用します: {driver_path}")
                return driver_path
        return None
