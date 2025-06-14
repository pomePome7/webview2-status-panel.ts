# TODO: settings.py
import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
                            QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QLabel,
                            QMessageBox, QProgressBar, QDialog, QTabWidget, QGroupBox, QFormLayout,
                            QInputDialog) # QInputDialog を追加
from PyQt6.QtCore import QSettings, Qt


# 設定管理クラス
class AppSettings:
    def __init__(self, organization_name="YourCompany", application_name="ECLoginApp"):
        # アプリケーション情報の設定
        self.organization_name = organization_name
        self.application_name = application_name
                
        # QSettingsオブジェクトの初期化
        self.settings = QSettings(self.organization_name, self.application_name)
        
        # デフォルト設定
        self.default_settings = {
            "accounts": {},
            "selected_sites": ["楽天市場"],
            "auto_login": False,
            "remember_accounts": True,
            "default_account": "",
            "api_key": "",
            "application_id": "",
            "affiliate_id": ""
        }
        
    def load_settings(self):
        # 保存された設定を読み込む
        settings_dict = {}
        
        # アカウント情報の読み込み
        settings_dict["accounts"] = {}
        self.settings.beginGroup("accounts")
        account_ids = self.settings.childGroups()
        for account_id in account_ids:
            self.settings.beginGroup(account_id)
            settings_dict["accounts"][account_id] = {
                "password": self.settings.value("password", "", str),
                "nickname": self.settings.value("nickname", "", str),
                # "sites" は現状未使用だが、将来的にサイトごとの設定に使える
                # "sites": self.settings.value("sites", [], list)
            }
            self.settings.endGroup()
        self.settings.endGroup()
        
        # その他の設定を読み込む
        settings_dict["selected_sites"] = self.settings.value("selected_sites", self.default_settings["selected_sites"], list)
        settings_dict["auto_login"] = self.settings.value("auto_login", self.default_settings["auto_login"], bool)
        settings_dict["remember_accounts"] = self.settings.value("remember_accounts", self.default_settings["remember_accounts"], bool)
        settings_dict["default_account"] = self.settings.value("default_account", self.default_settings["default_account"], str)
        settings_dict["api_key"] = self.settings.value("api_key", self.default_settings["api_key"], str)
        settings_dict["application_id"] = self.settings.value("application_id", self.default_settings["application_id"], str)
        settings_dict["affiliate_id"] = self.settings.value("affiliate_id", self.default_settings["affiliate_id"], str)
        
        return settings_dict
    
    def save_settings(self, settings_dict):
        """
        設定を保存する
        """
        # アカウント情報の保存 (個別メソッドに任せる)
        # self.save_all_accounts(settings_dict.get("accounts", {}))

        # その他の設定を保存
        if "selected_sites" in settings_dict:
            self.settings.setValue("selected_sites", settings_dict["selected_sites"])
        if "auto_login" in settings_dict:
            self.settings.setValue("auto_login", settings_dict["auto_login"])
        if "remember_accounts" in settings_dict:
            self.settings.setValue("remember_accounts", settings_dict["remember_accounts"])
        if "default_account" in settings_dict:
            self.settings.setValue("default_account", settings_dict["default_account"])
        if "api_key" in settings_dict:
            self.settings.setValue("api_key", settings_dict["api_key"])
        if "application_id" in settings_dict:
            self.settings.setValue("application_id", settings_dict["application_id"])
        if "affiliate_id" in settings_dict:
            self.settings.setValue("affiliate_id", settings_dict["affiliate_id"])
            
        # 確実に設定を保存
        self.settings.sync()
        

    def save_account(self, account_id, password, nickname=""):
        """
        アカウント情報を保存する
        """
        if not self.settings.value("remember_accounts", True, bool):
            print("アカウント記憶が無効のため保存しません。")
            return
            
        self.settings.beginGroup("accounts")
        self.settings.beginGroup(account_id)
        # パスワードはセキュリティを考慮し、別途暗号化/復号の仕組みを推奨
        self.settings.setValue("password", password)
        self.settings.setValue("nickname", nickname)
        self.settings.endGroup()
        self.settings.endGroup()
        self.settings.sync()
        print(f"アカウント '{account_id}' を保存しました。")
    
    def get_accounts(self):
        """
        保存されている全てのアカウント情報を取得
        """
        accounts = {}
        self.settings.beginGroup("accounts")
        account_ids = self.settings.childGroups()
        for account_id in account_ids:
            self.settings.beginGroup(account_id)
            accounts[account_id] = {
                "password": self.settings.value("password", "", str),
                "nickname": self.settings.value("nickname", "", str),
            }
            self.settings.endGroup()
        self.settings.endGroup()
        return accounts
    
    def delete_account(self, account_id):
        """
        アカウント情報を削除する
        """
        self.settings.beginGroup("accounts")
        if account_id in self.settings.childGroups():
            # グループごと削除するのが確実
            self.settings.remove(account_id)
            print(f"アカウント '{account_id}' を削除しました。")
        else:
            print(f"アカウント '{account_id}' は見つかりませんでした。")
        self.settings.endGroup()
        self.settings.sync()

        
        # デフォルトアカウントも更新
        current_default = self.settings.value("default_account", "")
        if current_default == account_id:
            self.settings.setValue("default_account", "")
            print("デフォルトアカウントをリセットしました。")
            self.settings.sync()

    def save_api_settings(self, api_key, application_id, affiliate_id=None, callback_domain=None):
        """APIキー情報を保管する"""
        # ここでも暗号化を検討
        self.settings.setValue("api_key", api_key)
        self.settings.setValue("application_id", application_id)
        if affiliate_id is not None: # Noneを保存しないように
            self.settings.setValue("affiliate_id", affiliate_id)
        if callback_domain:
            self.settings.setValue("callback_domain", callback_domain)
        else:
            self.settings.remove("affiliate_id") # Noneの場合は削除
        self.settings.sync()

    def get_api_settings(self):
        """APIキー情報を取得する"""
        return {
            "api_key": self.settings.value("api_key", "", str),
            "application_id": self.settings.value("application_id", "", str),
            "affiliate_id": self.settings.value("affiliate_id", "", str),
            "callback_domain": self.settings.value("callback_domain", "", str)
        }


# 設定ダイアログクラス
class SettingsDialog(QDialog):
    def __init__(self, app_settings: AppSettings, parent=None): # 型ヒントを追加
        super().__init__(parent)
        self.app_settings = app_settings
        # ダイアログを開くたびに最新の設定をロード
        self.settings_data = app_settings.load_settings()
        
        self.setWindowTitle("アプリケーション設定")
        self.setMinimumWidth(500)
        # self.setMinimumHeight(400) # 固定高さより可変の方が良い場合も
        
        self.init_ui()
    
    def init_ui(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self) # selfを親に設定
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # アカウント設定タブ
        account_tab = QWidget()
        account_layout = QVBoxLayout(account_tab) # 親ウィジェットを設定
        
        # 保存されたアカウント一覧
        accounts_group = QGroupBox("保存済みアカウント")
        accounts_layout = QVBoxLayout(accounts_group) # 親ウィジェットを設定
        
        self.accounts_list = QListWidget()
        self.accounts_list.setToolTip("保存されているアカウントの一覧です。")
        accounts_layout.addWidget(self.accounts_list)
        
        
        # アカウント操作ボタン
        account_buttons_layout = QHBoxLayout() # レイアウトを作成
        self.add_account_button = QPushButton("追加")
        self.add_account_button.setToolTip("新しいアカウント情報を追加します。")
        self.edit_account_button = QPushButton("編集")
        self.edit_account_button.setToolTip("選択中のアカウント情報を編集します。")
        self.delete_account_button = QPushButton("削除")
        self.delete_account_button.setToolTip("選択中のアカウント情報を削除します。")
        
        self.add_account_button.clicked.connect(self.add_account)
        self.edit_account_button.clicked.connect(self.edit_account)
        self.delete_account_button.clicked.connect(self.delete_account)
        # ダブルクリックで編集も便利
        self.accounts_list.itemDoubleClicked.connect(lambda item: self.edit_account())
        
        account_buttons_layout.addWidget(self.add_account_button)
        account_buttons_layout.addWidget(self.edit_account_button)
        account_buttons_layout.addWidget(self.delete_account_button)
        account_buttons_layout.addStretch() # ボタンを左に寄せる
        
        accounts_layout.addLayout(account_buttons_layout)
        account_layout.addWidget(accounts_group)
        
        
        # アカウント設定オプション
        account_options_group = QGroupBox("アカウントオプション")
        account_options_layout = QVBoxLayout(account_options_group) # 親設定
        
        # アカウント設定のチェックボックス
        self.remember_accounts_check = QCheckBox("アカウント情報を記憶する")
        self.remember_accounts_check.setToolTip("チェックを外すとアカウント情報は保存されません。")
        # QSettingsから直接読み込む方が確実な場合も
        self.remember_accounts_check.setChecked(self.app_settings.settings.value("remember_accounts", True, bool))

        self.auto_login_check = QCheckBox("起動時に自動ログイン (デフォルトアカウント使用)")
        self.auto_login_check.setToolTip("チェックすると、起動時にデフォルトアカウントで自動ログインを試みます。")
        self.auto_login_check.setChecked(self.app_settings.settings.value("auto_login", False, bool))

        
        # デフォルトアカウント表示/設定
        
        self.default_account_label = QLabel("デフォルト:")
        self.default_account_display = QLineEdit() # 表示用
        self.default_account_display.setReadOnly(True)
        self.set_default_button = QPushButton("選択をデフォルトに設定")
        self.set_default_button.setToolTip("リストで選択中のアカウントをデフォルトログインアカウントに設定します。")
        self.set_default_button.clicked.connect(self.set_default_account)
        # レイアウトに追加
        default_account_layout = QHBoxLayout() # 横並びに
        default_account_layout.addWidget(self.default_account_label)
        default_account_layout.addWidget(self.default_account_display, 1) # 幅を広げる
        default_account_layout.addWidget(self.set_default_button)
        
        self.default_account_display.setPlaceholderText("設定されていません")
        self.default_account_display.setText(self.app_settings.settings.value("default_account", ""))
        
        account_options_layout.addWidget(self.remember_accounts_check)
        account_options_layout.addWidget(self.auto_login_check)
        account_options_layout.addLayout(default_account_layout)

        # account_options_group.setLayout(account_options_layout) # 親設定済み
        account_layout.addWidget(account_options_group)
        account_layout.addStretch(1) # 上に詰める
        
        # account_tab.setLayout(account_layout) # 親設定済み
        self.tab_widget.addTab(account_tab, "アカウント")

        # --- ECサイト設定タブ ---
        site_tab = QWidget()
        site_layout = QVBoxLayout(site_tab) # 親設定

        sites_group = QGroupBox("デフォルトで選択するECサイト")
        sites_layout = QVBoxLayout(sites_group) # 親設定
        
        
        self.site_checkboxes = {}
        # このリストは main.py と共通化するのが望ましい
        ec_sites = ["楽天市場", "Amazon", "Yahoo!ショッピング", "auワウマ"]
        selected_sites = self.app_settings.settings.value("selected_sites", ["楽天市場"], list)
        
        for site in ec_sites:
            checkbox = QCheckBox(site)
            checkbox.setChecked(site in selected_sites)
            sites_layout.addWidget(checkbox)
            self.site_checkboxes[site] = checkbox
            
        # sites_group.setLayout(sites_layout) # 親設定済み
        site_layout.addWidget(sites_group)
        site_layout.addStretch(1) # 上に詰める
        
        # site_tab.setLayout(site_layout) # 親設定済み        
        # タブの追加
        self.tab_widget.addTab(site_tab, "ECサイト")
        
        # --- API設定タブ ---
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab) # 親設定
        
        # APIキー設定グループ
        api_group = QGroupBox("デフォルトで選択するECサイト")
        api_form = QFormLayout(api_group) # 親設定
        
        # APIキー入力フィールド
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("75a187b3488bc52af3feb8b58255baedbf969b2a") # アプリケーションシークレットを入力
        self.application_id_input = QLineEdit()
        self.application_id_input.setPlaceholderText("1010308332718919149") # アプリケーションID/開発者IDを入力
        self.affiliate_id_input = QLineEdit()
        self.affiliate_id_input.setPlaceholderText("4733ad8f.f64e0b53.4733ad90.5371467a") # アフィリエイトIDを入力
        
        # 設定から値をロード
        api_settings = self.app_settings.get_api_settings()
        self.api_key_input.setText(api_settings.get("api_key", ""))
        self.application_id_input.setText(api_settings.get("application_id", ""))
        self.affiliate_id_input.setText(api_settings.get("affiliate_id", ""))
        
        api_form.addRow("75a187b3488bc52af3feb8b58255baedbf969b2a:", self.api_key_input) # アプリケーションシークレット用
        api_form.addRow("1010308332718919149:", self.application_id_input) # アプリケーションID/開発者ID用
        api_form.addRow("4733ad8f.f64e0b53.4733ad90.5371467a:", self.affiliate_id_input) # アフィリエイトID用
        
                
        # コールバックドメイン入力フィールドを追加
        self.callback_domain_input = QLineEdit()
        self.callback_domain_input.setPlaceholderText("コールバックが許可されるドメイン")
        self.callback_domain_input.setText(api_settings.get("callback_domain", ""))
        
        # フォームに追加
        api_form.addRow("コールバックドメイン:", self.callback_domain_input)
        
        # アプリケーションID入力フィールド
        self.application_id_input = QLineEdit()
        self.application_id_input.setText(self.app_settings.get_api_settings().get("application_id", ""))
        api_form.addRow("アプリケーションID:", self.application_id_input)
        
        # アフィリエイトID入力フィールド（オプション）
        self.affiliate_id_input = QLineEdit()
        self.affiliate_id_input.setText(self.app_settings.get_api_settings().get("affiliate_id", ""))
        api_form.addRow("アフィリエイトID(任意):", self.affiliate_id_input)
        
        # api_group.setLayout(api_form) #親設定済み
        api_layout.addWidget(api_group)
        api_layout.addStretch(1)
        api_tab.setLayout(api_layout)

        self.tab_widget.addTab(api_tab, "API設定")
        
        main_layout.addWidget(self.tab_widget)
        
        # 保存 / キャンセルボタン
        buttons_layout = QHBoxLayout() # レイアウト作成
        save_button = QPushButton("保存")
        cancel_button = QPushButton("キャンセル")
        
        # `save_settings` を直接接続
        save_button.clicked.connect(self.save_settings_and_accept) # 保存してダイアログを閉じる
        cancel_button.clicked.connect(self.reject) # ダイアログを閉じる
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addStretch(1) # 右寄せにする
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
        # アカウントリストを更新（ボタン定義後に呼び出す）
        self.update_accounts_list()        
    
    def update_accounts_list(self):
        """アカウントリストを更新"""
        self.accounts_list.clear()
        # アカウント記憶が無効なら表示しない
        if not self.app_settings.settings.value("remember_accounts", True, bool):
            self.accounts_list.addItem(QListWidgetItem("アカウント記憶が無効です"))
            self.accounts_list.setEnabled(False)
            self.edit_account_button.setEnabled(False)
            self.delete_account_button.setEnabled(False)
            self.set_default_button.setEnabled(False)
            return
        else:
            self.accounts_list.setEnabled(True)
            self.edit_account_button.setEnabled(True)
            self.delete_account_button.setEnabled(True)
            self.set_default_button.setEnabled(True)
            
        accounts = self.app_settings.get_accounts()
        if not accounts:
            self.accounts_list.addItem(QListWidgetItem("保存されたアカウントはありません"))
            self.accounts_list.setEnabled(False) # アイテムがない場合も無効化
            self.edit_account_button.setEnabled(False)
            self.delete_account_button.setEnabled(False)
            self.set_default_button.setEnabled(False)
            
            
        for account_id, account_data in sorted(accounts.items()): # IDでソートして表示
            display_name = account_data.get("nickname") or account_id # ニックネーム優先
            if account_data.get("nickname"):
                display_name = f"{account_data['nickname']} ({account_id})"
                
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, account_id)  # アカウントIDをデータとして保持
            self.accounts_list.addItem(item)            
    
    def add_account(self):
        """新しいアカウントを追加するダイアログを開く"""
        dialog = AccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted: # exec() の戻り値で判定
            account_id = dialog.account_id_input.text()
            password = dialog.password_input.text()
            nickname = dialog.nickname_input.text()
            
            if account_id in self.app_settings.get_accounts():
                reply = QMessageBox.question(self, "確認",
                                            f"アカウント '{account_id}' は既に存在します。上書きしますか？",
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if repr == QMessageBox.StandardButton.No:
                    return
            
            # アカウント情報を保存
            self.app_settings.save_account(account_id, password, nickname)
            
            # リストを更新
            self.update_accounts_list()
            
    
    def edit_account(self):
        """選択されたアカウントを編集"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "編集するアカウントを選択してください。")
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        accounts = self.app_settings.get_accounts()
        
        if account_id in accounts:
            account_data = accounts[account_id]
            
            dialog = AccountDialog(self, account_id, account_data.get("password", ""), account_data.get("nickname", ""))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_password = dialog.password_input.text()
                new_nickname = dialog.nickname_input.text()
                
                # アカウント情報を更新
                self.app_settings.save_account(account_id, new_password, new_nickname)
                # リストを更新
                self.update_accounts_list()
            else:
                QMessageBox.critical(self, "エラー", f"アカウント '{account_id}' の情報が見つかりません。")
                self.update_accounts_list() # リストを再同期
    
    def delete_account(self):
        """選択されたアカウントを削除"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "削除するアカウントを選択してください。")
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, "確認", f"アカウント「{account_id}」を削除してもよろしいですか？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # アカウント情報を削除
            self.app_settings.delete_account(account_id)
            
            # デフォルトアカウントの更新
            if self.default_account_display.text() == account_id:
                self.default_account_display.setText("")
            
            # リストを更新
            self.update_accounts_list()
            
    
    def set_default_account(self):
        """選択されたアカウントをデフォルトに設定"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "デフォルトに設定するアカウントを選択してください。")
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self.default_account_display.setText(account_id)
        # この時点では QSettings には保存しない（保存ボタンで一括保存）
        
    
    def save_settings(self):
        """設定を保存してダイアログを閉じる"""
        # 選択されたサイトを取得
        selected_sites = []
        for site, checkbox in self.site_checkboxes.items():
            if checkbox.isChecked():
                selected_sites.append(site)
            
        # remember_accounts が False ならアカウント情報をクリアする (任意)
        remember = self.remember_accounts_check.isChecked()
        if not remember:
            reply = QMessageBox.question(self, "確認",
                                        "アカウント記憶を無効にすると、保存されている全てのアカウント情報が削除されます。よろしいですか？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                accounts = self.app_settings.get_accounts()
                for acc_id in list(accounts.keys()): # 削除中にイテレートしないようにコピー
                    self.app_settings.delete_account(acc_id)
                self.update_accounts_list() # リスト表示を更新
                self.default_account_display.clear() # デフォルト表示もクリア
            else:
                # 無効化をキャンセルする場合はチェックを探す
                self.remember_accounts_check.setChecked(True)
                remember = True # 保存処理のためにTrueに戻す
                
                
        # 設定を更新
        # settings_to_save = {
        #     "selected_sites": selected_sites,
        #     "auto_login": self.auto_login_check.isChecked(),
        #     "remember_accounts": remember,
        #     "default_account": self.default_account_display.text(),
        #     "api_key": self.api_key_input.text(),
        #     "application_id": self.application_id_input.text(),
        #     "affiliate_id": self.affiliate_id_input.text() or None # 空文字はNoneに
        # }
        
        # 設定を保存
        # self.app_settings.save_settings(settings_to_save)
        
        # API設定を保存
        self.app_settings.save_api_settings(
            self.api_key_input.text(),
            self.application_id_input.text(),
            self.affiliate_id_input.text() or None,
            self.callback_domain_input.text() or None
        )
        
        QMessageBox.information(self, "設定保存", "設定を保存しました")
    
    def save_settings_and_accept(self):
        """設定を保存してダイアログを閉じる"""
        self.save_settings()  # 設定を保存
        self.accept()  # ダイアログを閉じる


class AccountDialog(QDialog):
    """アカウント追加/編集ダイアログ"""
    def __init__(self, parent=None, account_id="", password="", nickname=""):
        super().__init__(parent)
        self.is_editing = bool(account_id) # 編集モードかどうか
        self.setWindowTitle("アカウント情報" + (" (編集)" if self.is_editing else " (新規追加)"))
        self.setMinimumWidth(350)
        
        # フォームレイアウト
        form_layout = QFormLayout()
        
        # アカウントID入力
        self.account_id_input = QLineEdit(account_id)
        form_layout.addRow("アカウントID:", self.account_id_input)
        
        # パスワード入力
        self.password_input = QLineEdit(password)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("パスワード:", self.password_input)
        
        # ニックネーム入力（オプション）
        self.nickname_input = QLineEdit(nickname)
        form_layout.addRow("ニックネーム(任意):", self.nickname_input)
        
        # ボタン
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1) # 右寄せ
        save_button = QPushButton("保存")
        cancel_button = QPushButton("キャンセル")
        
        save_button.clicked.connect(self.validate_and_accept)
        cancel_button.clicked.connect(self.reject)
        save_button.setDefault(True) # Enterキーで保存
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        
        # メインレイアウトに追加
        main_layout = QVBoxLayout(self) # selfを親に設定
        main_layout.addLayout(form_layout)
        main_layout.addLayout(buttons_layout)
        
        # self.setLayout(main_layout)
        
        # 編集モードの場合、IDを編集不可に
        if self.is_editing:
            self.account_id_input.setReadOnly(True)
            self.account_id_input.setStyleSheet("background-color: #f0f0f0;") # 見た目で区別
        
    
    def validate_and_accept(self):
        """入力内容を検証して保存"""
        account_id = self.account_id_input.text().strip() # 前後の空白を除去
        password = self.password_input.text() # パスワードは空白を許容する場合もある
        
        if not account_id:
            QMessageBox.warning(self, "入力エラー", "アカウントIDを入力してください。")
            self.account_id_input.setFocus() # フォーカスを戻す
            return
        
        if not password:
            QMessageBox.warning(self, "入力エラー", "パスワードを入力してください。")
            self.password_input.setFocus()
            return
        
        self.accept()

# このファイルが直接実行された場合のテスト用コード (任意)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # AppSettingsのインスタンスを作成
    app_settings = AppSettings()
    # 設定ダイアログを表示
    dialog = SettingsDialog(app_settings)
    dialog.show()
    sys.exit(app.exec())
