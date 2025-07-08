# -*- coding: utf-8 -*-

import sys
import os
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

from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
                            QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QLabel,
                            QMessageBox, QProgressBar, QComboBox, QInputDialog, QFrame,
                            QTextEdit, QSplitter, QGroupBox, QGridLayout, QStackedWidget,
                            QTabWidget, QSpinBox, QDateEdit, QTimeEdit, QFileDialog)

from PyQt6.QtCore import (QUrl, QThread, pyqtSignal, QLibraryInfo, Qt, QTimer,
                        QSettings, QDateTime, QDate, QTime)

# QtWebEngineCore は WebView 初期化時に必要
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

# QtNetwork（ネットワーク） は Cookie 設定に必要
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtGui import QDesktopServices, QFont  # QtGuiからインポート

# webdriver_manager はフォールバック用に残す
from webdriver_manager.chrome import ChromeDriverManager

# Selenium 関連のインポート
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service

# ローカルモジュール
from settings import AppSettings, SettingsDialog, AccountDialog, UserPreferencesManager


class SeleniumThread(QThread):
    """プロフェッショナル自動ログインシステム - 5サイト対応"""
    finished = pyqtSignal()
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    account_success = pyqtSignal(str, str)  # アカウント、サイト成功通知

    def __init__(self, web_engine_view, account_data, selected_sites):
        super().__init__()
        self.web_engine_view = web_engine_view
        self.account_data = account_data  # {'account_id': str, 'password': str, 'nickname': str}
        self.selected_sites = selected_sites
        self.driver = None
        self.should_stop = False

    def run(self):
        try:
            self.log_message.emit("🚀 === BOX0.1 自動ログインシステム開始 ===")
            
            # アカウント情報表示
            account_display = self.account_data.get('nickname', self.account_data['account_id'])
            self.log_message.emit(f"👤 使用アカウント: {account_display}")
            self.log_message.emit(f"🏪 対象サイト: {', '.join(self.selected_sites)}")
            
            # システム環境チェック
            self.status_update.emit("🔍 システム環境をチェック中...")
            self.log_message.emit("📋 Step1: Chrome環境確認とCookie準備")
            self.progress_update.emit(10)
            
            if not self.check_chrome_installation():
                self.error_occurred.emit("Chromeブラウザがインストールされていません")
                return
            
            # WebDriver + Cookie設定
            self.status_update.emit("🚀 Chrome WebDriver起動中...")
            self.log_message.emit("📋 Step2: Selenium WebDriver + Cookie統合準備")
            self.progress_update.emit(30)
            
            chrome_options = Options()
            chrome_options.add_argument("--remote-debugging-port=9223")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--start-maximized")
            # Cookie保持のための設定
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # ブラウザの自動化検出を回避
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                self.log_message.emit("✅ Chrome WebDriver + Cookie準備完了")
                self.progress_update.emit(50)
            except Exception as e:
                self.error_occurred.emit(f"WebDriver起動失敗: {str(e)}")
                return

            # 各サイトへのログイン処理（5サイト対応）
            for i, site in enumerate(self.selected_sites):
                if self.should_stop:
                    break
                    
                progress = 50 + (40 * (i + 1) / len(self.selected_sites))
                self.progress_update.emit(int(progress))
                
                self.log_message.emit(f"📋 Step3-{i+1}: {site} ログイン処理開始")
                
                success = False
                if site == "楽天市場":
                    success = self.login_to_rakuten_with_cookies(
                        self.driver, 
                        self.account_data['account_id'], 
                        self.account_data['password']
                    )
                elif site == "Amazon":
                    success = self.login_to_amazon_with_cookies(
                        self.driver, 
                        self.account_data['account_id'], 
                        self.account_data['password']
                    )
                elif site == "Yahoo!ショッピング":
                    success = self.login_to_yahoo_with_cookies(
                        self.driver, 
                        self.account_data['account_id'], 
                        self.account_data['password']
                    )
                elif site == "auワウマ":
                    success = self.login_to_wowma_with_cookies(
                        self.driver, 
                        self.account_data['account_id'], 
                        self.account_data['password']
                    )
                elif site == "メルカリ":
                    success = self.login_to_mercari_with_cookies(
                        self.driver, 
                        self.account_data['account_id'], 
                        self.account_data['password']
                    )
                    
                if success:
                    self.status_update.emit(f"✅ {site} ログイン成功！")
                    self.log_message.emit(f"🎉 {site} - ログイン完了、TOPページ表示準備完了")
                    self.account_success.emit(account_display, site)
                    # Cookie情報をWebEngineViewに同期
                    self.sync_cookies_to_webengine(site)
                else:
                    self.status_update.emit(f"❌ {site} ログイン失敗")
                    self.log_message.emit(f"⚠️ {site} - ログイン失敗、再試行が必要")

            self.progress_update.emit(90)
            # 最終段階
            self.status_update.emit("⏳ ログイン完了 - ブラウザ待機中...")
            self.log_message.emit("📋 Step4: 全ログイン処理完了、ユーザー操作待機")
            
            self.wait_for_termination()
            
        except Exception as e:
            self.error_occurred.emit(f"予期しないエラー: {str(e)}\n{traceback.format_exc()}")
            self.log_message.emit(f"❌ 致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def check_chrome_installation(self):
        """Chrome環境確認"""
        try:
            self.log_message.emit("🔍 Chromeインストール状況確認中...")
            if platform.system() == "Windows":
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                    chrome_path = winreg.QueryValue(key, "")
                    winreg.CloseKey(key)
                    
                    if os.path.exists(chrome_path):
                        self.log_message.emit(f"✅ Chrome検出: {chrome_path}")
                        return True
                    else:
                        self.log_message.emit("❌ Chromeパスが無効")
                        return False
                except FileNotFoundError:
                    self.log_message.emit("❌ Chromeがレジストリに見つかりません")
                    return False
            return True
        except Exception as e:
            self.log_message.emit(f"⚠️ Chrome確認エラー: {e}")
            return True

    def login_to_rakuten_with_cookies(self, driver, account_id, password):
        """楽天市場ログイン + Cookie統合"""
        try:
            self.log_message.emit("🏪 楽天市場ログインページに移動中...")
            
            # 楽天ログインページに移動
            driver.get("https://grp01.id.rakuten.co.jp/rms/nid/loginfwd")
            time.sleep(3)
            
            self.log_message.emit("📝 アカウントID入力中...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "user_id"))
            )
            username_field.clear()
            username_field.send_keys(account_id)
            time.sleep(2)

            self.log_message.emit("➡️ 次のステップに進行中...")
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            next_button.click()
            time.sleep(3)

            self.log_message.emit("🔐 パスワード入力中...")
            password_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "password_current"))
            )
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(2)

            self.log_message.emit("🚀 ログイン実行中...")
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            login_button.click()

            # ログイン完了確認
            WebDriverWait(driver, 20).until(
                lambda d: "rakuten.co.jp" in d.current_url and "login" not in d.current_url.lower()
            )
            
            # Cookie情報を取得・保存
            cookies = driver.get_cookies()
            self.log_message.emit(f"🍪 Cookie取得完了: {len(cookies)}個のCookie")
            
            # TOP PAGEに移動して確認
            driver.get("https://www.rakuten.co.jp")
            time.sleep(2)
            
            self.log_message.emit("🎉 楽天市場ログイン完了！Cookie同期準備完了")
            return True
        
        except (TimeoutException, NoSuchElementException) as e:
            self.log_message.emit(f"⚠️ 楽天ログインタイムアウト: {e}")
            return False
        except Exception as e:
            self.log_message.emit(f"❌ 楽天ログイン予期しないエラー: {e}")
            return False

    def login_to_amazon_with_cookies(self, driver, account_id, password):
        """Amazon ログイン + Cookie統合"""
        try:
            self.log_message.emit("🛒 Amazonログインページに移動中...")
            
            driver.get("https://www.amazon.co.jp/ap/signin")
            time.sleep(3)

            self.log_message.emit("📧 メールアドレス入力中...")
            email_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "ap_email"))
            )
            email_field.clear()
            email_field.send_keys(account_id)
            time.sleep(1)
            
            continue_button = driver.find_element(By.ID, "continue")
            continue_button.click()
            time.sleep(3)

            self.log_message.emit("🔐 パスワード入力中...")
            password_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "ap_password"))
            )
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button = driver.find_element(By.ID, "signInSubmit")
            login_button.click()

            # ログイン成功確認
            WebDriverWait(driver, 15).until(
                lambda d: "amazon.co.jp" in d.current_url and "signin" not in d.current_url
            )
            
            cookies = driver.get_cookies()
            self.log_message.emit(f"🍪 Amazon Cookie取得完了: {len(cookies)}個のCookie")
            
            self.log_message.emit("🎉 Amazonログイン完了！Cookie同期準備完了")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ Amazonログインエラー: {e}")
            return False

    def login_to_yahoo_with_cookies(self, driver, account_id, password):
        """Yahoo!ショッピング ログイン + Cookie統合"""
        try:
            self.log_message.emit("🛍️ Yahoo!ショッピングログインページに移動中...")
            
            driver.get("https://login.yahoo.co.jp/config/login")
            time.sleep(3)

            self.log_message.emit("📧 Yahoo! ID入力中...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.clear()
            username_field.send_keys(account_id)
            time.sleep(1)
            
            next_button = driver.find_element(By.ID, "btnNext")
            next_button.click()
            time.sleep(3)

            self.log_message.emit("🔐 パスワード入力中...")
            password_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "passwd"))
            )
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button = driver.find_element(By.ID, "btnSubmit")
            login_button.click()

            # Yahoo!ショッピングに移動
            driver.get("https://shopping.yahoo.co.jp/")
            time.sleep(2)
            
            cookies = driver.get_cookies()
            self.log_message.emit(f"🍪 Yahoo! Cookie取得完了: {len(cookies)}個のCookie")
            
            self.log_message.emit("🎉 Yahoo!ショッピングログイン完了！Cookie同期準備完了")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ Yahoo!ログインエラー: {e}")
            return False

    def login_to_wowma_with_cookies(self, driver, account_id, password):
        """auワウマ ログイン + Cookie統合"""
        try:
            self.log_message.emit("📱 auワウマログインページに移動中...")
            
            driver.get("https://wowma.jp/login")
            time.sleep(3)

            self.log_message.emit("📧 メールアドレス入力中...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, "loginId"))
            )
            username_field.clear()
            username_field.send_keys(account_id)
            time.sleep(1)

            self.log_message.emit("🔐 パスワード入力中...")
            password_field = driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            login_button.click()

            # ログイン完了確認
            WebDriverWait(driver, 15).until(
                lambda d: "wowma.jp" in d.current_url and "login" not in d.current_url
            )
            
            cookies = driver.get_cookies()
            self.log_message.emit(f"🍪 auワウマ Cookie取得完了: {len(cookies)}個のCookie")
            
            self.log_message.emit("🎉 auワウマログイン完了！Cookie同期準備完了")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ auワウマログインエラー: {e}")
            return False

    def login_to_mercari_with_cookies(self, driver, account_id, password):
        """メルカリ ログイン + Cookie統合"""
        try:
            self.log_message.emit("📦 メルカリログインページに移動中...")
            
            driver.get("https://jp.mercari.com/login")
            time.sleep(3)

            self.log_message.emit("📧 メールアドレス入力中...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, "emailOrPhone"))
            )
            username_field.clear()
            username_field.send_keys(account_id)
            time.sleep(1)

            self.log_message.emit("🔐 パスワード入力中...")
            password_field = driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            # ログイン完了確認
            WebDriverWait(driver, 15).until(
                lambda d: "mercari.com" in d.current_url and "login" not in d.current_url
            )
            
            cookies = driver.get_cookies()
            self.log_message.emit(f"🍪 メルカリ Cookie取得完了: {len(cookies)}個のCookie")
            
            self.log_message.emit("🎉 メルカリログイン完了！Cookie同期準備完了")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ メルカリログインエラー: {e}")
            return False

    def sync_cookies_to_webengine(self, site):
        """Selenium CookieをWebEngineViewに同期"""
        try:
            self.log_message.emit(f"🔄 {site} Cookie同期中...")
            
            cookies = self.driver.get_cookies()
            profile = self.web_engine_view.page().profile()
            
            for cookie in cookies:
                qcookie = QNetworkCookie(
                    cookie['name'].encode(), 
                    cookie['value'].encode()
                )
                if 'domain' in cookie:
                    qcookie.setDomain(cookie['domain'])
                if 'path' in cookie:
                    qcookie.setPath(cookie['path'])
                    
                profile.cookieStore().setCookie(qcookie)
            
            self.log_message.emit(f"✅ {site} Cookie同期完了")
            
        except Exception as e:
            self.log_message.emit(f"⚠️ Cookie同期エラー: {e}")

    def wait_for_termination(self):
        """ブラウザ待機処理"""
        self.log_message.emit("⏳ ログイン完了 - ユーザー操作待機中...")
        try:
            while not self.should_stop:
                if len(self.driver.window_handles) == 0:
                    self.log_message.emit("👋 ユーザーがブラウザを閉じました")
                    break
                time.sleep(1)
        except Exception:
            self.log_message.emit("🔚 ブラウザセッション終了")

    def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if self.driver:
                self.driver.quit()
                self.log_message.emit("🧹 Chromeセッションクリーンアップ完了")
        except Exception:
            pass
        finally:
            self.progress_update.emit(100)
            self.log_message.emit("🏁 === BOX0.1 自動ログインシステム終了 ===")
            self.finished.emit()

    def stop(self):
        """スレッドの停止"""
        self.should_stop = True
        self.log_message.emit("⏹️ ユーザーによる停止要求")


class MainWindow(QWidget):
    """BOX0.1 PyQt6 Helper - プロフェッショナル版"""
    
    def __init__(self):
        super().__init__()
        print("🚀 BOX0.1 PyQt6 Helper - プロフェッショナル版 初期化開始")
        
        # 設定管理システムの初期化
        self.app_settings = AppSettings()
        self.settings_data = self.app_settings.load_settings()
        
        # ユーザー情報記憶機能の初期化
        self.user_prefs = UserPreferencesManager(self.app_settings.settings)
        
        self.selenium_thread = None
        self.auto_scroll_enabled = True
        self.init_ui()
        
        # 設定から初期値を復元
        self.load_saved_settings()
        # ユーザー設定を復元
        self.load_user_preferences()
        
        print("✅ BOX0.1 PyQt6 Helper プロフェッショナル版 初期化完了")

    def init_ui(self):
        """プロフェッショナルUI初期化"""
        # ウィンドウ設定
        self.setWindowTitle("🎯 BOX0.1 PyQt6 Helper - プロフェッショナル版")
        self.setGeometry(100, 100, 950, 800)
        
        # メインレイアウト
        main_layout = QVBoxLayout()
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # Tab1: メイン実行画面
        main_tab = self.create_main_execution_tab()
        self.tab_widget.addTab(main_tab, "🚀 実行")
        
        # Tab2: アカウント管理画面
        accounts_tab = self.create_accounts_management_tab()
        self.tab_widget.addTab(accounts_tab, "👤 アカウント管理")
        
        # Tab3: ユーザー設定画面
        user_settings_tab = self.create_user_settings_tab()
        self.tab_widget.addTab(user_settings_tab, "⚙️ ユーザー設定")
        
        # Tab4: ログ・ステータス
        log_tab = self.create_log_status_tab()
        self.tab_widget.addTab(log_tab, "📋 ログ・ステータス")
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        
        # WebEngineView（内部的に使用）
        self.web_engine_view = QWebEngineView()

    def create_main_execution_tab(self):
        """Tab1: メイン実行画面"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # タイトル
        title = QLabel("🎯 BOX0.1 自動ログインシステム")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #2c3e50; 
            margin: 15px;
            text-align: center;
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 8px;
        """)
        layout.addWidget(title)
        
        # アカウント選択
        account_group = QGroupBox("👤 アカウント選択")
        account_layout = QVBoxLayout()
        
        # アカウント選択コンボボックス
        combo_layout = QHBoxLayout()
        self.account_combo = QComboBox()
        self.account_combo.setStyleSheet("padding: 10px; font-size: 13px;")
        self.refresh_account_combo()
        
        # アカウント管理画面切り替えボタン
        switch_accounts_button = QPushButton("👤 アカウント管理")
        switch_accounts_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        switch_accounts_button.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        
        combo_layout.addWidget(self.account_combo, 3)
        combo_layout.addWidget(switch_accounts_button, 1)
        account_layout.addLayout(combo_layout)
        
        # アカウント情報表示
        self.account_info_label = QLabel("アカウントを選択してください")
        self.account_info_label.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 10px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            font-size: 12px;
        """)
        account_layout.addWidget(self.account_info_label)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # ECサイト選択 - 5サイト対応
        sites_group = QGroupBox("🏪 ECサイト選択")
        sites_layout = QVBoxLayout()
        
        self.ec_sites = ["楽天市場", "Amazon", "Yahoo!ショッピング", "auワウマ", "メルカリ"]
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(150)
        
        for site in self.ec_sites:
            item = QListWidgetItem(site)
            checkbox = QCheckBox(site)
            checkbox.setStyleSheet("margin: 8px; font-size: 12px;")
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, checkbox)
        
        sites_layout.addWidget(self.list_widget)
        sites_group.setLayout(sites_layout)
        layout.addWidget(sites_group)
        
        # 実行ボタン
        execution_group = QGroupBox("🚀 実行コントロール")
        execution_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 自動ログイン開始")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.start_button.clicked.connect(self.start_selenium)
        
        self.stop_button = QPushButton("⏹️ 停止")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_button.clicked.connect(self.stop_selenium)
        self.stop_button.setEnabled(False)
        
        execution_layout.addWidget(self.start_button)
        execution_layout.addWidget(self.stop_button)
        execution_group.setLayout(execution_layout)
        layout.addWidget(execution_group)
        
        # 簡易ステータス
        self.main_status = QLabel("📊 待機中 - アカウントを選択してください")
        self.main_status.setStyleSheet("""
            background-color: #3498db; 
            color: white;
            padding: 10px; 
            border-radius: 5px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
        """)
        layout.addWidget(self.main_status)
        
        tab.setLayout(layout)
        return tab

    def create_accounts_management_tab(self):
        """Tab2: アカウント管理画面（削除機能強化）"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # タイトル
        title = QLabel("👤 アカウント管理システム")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #2c3e50; 
            margin: 15px;
            text-align: center;
            background-color: #e8f5e8;
            padding: 10px;
            border-radius: 8px;
        """)
        layout.addWidget(title)
        
        # 戻るボタン
        back_layout = QHBoxLayout()
        back_to_main_button = QPushButton("🔙 実行画面に戻る")
        back_to_main_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        back_to_main_button.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))
        
        back_layout.addWidget(back_to_main_button)
        back_layout.addStretch()
        layout.addLayout(back_layout)
        
        # アカウントリスト
        accounts_group = QGroupBox("📋 登録済みアカウント一覧")
        accounts_layout = QVBoxLayout()
        
        self.accounts_list_widget = QListWidget()
        self.accounts_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #ffffff;
                padding: 5px;
            }
        """)
        accounts_layout.addWidget(self.accounts_list_widget)
        
        # アカウント操作ボタン（削除機能強化）
        buttons_layout = QHBoxLayout()
        
        add_account_button = QPushButton("➕ 新規追加")
        add_account_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        add_account_button.clicked.connect(self.add_new_account)
        
        edit_account_button = QPushButton("✏️ 編集")
        edit_account_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        edit_account_button.clicked.connect(self.edit_selected_account)
        
        delete_account_button = QPushButton("🗑️ 削除")
        delete_account_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_account_button.clicked.connect(self.delete_selected_account)
        
        # 全削除ボタン（強化機能）
        delete_all_button = QPushButton("🗑️ 全削除")
        delete_all_button.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7d3c98;
            }
        """)
        delete_all_button.clicked.connect(self.delete_all_accounts)
        
        buttons_layout.addWidget(add_account_button)
        buttons_layout.addWidget(edit_account_button)
        buttons_layout.addWidget(delete_account_button)
        buttons_layout.addWidget(delete_all_button)
        buttons_layout.addStretch()
        
        accounts_layout.addLayout(buttons_layout)
        accounts_group.setLayout(accounts_layout)
        layout.addWidget(accounts_group)
        
        # クイック追加フォーム
        quick_add_group = QGroupBox("⚡ クイック追加")
        quick_layout = QGridLayout()
        
        quick_layout.addWidget(QLabel("アカウントID:"), 0, 0)
        self.quick_account_id = QLineEdit()
        self.quick_account_id.setPlaceholderText("ID/メールアドレス")
        quick_layout.addWidget(self.quick_account_id, 0, 1)
        
        quick_layout.addWidget(QLabel("パスワード:"), 1, 0)
        self.quick_password = QLineEdit()
        self.quick_password.setPlaceholderText("パスワード")
        self.quick_password.setEchoMode(QLineEdit.EchoMode.Password)
        quick_layout.addWidget(self.quick_password, 1, 1)
        
        quick_layout.addWidget(QLabel("ニックネーム:"), 2, 0)
        self.quick_nickname = QLineEdit()
        self.quick_nickname.setPlaceholderText("覚えやすい名前（任意）")
        quick_layout.addWidget(self.quick_nickname, 2, 1)
        
        quick_add_button = QPushButton("🚀 即座に追加")
        quick_add_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        quick_add_button.clicked.connect(self.quick_add_account)
        quick_layout.addWidget(quick_add_button, 3, 0, 1, 2)
        
        quick_add_group.setLayout(quick_layout)
        layout.addWidget(quick_add_group)
        
        # アカウント操作メッセージエリア
        self.add_message_label = QLabel("📝 アカウント操作結果がここに表示されます")
        self.add_message_label.setStyleSheet("""
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
        """)
        layout.addWidget(self.add_message_label)
        
        # アカウントデータ管理
        data_management_group = QGroupBox("💾 データ管理")
        data_layout = QHBoxLayout()
        
        export_accounts_button = QPushButton("📤 エクスポート")
        export_accounts_button.setToolTip("アカウント情報をファイルに保存")
        export_accounts_button.clicked.connect(self.export_accounts)
        
        import_accounts_button = QPushButton("📥 インポート")
        import_accounts_button.setToolTip("ファイルからアカウント情報を読み込み")
        import_accounts_button.clicked.connect(self.import_accounts)
        
        backup_button = QPushButton("💾 バックアップ")
        backup_button.setToolTip("現在の設定をバックアップ")
        backup_button.clicked.connect(self.backup_settings)
        
        data_layout.addWidget(export_accounts_button)
        data_layout.addWidget(import_accounts_button)
        data_layout.addWidget(backup_button)
        data_layout.addStretch()
        data_management_group.setLayout(data_layout)
        layout.addWidget(data_management_group)
        
        tab.setLayout(layout)
        self.refresh_accounts_list()
        return tab

    def create_user_settings_tab(self):
        """Tab3: ユーザー設定画面（記憶機能）"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # タイトル
        title = QLabel("⚙️ ユーザー設定 & 記憶機能")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #2c3e50; 
            margin: 15px;
            text-align: center;
            background-color: #fff3cd;
            padding: 10px;
            border-radius: 8px;
        """)
        layout.addWidget(title)
        
        # 個人情報設定
        personal_group = QGroupBox("👤 個人情報設定")
        personal_layout = QGridLayout()
        
        personal_layout.addWidget(QLabel("ユーザー名:"), 0, 0)
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("あなたの名前")
        personal_layout.addWidget(self.user_name_input, 0, 1)
        
        personal_layout.addWidget(QLabel("メールアドレス:"), 1, 0)
        self.user_email_input = QLineEdit()
        self.user_email_input.setPlaceholderText("your@email.com")
        personal_layout.addWidget(self.user_email_input, 1, 1)
        
        personal_layout.addWidget(QLabel("組織/会社:"), 2, 0)
        self.user_organization_input = QLineEdit()
        self.user_organization_input.setPlaceholderText("所属組織（任意）")
        personal_layout.addWidget(self.user_organization_input, 2, 1)
        
        personal_group.setLayout(personal_layout)
        layout.addWidget(personal_group)
        
        # 自動化設定
        automation_group = QGroupBox("🤖 自動化設定")
        automation_layout = QVBoxLayout()
        
        self.auto_login_check = QCheckBox("起動時に自動ログインを実行")
        self.auto_login_check.setToolTip("アプリケーション起動時に自動的にログイン処理を開始")
        
        self.remember_last_account_check = QCheckBox("最後に使用したアカウントを記憶")
        self.remember_last_account_check.setToolTip("前回使用したアカウントを次回起動時に自動選択")
        
        self.remember_last_sites_check = QCheckBox("最後に選択したサイトを記憶")
        self.remember_last_sites_check.setToolTip("前回選択したECサイトを次回起動時に自動選択")
        
        self.auto_close_browser_check = QCheckBox("ログイン完了後にブラウザを自動で閉じる")
        self.auto_close_browser_check.setToolTip("全てのログイン処理完了後、一定時間でブラウザを閉じる")
        
        automation_layout.addWidget(self.auto_login_check)
        automation_layout.addWidget(self.remember_last_account_check)
        automation_layout.addWidget(self.remember_last_sites_check)
        automation_layout.addWidget(self.auto_close_browser_check)
        
        automation_group.setLayout(automation_layout)
        layout.addWidget(automation_group)
        
        # 表示設定
        display_group = QGroupBox("🎨 表示設定")
        display_layout = QGridLayout()
        
        display_layout.addWidget(QLabel("ログフォントサイズ:"), 0, 0)
        self.log_font_size_spin = QSpinBox()
        self.log_font_size_spin.setRange(8, 16)
        self.log_font_size_spin.setValue(11)
        self.log_font_size_spin.setSuffix("pt")
        display_layout.addWidget(self.log_font_size_spin, 0, 1)
        
        display_layout.addWidget(QLabel("ログ保持行数:"), 1, 0)
        self.log_max_lines_spin = QSpinBox()
        self.log_max_lines_spin.setRange(100, 2000)
        self.log_max_lines_spin.setValue(500)
        self.log_max_lines_spin.setSuffix("行")
        display_layout.addWidget(self.log_max_lines_spin, 1, 1)
        
        self.dark_theme_check = QCheckBox("ダークテーマを使用")
        self.dark_theme_check.setToolTip("ログエリアなどでダークテーマを使用")
        display_layout.addWidget(self.dark_theme_check, 2, 0, 1, 2)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # 使用統計
        stats_group = QGroupBox("📊 使用統計")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("使用統計情報がここに表示されます")
        self.stats_label.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 15px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            font-size: 12px;
        """)
        stats_layout.addWidget(self.stats_label)
        
        refresh_stats_button = QPushButton("🔄 統計更新")
        refresh_stats_button.clicked.connect(self.update_usage_stats)
        stats_layout.addWidget(refresh_stats_button)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 設定保存・リセット
        settings_control_group = QGroupBox("💾 設定管理")
        settings_control_layout = QHBoxLayout()
        
        save_user_settings_button = QPushButton("💾 設定保存")
        save_user_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_user_settings_button.clicked.connect(self.save_user_settings)
        
        reset_user_settings_button = QPushButton("🔄 設定リセット")
        reset_user_settings_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        reset_user_settings_button.clicked.connect(self.reset_user_settings)
        
        settings_control_layout.addWidget(save_user_settings_button)
        settings_control_layout.addWidget(reset_user_settings_button)
        settings_control_layout.addStretch()
        settings_control_group.setLayout(settings_control_layout)
        layout.addWidget(settings_control_group)
        
        tab.setLayout(layout)
        return tab

    def create_log_status_tab(self):
        """Tab4: ログ・ステータス画面"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # タイトル
        title = QLabel("📋 実行ログ & システム状況")
        title.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #2c3e50; 
            margin: 10px;
            text-align: center;
            background-color: #e3f2fd;
            padding: 10px;
            border-radius: 8px;
        """)
        layout.addWidget(title)
        
        # ステータス表示
        self.detailed_status = QLabel("📊 待機中 - システム準備完了")
        self.detailed_status.setStyleSheet("""
            background-color: #17a2b8; 
            color: white;
            padding: 12px; 
            border-radius: 5px;
            font-size: 13px;
            font-weight: bold;
        """)
        layout.addWidget(self.detailed_status)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #17a2b8;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #20c997;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # ログエリア
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # ログ制御ボタン
        log_control_layout = QHBoxLayout()
        
        clear_log_button = QPushButton("🧹 ログクリア")
        clear_log_button.clicked.connect(self.log_text.clear)
        
        save_log_button = QPushButton("💾 ログ保存")
        save_log_button.clicked.connect(self.save_log_to_file)
        
        auto_scroll_check = QCheckBox("自動スクロール")
        auto_scroll_check.setChecked(True)
        auto_scroll_check.stateChanged.connect(
            lambda state: setattr(self, 'auto_scroll_enabled', state == Qt.CheckState.Checked.value)
        )
        
        log_control_layout.addWidget(clear_log_button)
        log_control_layout.addWidget(save_log_button)
        log_control_layout.addWidget(auto_scroll_check)
        log_control_layout.addStretch()
        
        layout.addLayout(log_control_layout)
        
        tab.setLayout(layout)
        return tab

    def refresh_account_combo(self):
        """アカウントコンボボックスを更新"""
        self.account_combo.clear()
        self.account_combo.addItem("-- アカウントを選択 --", "")
        
        accounts = self.app_settings.get_accounts()
        for account_id, account_data in accounts.items():
            nickname = account_data.get("nickname", "")
            display_name = f"{nickname} ({account_id})" if nickname else account_id
            self.account_combo.addItem(display_name, account_id)
        
        # コンボボックス変更時の処理
        self.account_combo.currentTextChanged.connect(self.update_account_info_display)

    def refresh_accounts_list(self):
        """設定画面のアカウントリストを更新"""
        self.accounts_list_widget.clear()
        
        accounts = self.app_settings.get_accounts()
        if not accounts:
            item = QListWidgetItem("📝 まだアカウントが登録されていません")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.accounts_list_widget.addItem(item)
            return
        
        for account_id, account_data in accounts.items():
            nickname = account_data.get("nickname", "")
            display_text = f"👤 {nickname} ({account_id})" if nickname else f"👤 {account_id}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, account_id)
            self.accounts_list_widget.addItem(item)

    def update_account_info_display(self):
        """選択されたアカウントの情報を表示"""
        selected_account_id = self.account_combo.currentData()
        
        if not selected_account_id:
            self.account_info_label.setText("アカウントを選択してください")
            return
        
        accounts = self.app_settings.get_accounts()
        if selected_account_id in accounts:
            account_data = accounts[selected_account_id]
            nickname = account_data.get("nickname", "未設定")
            
            info_text = f"""
            📋 選択されたアカウント情報:
            • アカウントID: {selected_account_id}
            • ニックネーム: {nickname}
            • ステータス: ✅ 利用可能
            """
            self.account_info_label.setText(info_text.strip())
            
            # 最後に使用したアカウントを記憶
            self.user_prefs.set_preference("last_used_account", selected_account_id)
        else:
            self.account_info_label.setText("⚠️ アカウント情報が見つかりません")

    def load_saved_settings(self):
        """保存された設定を読み込み"""
        # デフォルトアカウントを選択
        default_account = self.settings_data.get("default_account", "")
        if default_account:
            for i in range(self.account_combo.count()):
                if self.account_combo.itemData(i) == default_account:
                    self.account_combo.setCurrentIndex(i)
                    break

        # 選択されたサイトを復元
        selected_sites = self.settings_data.get("selected_sites", ["楽天市場"])
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(item.text() in selected_sites)

    def load_user_preferences(self):
        """ユーザー設定を読み込み"""
        # 個人情報
        self.user_name_input.setText(self.user_prefs.get_preference("user_name", ""))
        self.user_email_input.setText(self.user_prefs.get_preference("user_email", ""))
        self.user_organization_input.setText(self.user_prefs.get_preference("user_organization", ""))
        
        # 自動化設定
        self.auto_login_check.setChecked(self.user_prefs.get_preference("auto_login", False))
        self.remember_last_account_check.setChecked(self.user_prefs.get_preference("remember_last_account", True))
        self.remember_last_sites_check.setChecked(self.user_prefs.get_preference("remember_last_sites", True))
        self.auto_close_browser_check.setChecked(self.user_prefs.get_preference("auto_close_browser", False))
        
        # 表示設定
        self.log_font_size_spin.setValue(self.user_prefs.get_preference("log_font_size", 11))
        self.log_max_lines_spin.setValue(self.user_prefs.get_preference("log_max_lines", 500))
        self.dark_theme_check.setChecked(self.user_prefs.get_preference("dark_theme", True))
        
        # 最後に使用したアカウントを復元
        if self.remember_last_account_check.isChecked():
            last_account = self.user_prefs.get_preference("last_used_account", "")
            if last_account:
                for i in range(self.account_combo.count()):
                    if self.account_combo.itemData(i) == last_account:
                        self.account_combo.setCurrentIndex(i)
                        break

        # 使用統計を更新
        self.update_usage_stats()

    def add_new_account(self):
        """新しいアカウントを追加"""
        dialog = AccountDialog(self)
        if dialog.exec() == AccountDialog.DialogCode.Accepted:
            account_id = dialog.account_id_input.text()
            password = dialog.password_input.text()
            nickname = dialog.nickname_input.text()
            
            # アカウントを保存
            self.app_settings.save_account(account_id, password, nickname)
            
            # 使用統計を更新
            self.increment_usage_stat("accounts_added")
            
            # UI更新
            self.refresh_accounts_list()
            self.refresh_account_combo()
            
            # メッセージ更新
            self.add_message_label.setText(f"✅ アカウント '{nickname or account_id}' を追加しました")
            self.add_log(f"✅ 新規アカウント追加: {nickname or account_id}")

    def quick_add_account(self):
        """クイック追加機能"""
        account_id = self.quick_account_id.text().strip()
        password = self.quick_password.text().strip()
        nickname = self.quick_nickname.text().strip()
        
        if not account_id or not password:
            QMessageBox.warning(self, "⚠️ 警告", "アカウントIDとパスワードは必須です。")
            return
        
        # 重複チェック
        accounts = self.app_settings.get_accounts()
        if account_id in accounts:
            reply = QMessageBox.question(self, "🔄 確認", 
                                        f"アカウント '{account_id}' は既に存在します。上書きしますか？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # アカウントを保存
        self.app_settings.save_account(account_id, password, nickname)
        
        # フィールドクリア
        self.quick_account_id.clear()
        self.quick_password.clear()
        self.quick_nickname.clear()
        
        # 使用統計を更新
        self.increment_usage_stat("accounts_added")
        
        # UI更新
        self.refresh_accounts_list()
        self.refresh_account_combo()
        
        # メッセージ更新
        display_name = nickname or account_id
        self.add_message_label.setText(f"🚀 '{display_name}' を即座に追加完了！")
        self.add_log(f"🚀 クイック追加: {display_name}")

    def edit_selected_account(self):
        """選択されたアカウントを編集"""
        selected_items = self.accounts_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "⚠️ 警告", "編集するアカウントを選択してください。")
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        accounts = self.app_settings.get_accounts()
        
        if account_id in accounts:
            account_data = accounts[account_id]
            
            dialog = AccountDialog(self, account_id, 
                                 account_data.get("password", ""), 
                                 account_data.get("nickname", ""))
            if dialog.exec() == AccountDialog.DialogCode.Accepted:
                new_password = dialog.password_input.text()
                new_nickname = dialog.nickname_input.text()
                
                self.app_settings.save_account(account_id, new_password, new_nickname)
                self.refresh_accounts_list()
                self.refresh_account_combo()
                
                self.add_message_label.setText(f"✏️ アカウント '{new_nickname or account_id}' を編集しました")
                self.add_log(f"✏️ アカウント編集: {new_nickname or account_id}")

    def delete_selected_account(self):
        """選択されたアカウントを削除（強化版）"""
        selected_items = self.accounts_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "⚠️ 警告", "削除するアカウントを選択してください。")
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # 確認ダイアログ（詳細表示）
        accounts = self.app_settings.get_accounts()
        account_data = accounts.get(account_id, {})
        nickname = account_data.get("nickname", "")
        
        confirm_msg = f"""
        以下のアカウントを完全に削除しますか？
        
        • アカウントID: {account_id}
        • ニックネーム: {nickname or '未設定'}
        
        ⚠️ この操作は取り消せません。
        """
        
        reply = QMessageBox.question(self, "🗑️ アカウント削除確認", confirm_msg.strip(),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # パスワードも完全に削除
            self.app_settings.delete_account(account_id)
            
            # 使用統計を更新
            self.increment_usage_stat("accounts_deleted")
            
            self.refresh_accounts_list()
            self.refresh_account_combo()
            
            self.add_message_label.setText(f"🗑️ アカウント '{account_id}' を完全削除しました")
            self.add_log(f"🗑️ アカウント完全削除: {account_id}")

    def delete_all_accounts(self):
        """全アカウントを削除（新機能）"""
        accounts = self.app_settings.get_accounts()
        if not accounts:
            QMessageBox.information(self, "ℹ️ 情報", "削除するアカウントがありません。")
            return
        
        # 確認ダイアログ
        confirm_msg = f"""
        登録されている全てのアカウント（{len(accounts)}個）を削除しますか？
        
        削除されるアカウント:
        {chr(10).join(f"• {data.get('nickname', id)} ({id})" for id, data in accounts.items())}
        
        ⚠️ この操作は取り消せません。
        """
        
        reply = QMessageBox.critical(self, "🗑️ 全アカウント削除確認", confirm_msg.strip(),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # パスワード再確認
            password, ok = QInputDialog.getText(self, "🔐 最終確認", 
                                              "確認のため「DELETE」と入力してください:",
                                              QLineEdit.EchoMode.Normal)
            
            if ok and password == "DELETE":
                # 全アカウントを削除
                deleted_count = len(accounts)
                for account_id in list(accounts.keys()):
                    self.app_settings.delete_account(account_id)
                
                # 使用統計を更新
                self.user_prefs.set_preference("accounts_deleted", 
                    self.user_prefs.get_preference("accounts_deleted", 0) + deleted_count)
                
                self.refresh_accounts_list()
                self.refresh_account_combo()
                
                self.add_message_label.setText(f"🗑️ 全アカウント（{deleted_count}個）を完全削除しました")
                self.add_log(f"🗑️ 全アカウント削除: {deleted_count}個のアカウントを削除")
                
                QMessageBox.information(self, "✅ 完了", "全てのアカウントが削除されました。")
            else:
                QMessageBox.information(self, "❌ キャンセル", "削除をキャンセルしました。")

    def export_accounts(self):
        """アカウント情報をエクスポート"""
        accounts = self.app_settings.get_accounts()
        if not accounts:
            QMessageBox.information(self, "ℹ️ 情報", "エクスポートするアカウントがありません。")
            return
        
        # ファイル保存ダイアログ
        file_path, _ = QFileDialog.getSaveFileName(
            self, "アカウント情報をエクスポート", 
            f"BOX01_accounts_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                export_data = self.app_settings.export_accounts_data()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                self.add_message_label.setText(f"✅ {len(accounts)}個のアカウントをエクスポートしました")
                self.add_log(f"📤 アカウントエクスポート: {file_path}")
                QMessageBox.information(self, "✅ 完了", f"アカウント情報をエクスポートしました:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "❌ エラー", f"エクスポートに失敗しました:\n{str(e)}")

    def import_accounts(self):
        """アカウント情報をインポート"""
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getOpenFileName(
            self, "アカウント情報をインポート", "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                # 確認ダイアログ
                accounts_count = len(import_data.get('accounts', {}))
                reply = QMessageBox.question(self, "📥 インポート確認", 
                                           f"{accounts_count}個のアカウントをインポートしますか？",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    imported_count = self.app_settings.import_accounts_data(import_data)
                    
                    self.refresh_accounts_list()
                    self.refresh_account_combo()
                    
                    self.add_message_label.setText(f"✅ {imported_count}個のアカウントをインポートしました")
                    self.add_log(f"📥 アカウントインポート: {file_path}")
                    QMessageBox.information(self, "✅ 完了", f"{imported_count}個のアカウントをインポートしました。")
                
            except Exception as e:
                QMessageBox.critical(self, "❌ エラー", f"インポートに失敗しました:\n{str(e)}")

    def backup_settings(self):
        """設定をバックアップ"""
        # バックアップファイル保存
        file_path, _ = QFileDialog.getSaveFileName(
            self, "設定をバックアップ", 
            f"BOX01_backup_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                backup_data = self.app_settings.create_backup_data()
                # ユーザー設定も追加
                backup_data["user_preferences"] = self.user_prefs.load_user_preferences()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                self.add_log(f"💾 設定バックアップ: {file_path}")
                QMessageBox.information(self, "✅ 完了", f"設定をバックアップしました:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "❌ エラー", f"バックアップに失敗しました:\n{str(e)}")

    def save_user_settings(self):
        """ユーザー設定を保存"""
        preferences = {
            # 個人情報
            "user_name": self.user_name_input.text(),
            "user_email": self.user_email_input.text(),
            "user_organization": self.user_organization_input.text(),
            
            # 自動化設定
            "auto_login": self.auto_login_check.isChecked(),
            "remember_last_account": self.remember_last_account_check.isChecked(),
            "remember_last_sites": self.remember_last_sites_check.isChecked(),
            "auto_close_browser": self.auto_close_browser_check.isChecked(),
            
            # 表示設定
            "log_font_size": self.log_font_size_spin.value(),
            "log_max_lines": self.log_max_lines_spin.value(),
            "dark_theme": self.dark_theme_check.isChecked(),
        }
        
        self.user_prefs.save_user_preferences(preferences)
        
        # ログフォントサイズを即座に適用
        self.update_log_font_size()
        
        self.add_log("💾 ユーザー設定を保存しました")
        QMessageBox.information(self, "✅ 完了", "ユーザー設定を保存しました。")

    def reset_user_settings(self):
        """ユーザー設定をリセット"""
        reply = QMessageBox.question(self, "🔄 設定リセット確認",
                                    "ユーザー設定を初期値にリセットしますか？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 設定をクリア
            self.user_prefs.settings.beginGroup("user_preferences")
            self.user_prefs.settings.clear()
            self.user_prefs.settings.endGroup()
            
            # フィールドをリセット
            self.user_name_input.clear()
            self.user_email_input.clear()
            self.user_organization_input.clear()
            
            self.auto_login_check.setChecked(False)
            self.remember_last_account_check.setChecked(True)
            self.remember_last_sites_check.setChecked(True)
            self.auto_close_browser_check.setChecked(False)
            
            self.log_font_size_spin.setValue(11)
            self.log_max_lines_spin.setValue(500)
            self.dark_theme_check.setChecked(True)
            
            self.add_log("🔄 ユーザー設定をリセットしました")
            QMessageBox.information(self, "✅ 完了", "ユーザー設定をリセットしました。")

    def update_usage_stats(self):
        """使用統計を更新"""
        accounts_count = len(self.app_settings.get_accounts())
        accounts_added = self.user_prefs.get_preference("accounts_added", 0)
        accounts_deleted = self.user_prefs.get_preference("accounts_deleted", 0)
        login_attempts = self.user_prefs.get_preference("login_attempts", 0)
        successful_logins = self.user_prefs.get_preference("successful_logins", 0)
        
        stats_text = f"""
        📊 使用統計情報:
        
        • 現在のアカウント数: {accounts_count}個
        • 累計追加アカウント: {accounts_added}個
        • 累計削除アカウント: {accounts_deleted}個
        • ログイン試行回数: {login_attempts}回
        • 成功ログイン回数: {successful_logins}回
        • 成功率: {(successful_logins/login_attempts*100) if login_attempts > 0 else 0:.1f}%
        
        📅 最終利用日時: {self.user_prefs.get_preference('last_usage_date', '未記録')}
        """
        
        self.stats_label.setText(stats_text.strip())
        
        # 最終利用日時を更新
        self.user_prefs.set_preference('last_usage_date', QDateTime.currentDateTime().toString())

    def increment_usage_stat(self, stat_name):
        """使用統計をインクリメント"""
        current_value = self.user_prefs.get_preference(stat_name, 0)
        self.user_prefs.set_preference(stat_name, current_value + 1)

    def update_log_font_size(self):
        """ログフォントサイズを更新"""
        font_size = self.log_font_size_spin.value()
        current_style = self.log_text.styleSheet()
        # フォントサイズ部分を更新
        new_style = re.sub(r'font-size:\s*\d+px', f'font-size: {font_size}px', current_style)
        self.log_text.setStyleSheet(new_style)

    def save_log_to_file(self):
        """ログをファイルに保存"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ログを保存", 
            f"BOX01_log_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                
                self.add_log(f"💾 ログ保存: {file_path}")
                QMessageBox.information(self, "✅ 完了", f"ログを保存しました:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "❌ エラー", f"ログ保存に失敗しました:\n{str(e)}")

    def get_account_data(self):
        """選択されたアカウントのデータを取得"""
        selected_account_id = self.account_combo.currentData()
        
        if not selected_account_id:
            return None
        
        accounts = self.app_settings.get_accounts()
        if selected_account_id in accounts:
            account_info = accounts[selected_account_id]
            return {
                'account_id': selected_account_id,
                'password': account_info['password'],
                'nickname': account_info.get('nickname', '')
            }
        
        return None

    def start_selenium(self):
        """自動ログイン開始"""
        print("🚀 BOX0.1 自動ログインシステム開始")
        
        # アカウント情報取得
        account_data = self.get_account_data()
        
        if not account_data:
            QMessageBox.warning(self, "⚠️ 警告", "アカウントを選択してください。")
            self.add_log("❌ アカウント未選択 - 実行不可")
            return

        # 選択されたECサイトを取得
        selected_sites = self.get_selected_sites()
        
        if not selected_sites:
            QMessageBox.warning(self, "⚠️ 警告", "ECサイトを選択してください。")
            self.add_log("❌ ECサイト未選択 - 実行不可")
            return

        # 使用統計を更新
        self.increment_usage_stat("login_attempts")

        # UIの状態変更
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # ログタブに自動切り替え
        self.tab_widget.setCurrentIndex(3)
        
        # ログクリア
        self.log_text.clear()
        self.add_log("🚀 === BOX0.1 自動ログインシステム開始 ===")
        
        account_display = account_data.get('nickname') or account_data['account_id']
        self.add_log(f"👤 使用アカウント: {account_display}")
        self.add_log(f"🏪 対象サイト: {', '.join(selected_sites)}")
        
        # 最後に選択したサイトを記憶
        if self.remember_last_sites_check.isChecked():
            self.user_prefs.set_preference("last_selected_sites", selected_sites)
        
        # Seleniumスレッド開始
        self.selenium_thread = SeleniumThread(self.web_engine_view, account_data, selected_sites)
        self.selenium_thread.finished.connect(self.on_selenium_finished)
        self.selenium_thread.status_update.connect(self.update_status)
        self.selenium_thread.progress_update.connect(self.update_progress)
        self.selenium_thread.error_occurred.connect(self.on_error_occurred)
        self.selenium_thread.log_message.connect(self.add_log)
        self.selenium_thread.account_success.connect(self.on_account_success)
        self.selenium_thread.start()

    def stop_selenium(self):
        """Selenium処理を停止"""
        if self.selenium_thread and self.selenium_thread.isRunning():
            self.selenium_thread.stop()
            self.update_status("停止処理中...")
            self.add_log("⏹️ ユーザーによる停止要求")

    def update_status(self, message):
        """ステータスを更新"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        status_text = f"[{timestamp}] {message}"
        
        # メインタブのステータス更新
        self.main_status.setText(f"📊 {message}")
        
        # ログタブの詳細ステータス更新
        self.detailed_status.setText(f"📊 {status_text}")

    def update_progress(self, value):
        """プログレスバーを更新"""
        self.progress_bar.setValue(value)

    def add_log(self, message):
        """ログメッセージを追加"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        
        # 行数制限
        max_lines = self.log_max_lines_spin.value()
        document = self.log_text.document()
        if document.lineCount() > max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 
                              document.lineCount() - max_lines)
            cursor.removeSelectedText()
        
        # 自動スクロール
        if hasattr(self, 'auto_scroll_enabled') and self.auto_scroll_enabled:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def on_account_success(self, account_name, site_name):
        """アカウント成功時の処理"""
        success_message = f"🎉 {account_name} → {site_name} ログイン成功！"
        self.add_message_label.setText(success_message)
        self.add_log(success_message)
        
        # 成功統計を更新
        self.increment_usage_stat("successful_logins")

    def on_error_occurred(self, error_message):
        """エラー発生時の処理"""
        QMessageBox.critical(self, "❌ エラー", error_message)
        self.update_status("エラー発生")
        self.add_log(f"❌ 致命的エラー: {error_message}")

    def on_selenium_finished(self):
        """Selenium処理完了時の処理"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.update_status("処理完了")
        self.add_log("🏁 BOX0.1 自動ログインシステム完了")

    def get_selected_sites(self):
        """選択されたECサイトのリストを取得"""
        selected_sites = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_sites.append(item.text())
        return selected_sites

    def closeEvent(self, event):
        """アプリケーション終了時の処理"""
        if self.selenium_thread and self.selenium_thread.isRunning():
            self.selenium_thread.stop()
            self.selenium_thread.wait(3000)
        
        # 最終利用日時を更新
        self.user_prefs.set_preference('last_usage_date', QDateTime.currentDateTime().toString())
        
        self.add_log("👋 アプリケーション終了")
        event.accept()


def main():
    """メイン関数"""
    print("🚀 BOX0.1 PyQt6 Helper - プロフェッショナル版 起動開始")
    
    app = QApplication(sys.argv)
    
    # アプリケーション情報設定
    app.setApplicationName("BOX0.1 PyQt6 Helper - プロフェッショナル版")
    app.setApplicationVersion("2.2.0")
    app.setOrganizationName("BOX0.1")
    
    # フォント設定
    font = QFont()
    font.setFamily("Yu Gothic UI")
    font.setPointSize(9)
    app.setFont(font)
    
    # メインウィンドウ作成・表示
    window = MainWindow()
    window.show()
    
    print("✅ BOX0.1 PyQt6 Helper プロフェッショナル版 表示完了")
    print("📋 機能: 5サイト自動ログイン + アカウント管理 + ユーザー設定記憶 + 完全削除")
    
    # アプリケーション実行
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
