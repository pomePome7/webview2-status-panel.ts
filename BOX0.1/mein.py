# -*- coding: utf-8 -*-

import sys
import os

from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,QHBoxLayout, QListWidget, QListWidgetItem,QCheckBox, QLineEdit, QLabel, QMessageBox)
from PyQt6.QtCore import QUrl, QThread, pyqtSignal, QLibraryInfo, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from selenium import webdriver
# QLibraryInfoを利用してPyQt6のパスを取得
qt_dir = os.path.join(os.path.dirname(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibrariesPath)), "Qt")
from selenium.webdriver.chrome.options import Options

# Selenium 関連のインポート
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


resources_path = os.path.join(qt_dir, "resources")
translations_path = os.path.join(qt_dir, "translations")
qtwebengine_resources_path = os.path.join(qt_dir, "resources", "qtwebengine_resources.pak")

datas =[
    (resources_path, "PyQt6/Qt/resources"),
    (translations_path, "PyQt6/Qt/translations"),
]
if os.path.exists(qtwebengine_resources_path):
    datas.append((qtwebengine_resources_path, "PyQt6/Qt/resources"))

class SeleniumThread(QThread):
    finished = pyqtSignal()

    def __init__(self, web_engine_view, account_id, password, selected_sites):
        super().__init__()
        self.web_engine_view = web_engine_view
        self.account_id = account_id
        self.password = password
        self.selected_sites = selected_sites
        self.driver = None
    
    def run(self):
        try:
            # Chromeオプションを設定
            chrome_options = Options()
            chrome_options.add_argument("--remote-debugging-port=9223")  # リモートデバッグポートを指定


            # webdriver-managerを使用してChromeDriverを自動管理
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # 選択されたECサイトにログイン
            for site in self.selected_sites:
                if site == "楽天市場":
                    self.login_to_rakuten(self.driver, self.account_id, self.password)
                    # QWebEngineViewにURLをロード
                    self.web_engine_view.load(QUrl("https://www.google.com"))



                    # アプリケーションが閉じられるまでChromeを開いたままにする
                    self.wait_for_termination()
            
                    # ブラウザを閉じる
                    self.driver.quit()
                    print("Chrome終了")
                    self.finished.emit()
        

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            if self.driver:
                self.driver.quit()
                self.finished.emit()


    
    def wait_for_termination(self):
        # Chromeが閉じられるまで待機 (例: 5秒ごとに確認)
        try:
            while True:
                # ウィンドウハンドルが存在するか確認
                self.driver.window_handles
        except:
            #Chromeが閉じられた
            return
    
    def login_to_rakuten(self, driver, account_id, password):
        """楽天市場にログインする関数（2023年以降のログイン画面に対応）"""
        try:
            # まずログインページに移動
            driver.get("https://grp01.id.rakuten.co.jp/rms/nid/loginfwd")

            # ID入力フィールドを待機して入力
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "user_id"))
            )
            username_field.clear()
            username_field.send_keys(account_id)

            # 次へボタンをクリック
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            next_button.click()

            # パスワード入力フィールドを待機して入力
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "password_current"))
            )
            password_field.clear()
            password_field.send_keys(password)

            # ログインボタンをクリック（再度「次へ」ボタン）
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            login_button.click()

            # ログイン後のページが表示されるのを待機
            WebDriverWait(driver, 10).until(
                EC.url_contains("www.rakuten.co.jp")
            )
            print("楽天市場にログインしました")
            return True
        
        except TimeoutException:
            print("タイムアウト：ページの読み込みに時間がかかりすぎています")
            return False
        except Exception as e:
            print(f"ログイン中にエラーが発生しました: {e}")
            return False

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # フォントサイズを設定
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(12)  # フォントサイズを12ptに設定
        app.setFont(font)

        self.setWindowTitle("ECサイト選択")
        self.setGeometry(100, 100, 400, 400)

        # ECサイトのリスト
        self.ec_sites = ["楽天市場", "Amazon", "Yahoo!ショッピング", "Qoo10"]

        # QListWidget の作成
        self.list_widget = QListWidget()

        # ECサイトをリストに追加
        for site in self.ec_sites:
            item = QListWidgetItem(site)
            item.setText(site)  # テキストを明示的に設定

            # QCheckBox を作成して、リストアイテムに関連付ける
            checkbox = QCheckBox(site)
            checkbox.setStyleSheet("margin: 5px; font-size: 14px;")  # スタイルを調整（フォントサイズ追加）
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, checkbox)

        # アカウントID とパスワードの入力フィールド
        self.account_id_label = QLabel("アカウントID:")
        self.account_id_input = QLineEdit()
        self.password_label = QLabel("パスワード:")
        self.password_input = QLineEdit()

        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)  # パスワードをマスク

        # 開始ボタン
        self.start_button = QPushButton("開始")
        self.start_button.clicked.connect(self.start_selenium)

        # レイアウト
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.account_id_label)
        layout.addWidget(self.account_id_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.start_button)

        self.setLayout(layout)
        self.web_engine_view = QWebEngineView()

    def start_selenium(self):
        """Selenium スレッドを開始"""
        # アカウントID とパスワードを取得
        account_id = self.account_id_input.text()
        password = self.password_input.text()

        # 選択されたECサイトを取得
        selected_sites = self.get_selected_sites()

        if not account_id or not password:
            QMessageBox.warning(self, "警告", "アカウントIDとパスワードを入力してください。")
            return
        
        if not selected_sites:
            QMessageBox.warning(self, "警告", "ECサイトを選択してください。")
            return
        

        # SeleniumThread インスタンスを作成して、スレッドを開始
        self.selenium_thread = SeleniumThread(self.web_engine_view, account_id, password, selected_sites)
        self.selenium_thread.finished.connect(self.on_selenium_finished)
        self.start_button.setEnabled(False)  # ボタンを無効化
        self.selenium_thread.start()
    
    def on_selenium_finished(self):
        self.start_button.setEnabled(True)  # ボタンを有効化

    def get_selected_sites(self):
        """選択されたECサイトのリストを取得する"""
        selected_sites = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_sites.append(item.text())
        return selected_sites




if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
