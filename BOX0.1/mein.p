# TODO:mein.py
import sys
import os
import re
import zipfile
import subprocess
import requests
import platform
from io import BytesIO
import time  # time.sleepの使用に必要
import traceback
import winreg  # Windows専用


from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
                            QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QLabel,
                            QMessageBox, QProgressBar, QComboBox, QInputDialog,QProgressBar, QFrame) # QFrameを追加して区切り線
from PyQt6.QtCore import (QUrl, QThread, pyqtSignal, QLibraryInfo, Qt, QTimer,
                        QSettings, QDateTime) # QDateTime を追加
# QtWebEngineCore は WebView 初期化時に必要
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
# QtNetwork（ネットワーク） は Cookie 設定に必要
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtGui import QDesktopServices  # QtGuiからインポート

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
# from selenium.webdriver.common.keys import Keys #TODO:現状未使用
from settings import AppSettings, SettingsDialog, AccountDialog # settings.pyを活用して、main.pyのMainWindowクラスに複数アカウント管理機能を統合

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
    finished = pyqtSignal()
    status_update = pyqtSignal(str)  # ステータス更新用シグナル
    progress_update = pyqtSignal(int)  # 進捗状況更新用シグナル
    login_success = pyqtSignal(bool)  # ログイン成功/失敗を通知するシグナル
    # Cookie連携用の新しいシグナル（リストと文字列を送信）
    cookies_ready = pyqtSignal(list, str)
    url_update = pyqtSignal(str)  # UI更新用のシグナル（URLをメインスレッドに通知）
    browser_page_source = pyqtSignal(str)  # HTML内容を送信するシグナル

    def __init__(self, account_id, password, selected_sites, use_dummy=False):
        super().__init__()
        self.account_id = account_id
        self.password = password
        self.selected_sites = selected_sites
        self.driver = None
        self.is_running = True
        self.use_dummy = use_dummy # ダミーモードフラグ
    
    def run(self):
        try:
            # 進捗状況を更新（10%）
            self.progress_update.emit(10)
            self.status_update.emit("ChromeDriverのパスを確認中...")
            
            # ChromeDriverをダウンロード/取得
            chrome_driver_path = download_chromedriver()
            if not chrome_driver_path:
                self.status_update.emit("ChromeDriverの取得に失敗しました。処理を中止します。")
                self.login_success.emit(False)
                return # スレッドを終了
            
            # 進捗状況を更新（20%）
            self.progress_update.emit(20)
            self.status_update.emit("Chromeオプションを設定中...")

            # Chromeオプションを設定
            chrome_options = Options()
            chrome_options.add_argument("--remote-debugging-port=9223")  # リモートデバッグポートを指定
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # chrome_options.add_argument("--disable-web-security")  # CORSエラー対策
            # chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")  # クロスドメイン問題対策
            chrome_options.add_argument("--disable-extensions")  # 広告ブロッカーを無効化
            chrome_options.add_argument("--disable-gpu")  # GPUハードウェアアクセラレーションを無効化
            # chrome_options.add_argument("--headless")  # ヘッドレスモードを追加 WebVewに表示するならヘッドレス不要の場合も
            chrome_options.add_argument("--window-size=1280,1080")
            
            service = Service(chrome_driver_path)
            
            # 進捗状況を更新（30%）
            self.progress_update.emit(30)
            self.status_update.emit("Selenium WebDriverを起動中...")
            class DummyDriver:
                def __init__(self):
                    self._current_url = "https://dummy.url"
                    
                def get(self, url):
                    """URLにアクセスするメソッド"""
                    print(f"ダミードライバーでアクセス: {url}")
                    self._current_url = url
                    return None
                def get_cookies(self):
                    return [{"name": "dummy", "value": "cookie", "domain": "rakuten.co.jp", "path": "/"}]
                def quit(self):
                    print("Dummy driver quit")
                
                @property
                def current_url(self):
                    return self._current_url
                @property
                def page_source(self):
                    return "<html><body><h1>ダミーページ</h1></body></html>"
            try:
                # self.driver = webdriver.Chrome(service=service, options=chrome_options) # 実際のWebDriver起動
                if self.use_dummy:
                    print("WebDriverを起動します（ダミードライバーを使用）") # WebDriverがない環境でのエラー回避
                    # ダミーのdriverオブジェクトを作成（実際のテストには不要）
                    self.driver = DummyDriver()
                else:
                    print("WebDriverを起動します（実際のWebDriverを使用）")
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.driver.set_page_load_timeout(60)  # 60秒に設定                
                self.status_update.emit("ブラウザを起動しました")
            except WebDriverException as e:
                self.status_update.emit(f"ブラウザの起動に失敗しました: {e}")
                self.login_success.emit(False)
                return # スレッド終了
            except Exception as e: # WerDriverがｌない場合などの他のエラーも推奨
                self.status_update.emit(f"WebDriverの初期中に予期せぬエラーが発生しました: {e}")
                print(traceback.format_exc()) # 詳細なエラー
                self.login_success.emit(False)
                return # スレッド終了
            
            # 進捗状況を更新（40%）
            self.progress_update.emit(40)

            # 選択されたECサイトにログインする
            login_result = False # 初期化
            for site in self.selected_sites:
                if site == "楽天市場":
                    self.status_update.emit(f"{site}へのログインを開始...")
                    self.progress_update.emit(50)
                    login_result = self.login_to_rakuten(self.driver, self.account_id, self.password)
                    self.progress_update.emit(70)
                    break
                
            # ログイン情報に基づいて処理
            if login_result:
                self.status_update.emit("ログインに成功。Cookieを取得中...")
                try:
                    # Cookieと最終URLを取得
                    current_url = self.driver.current_url
                    cookies = self.driver.get_cookies()
                    print(f"取得したCookie数: {len(cookies)}") # デバッグ
                    
                    # CookieとURLをメインスレッドに送信
                    self.cookies_ready.emit(cookies, current_url)
                    self.status_update.emit("Cookie情報を送信しました。")
                    self.login_success.emit(True)
                    self.progress_update.emit(90)
                    
                except Exception as e:
                    self.status_update.emit(f"Cookie取得/送信エラー: {e}")
                    print(traceback.format_exc())# 詳細なエラー                    
                # finally:ブロックは不要、ログイン成功/失敗に関わらず後続のdriver終了処理を行いたい場合は、if/elseの外に記述する
                # ただし、元のコードの構造を維持するため、ここにfinallyを残すのではなく、if/elseの各ブロックでdriver.quit()を呼ぶ
                    # Cookie送信後,WebDriverを終了
                    if self.driver:
                        try:
                            self.driver.quit()
                            print("Selenium WebDriverを終了しました。")
                        except Exception as quit_error:
                            print(f"WebDriver終了エラー: {quit_error}")
                        self.driver = None # 参照をクリア
                        
            else:
                self.status_update.emit("ログインに失敗しました。")
                self.login_success.emit(False)
                # 失敗した場合もWebDriverを終了
                # if self.driver:
                #     try:
                #         self.driver.quit()
                #     except Exception: pass
                #     self.driver = None
                self.progress_update.emit(100)
                self.status_update.emit("Selenium処理終了")
                
        except Exception as e:
            print(f"Seleniumスレッド実行エラー: {e}")
            print(traceback.format_exc()) # 詳細なエラーログ
            self.status_update.emit(f"スレッドエラー: {e}")
            self.login_success.emit(False) # エラー時は失敗として通知
            # エラー発生時もWebDriverを閉じる試み
            # if self.driver:
            #     try:
            #         self.driver.quit()
            #     except Exception: pass
            #     self.driver = None
        finally:
            # スレッドの最後に必ずWebDriverを終了する
            if self.driver:
                try:
                    self.driver.quit()
                    print("Selenium WebDriverを終了しました。")
                except Exception as quit_error:
                    print(f"WebDriver終了エラー: {quit_error}")
                finally:
                    self.driver = None # 参照をクリア
            # スレッド終了を通知
            self.finished.emit()
            print("Seleniumスレッド終了")            

    def login_to_rakuten(self, driver, account_id, password):
        """楽天市場にログインする関数"""
        try:
            # デバッグ出力
            print(f"ログイン開始: account_id={account_id}")
            self.status_update.emit("楽天市場ログインページにアクセスしています...")

            # 直接SSOログインページに移動
            login_page_url = "https://login.account.rakuten.com/sso/authorize?client_id=rakuten_ichiba_top_web&service_id=s2458&response_type=code&scope=openid&redirect_uri=https%3A%2F%2Fwww.rakuten.co.jp%2F"
            driver.get(login_page_url)
            
            print(f"アクセスしたURL: {login_page_url}")
            # --- 要素待機と操作 (ここを安定化させるのが鍵) ---
            wait = WebDriverWait(driver, 15) # 待機時間設定

            # HTML内容を送信
            self.browser_page_source.emit(driver.page_source)
            
            username_field = None
            username_patterns = [
                (By.CSS_SELECTOR, "input[id^='user']"), # IDが'user'で始まる
                (By.CSS_SELECTOR, "input[id*='user']"), # IDに'user'を含む
                (By.XPATH, "//input[contains(@id, 'user')]"),
                (By.NAME, "user_id"), # name属性がuser_id
                (By.XPATH, "//input[contains(@name, 'user')]"),
                (By.CSS_SELECTOR, "input[type='text']"), # フォールバック: テキスト入力フィールド
            ]
            for by, pattern in username_patterns:
                try:
                    username_field = wait.until(EC.presence_of_element_located((by, pattern)))
                    print(f"ユーザーIDフィールドを発見: {by} {pattern}")
                    break
                except Exception:
                    continue
                
            if not username_field:
                print("ユーザーIDフィールドが見つかりません")
                self.status_update.emit("ユーザーIDフィールドが見つかりません")
                return False
            
            # ユーザーID入力処理
            self.status_update.emit("ユーザーID入力中...")
            username_field.clear()
            username_field.send_keys(account_id)
            print("ユーザーIDを入力しました")
            
            # --- 追加: 以下のコードを追加 ---
            # 「次へ」ボタンも動的クラス/IDに対応
            next_button = None
            next_button_patterns = [
                (By.XPATH, "//div[contains(@class, 'button__submit')]"),
                (By.XPATH, "//div[contains(@id, 'cta')]"),
                (By.XPATH, "//button[contains(text(), '次へ')]"),
                (By.XPATH, "//div[contains(text(), '次へ')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']")
            ]
            for by, pattern in next_button_patterns:
                try:
                    next_button = wait.until(EC.element_to_be_clickable((by, pattern)))
                    print(f"次へボタンを発見: {by} {pattern}")
                    break
                except Exception:
                    continue
                
            if next_button:
                next_button.click()
                print("「次へ」ボタンをクリックしました")
                time.sleep(1) # ボタンクリック後の短い待機
            else:
                print("「次へ」ボタンがないか、既にパスワード入力画面です")
                
            # --- 追加: 以下のコードを追加 ---
            # パスワード入力フィールドも動的ID対応
            password_field = None
            password_patterns = [
                (By.ID, "password_current"),
                (By.CSS_SELECTOR, "input[id^='pass']"),
                (By.XPATH, "//input[contains(@id, 'pass')]"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@type='password']"),
                (By.XPATH, "//input[contains(@name, 'pass')]"),
            ]
            for by, pattern in password_patterns:
                try:
                    password_field = wait.until(EC.presence_of_element_located((by, pattern)))
                    print(f"パスワードフィールドを発見: {by} {pattern}")
                    break
                except Exception:
                    continue
                
            if not password_field:
                print("パスワード入力が見つかりません")
                self.status_update.emit("パスワード入力フィールドが見つかりません")
                return False
            # --- フィールド・コンテインズをここまで追加
            
            # パスワード入力処理
            self.status_update.emit("パスワード入力中...")
            password_field.clear()
            password_field.send_keys(password)
            print("パスワードを入力しました")
            
            
            # ログインボタンも動的クラス/ID対応
            login_submit = None
            login_submit_patterns = [
                (By.XPATH, "//div[contains(@class, 'button__submit') or contains(@id, 'cta')]"),
                (By.XPATH, "//button[contains(text(), 'ログイン')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']")
            ]
            for by, pattern in login_submit_patterns:
                try:
                    login_submit = wait.until(EC.element_to_be_clickable((by, pattern)))
                    print(f"ログインボタンを発見: {by} {pattern}")
                    break
                except Exception:
                    continue
                
            if not login_submit:
                print("ログインボタンが見つかりません")
                self.status_update.emit("ログインボタンが見つかりません")
                return False
            
            # ログインボタンクリック
            self.status_update.emit("ログイン中...")
            login_submit.click()
            print("ログインボタンをクリックしました")
            
            # ログイン後のリダイレクトを待機
            WebDriverWait(driver, 30).until(
                lambda d: "www.rakuten.co.jp" in d.current_url or "rate.co.jp" in d.current_url
            )
            print(f"ログイン後の現在のURL: {driver.current_url}")
            self.status_update.emit("楽天市場にログインしました")
            
            # ログイン失敗の検出
            if "login.account.rakuten.com" in driver.current_url:
                print("ログインに失敗しました")
                self.status_update.emit("ログインに失敗しました。認証情報を確認してください。")
                return False
            
            return True
        
        except NoSuchElementException as e:
            print(f"要素が見つかりません: {e}")
            self.status_update.emit(f"ログインフォームの要素が見つかりません: {e}")
            return False
        except Exception as e:
            print(f"ログイン中にエラー: {e}")
            self.status_update.emit(f"ログイン中にエラー: {e}")
            return False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # ウィンドウ設定
        self.setWindowTitle("Hello World")
        self.setGeometry(100, 100, 400, 200)
        
        # レイアウト
        layout = QVBoxLayout()
        
        # ラベル作成
        label = QLabel("Hello World!")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px;")
        
        # レイアウトに追加
        layout.addWidget(label)
        
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
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
        
        # TODO:chrome 115以降は新しいURLフォーマットを使用
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
    
    #     # Chrome 135以降の場合は134の最新バージョンを使用
    #     if int(major_version) >= 135:
    #         driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{available_chrome_versions[0]}/win64/chromedriver-win64.zip"
    #         print(f"Chrome {major_version}用に互換性のある{available_chrome_versions[0]}バージョンを使用します")
    #     if major_version == "134":
    #         # 同じメジャーバージョンの場合は最新の互換性のあるマイナーバージョンを使用
    #         driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{available_chrome_versions[0]}/win64/chromedriver-win64.zip"
    #         print(f"Chrome 134用に最新の{available_chrome_versions[0]}バージョンを使用します")
    #     else:
    #         # 古いバージョンの場合は既知の安定バージョンを使用
    #         driver_url = f"https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_win64.zip"
    #         print(f"古いChrome {major_version}用に114.0.5735.90バージョンを使用します")
        
    #     print(f"ダウンロードURL: {driver_url}")
        
    #     # ダウンロード試行
    #     response = requests.get(driver_url)
    #     if response.status_code != 200:
    #         print(f"ChromeDriverのダウンロードに失敗しました。ステータスコード: {response.status_code}")
            
    #         # 別のバージョンを順番に試す
    #         for version in available_chrome_versions[1:]:
    #             backup_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"
    #             print(f"代替URLを試行: {backup_url}")
    #             backup_response = requests.get(backup_url)
    #             if backup_response.status_code == 200:
    #                 response = backup_response
    #                 print(f"代替URLからのダウンロードに成功しました: {backup_url}")
    #                 break
                
    #         # すべての代替URLが失敗した場合
    #         if response.status_code != 200:
    #             print("すべてのURLでのダウンロードに失敗しました。webdriver_managerを使用します。")
    #             try:
    #                 # webdriver_managerを使用
    #                 from webdriver_manager.chrome import ChromeDriverManager
    #                 driver_path = ChromeDriverManager().install()
    #                 print(f"webdriver_managerでのダウンロードに成功しました: {driver_path}")
    #                 return driver_path
    #             except Exception as e:
    #                 print(f"webdriver_managerでのダウンロードにも失敗しました: {e}")
    #                 return None
        
    #     # ZIPファイルを展開
    #     with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
    #         driver_name = "chromedriver.exe"  # Windowsの場合
    #         # ZIPファイルの内容を表示
    #         file_list = zip_file.namelist()
    #         print(f"ZIPファイル内の内容: {file_list}")  # デバッグ用
            
    #         # chromedriver.exeを含むファイルパスを探す
    #         driver_in_zip = None
    #         for file in file_list:
    #             if file.endswith(driver_name):
    #                 driver_in_zip = file
    #                 break
                
    #         if not driver_in_zip:
    #             print(f"ZIPファイル内にChromeDriverが見つかりませんでした。ファイル一覧: {file_list}")
    #             return None
            
    #         # 既存のChromeDriverを削除
    #         driver_path = os.path.join(destination, driver_name)
    #         if os.path.exists(driver_path):
    #             try:
    #                 os.remove(driver_path)
    #                 print(f"既存のChromeDriverを削除しました: {driver_path}")
    #             except Exception as e:
    #                 print(f"既存のChromeDriverの削除に失敗しました: {e}")
            
    #         # 新しいChromeDriverを展開
    #         with open(driver_path, 'wb') as f:
    #             f.write(zip_file.read(driver_in_zip))
            
    #         print(f"ChromeDriverを正常にダウンロードしました: {driver_path}")
    #         return driver_path
        
    # except Exception as e:
    #     print(f"ChromeDriverダウンロードエラー: {e}")
    #     # エラーの場合、既存のChromeDriverのパスを返す（存在する場合）
    #     if destination:
    #         driver_name = "chromedriver.exe"
    #         driver_path = os.path.join(destination, driver_name)
    #         if os.path.exists(driver_path):
    #             print(f"既存のChromeDriverを使用します: {driver_path}")
    #             return driver_path
    #     return None
