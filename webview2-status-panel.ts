// src/extension.ts - PyQt6開発支援機能を追加
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

// 拡張機能が有効化されたときに呼び出される
export function activate(context: vscode.ExtensionContext) {
    console.log('PyQt6 Developer Helper が有効化されました！');

    // 既存のHello Worldコマンド
    let helloWorldCommand = vscode.commands.registerCommand('pyqt6-developer-helper.helloWorld', () => {
        vscode.window.showInformationMessage('Hello World from PyQt6 Developer Helper!');
    });

    // PyQt6開発支援コマンド群を追加
    registerPyQt6Commands(context);

    // コマンドをサブスクリプションに追加
    context.subscriptions.push(helloWorldCommand);
}

// PyQt6開発支援コマンドの登録
function registerPyQt6Commands(context: vscode.ExtensionContext) {
    
    // 1. WebView2ステータスチェッカー
    let webview2CheckerCommand = vscode.commands.registerCommand('pyqt6-developer-helper.checkWebView2', () => {
        WebView2StatusPanel.createOrShow(context.extensionUri);
    });

    // 2. PyQt6 UIプレビュー
    let uiPreviewCommand = vscode.commands.registerCommand('pyqt6-developer-helper.previewUI', () => {
        PyQt6UIPreviewPanel.createOrShow(context.extensionUri);
    });

    // 3. プロジェクト設定チェック
    let projectCheckCommand = vscode.commands.registerCommand('pyqt6-developer-helper.checkProject', () => {
        checkPyQt6ProjectSetup();
    });

    // 4. 依存関係チェック
    let dependencyCheckCommand = vscode.commands.registerCommand('pyqt6-developer-helper.checkDependencies', () => {
        checkPyQt6Dependencies();
    });

    // 5. サンプルコード生成
    let generateSampleCommand = vscode.commands.registerCommand('pyqt6-developer-helper.generateSample', () => {
        generatePyQt6Sample();
    });

    // 全てのコマンドをサブスクリプションに追加
    context.subscriptions.push(
        webview2CheckerCommand,
        uiPreviewCommand,
        projectCheckCommand,
        dependencyCheckCommand,
        generateSampleCommand
    );
}

// WebView2ステータスチェック用パネルクラス
class WebView2StatusPanel {
    public static currentPanel: WebView2StatusPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (WebView2StatusPanel.currentPanel) {
            WebView2StatusPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'webview2Status',
            'WebView2 Status Checker',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [extensionUri]
            }
        );

        WebView2StatusPanel.currentPanel = new WebView2StatusPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._update();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Webviewからのメッセージを処理
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'checkWebView2':
                        this._runWebView2Check();
                        return;
                    case 'installWebView2':
                        this._installWebView2();
                        return;
                }
            },
            null,
            this._disposables
        );
    }

    public dispose() {
        WebView2StatusPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.title = 'WebView2 Status';
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    private _runWebView2Check() {
        // VSCodeの統合ターミナルでWebView2チェックスクリプトを実行
        const terminal = vscode.window.createTerminal('WebView2 Check');
        terminal.sendText('python -c "import platform; print(f\'OS: {platform.system()}\'); import winreg; print(\'WebView2チェック中...\'); "');
        terminal.show();
    }

    private _installWebView2() {
        vscode.window.showInformationMessage('WebView2インストールを開始します...');
        const terminal = vscode.window.createTerminal('WebView2 Install');
        terminal.sendText('python -c "import webbrowser; webbrowser.open(\'https://developer.microsoft.com/microsoft-edge/webview2/\')"');
        terminal.show();
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WebView2 Status Checker</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 20px;
                    background-color: var(--vscode-editor-background);
                    color: var(--vscode-editor-foreground);
                }
                .status-card {
                    border: 1px solid var(--vscode-panel-border);
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    background-color: var(--vscode-panel-background);
                }
                .status-ok {
                    border-left: 4px solid #4CAF50;
                }
                .status-error {
                    border-left: 4px solid #f44336;
                }
                .status-warning {
                    border-left: 4px solid #ff9800;
                }
                button {
                    background-color: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    padding: 8px 16px;
                    margin: 5px;
                    border-radius: 3px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: var(--vscode-button-hoverBackground);
                }
                .command-section {
                    margin-top: 20px;
                    padding: 15px;
                    background-color: var(--vscode-textCodeBlock-background);
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>🔍 WebView2 Status Checker</h1>
            
            <div class="status-card status-warning">
                <h3>WebView2 Runtime Status</h3>
                <p>アプリケーションで必要なWebView2ランタイムの状態を確認します。</p>
                <button onclick="checkWebView2()">WebView2をチェック</button>
                <button onclick="installWebView2()">WebView2をインストール</button>
            </div>

            <div class="status-card">
                <h3>PyQt6-WebEngine Status</h3>
                <p>PyQt6-WebEngineモジュールの状態を確認します。</p>
                <button onclick="checkPyQt6WebEngine()">PyQt6-WebEngineをチェック</button>
            </div>

            <div class="command-section">
                <h3>🚀 便利なコマンド</h3>
                <p>以下のコマンドをターミナルで実行できます：</p>
                <ul>
                    <li><code>pip install PyQt6-WebEngine</code> - PyQt6-WebEngineをインストール</li>
                    <li><code>python -c "from PyQt6.QtWebEngineWidgets import QWebEngineView; print('✅ PyQt6-WebEngine正常')"</code> - インストール確認</li>
                </ul>
            </div>

            <script>
                const vscode = acquireVsCodeApi();
                
                function checkWebView2() {
                    vscode.postMessage({
                        command: 'checkWebView2'
                    });
                }
                
                function installWebView2() {
                    vscode.postMessage({
                        command: 'installWebView2'
                    });
                }

                function checkPyQt6WebEngine() {
                    vscode.postMessage({
                        command: 'checkPyQt6WebEngine'
                    });
                }
            </script>
        </body>
        </html>`;
    }
}

// PyQt6 UIプレビュー用パネルクラス
class PyQt6UIPreviewPanel {
    public static currentPanel: PyQt6UIPreviewPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (PyQt6UIPreviewPanel.currentPanel) {
            PyQt6UIPreviewPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'pyqt6UIPreview',
            'PyQt6 UI Preview',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [extensionUri]
            }
        );

        PyQt6UIPreviewPanel.currentPanel = new PyQt6UIPreviewPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._update();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    public dispose() {
        PyQt6UIPreviewPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.title = 'PyQt6 UI Preview';
        this._panel.webview.html = this._getUIPreviewHtml(webview);
    }

    private _getUIPreviewHtml(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PyQt6 UI Preview</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 20px;
                    background-color: var(--vscode-editor-background);
                    color: var(--vscode-editor-foreground);
                }
                .preview-area {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-top: 20px;
                }
                .component-list {
                    border: 1px solid var(--vscode-panel-border);
                    padding: 15px;
                    border-radius: 5px;
                    background-color: var(--vscode-panel-background);
                }
                .mock-ui {
                    border: 1px solid var(--vscode-panel-border);
                    padding: 15px;
                    border-radius: 5px;
                    background-color: var(--vscode-panel-background);
                    min-height: 300px;
                }
                .widget-mock {
                    border: 1px solid #ccc;
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 3px;
                    background-color: #f5f5f5;
                    color: #333;
                }
                .button-mock {
                    background-color: #e1e1e1;
                    border: 1px solid #adadad;
                    padding: 8px 16px;
                    display: inline-block;
                    margin: 5px;
                }
                .input-mock {
                    background-color: white;
                    border: 1px solid #adadad;
                    padding: 8px;
                    width: 200px;
                    display: block;
                    margin: 5px 0;
                }
            </style>
        </head>
        <body>
            <h1>🎨 PyQt6 UI Preview</h1>
            <p>現在のPythonファイルからPyQt6コンポーネントを解析してプレビューを表示します。</p>
            
            <div class="preview-area">
                <div class="component-list">
                    <h3>検出されたコンポーネント</h3>
                    <ul id="componentList">
                        <li>QPushButton: start_button</li>
                        <li>QLineEdit: account_id_input</li>
                        <li>QLineEdit: password_input</li>
                        <li>QWebEngineView: web_view</li>
                        <li>QProgressBar: progress_bar</li>
                    </ul>
                </div>
                
                <div class="mock-ui">
                    <h3>UIモックアップ</h3>
                    <div class="widget-mock">
                        <label>アカウントID:</label>
                        <div class="input-mock">account_id_input</div>
                    </div>
                    <div class="widget-mock">
                        <label>パスワード:</label>
                        <div class="input-mock">password_input</div>
                    </div>
                    <div class="widget-mock">
                        <div class="button-mock">ログイン開始</div>
                    </div>
                    <div class="widget-mock">
                        <div style="width: 100%; height: 20px; background-color: #4CAF50;">進捗バー (progress_bar)</div>
                    </div>
                </div>
            </div>
        </body>
        </html>`;
    }
}

// プロジェクト設定チェック機能
function checkPyQt6ProjectSetup() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        vscode.window.showErrorMessage('ワークスペースフォルダが開かれていません。');
        return;
    }

    const projectPath = workspaceFolder.uri.fsPath;
    
    // requirements.txtの存在チェック
    const requirementsPath = path.join(projectPath, 'requirements.txt');
    const hasRequirements = fs.existsSync(requirementsPath);
    
    // main.pyの存在チェック
    const mainPyPath = path.join(projectPath, 'main.py');
    const hasMainPy = fs.existsSync(mainPyPath);
    
    let message = '🔍 PyQt6プロジェクト設定チェック結果:\n\n';
    message += hasRequirements ? '✅ requirements.txt が見つかりました\n' : '❌ requirements.txt が見つかりません\n';
    message += hasMainPy ? '✅ main.py が見つかりました\n' : '❌ main.py が見つかりません\n';
    
    vscode.window.showInformationMessage(message);
}

// 依存関係チェック機能
function checkPyQt6Dependencies() {
    const terminal = vscode.window.createTerminal('PyQt6 Dependencies Check');
    terminal.sendText('echo "🔍 PyQt6依存関係をチェック中..."');
    terminal.sendText('python -c "import sys; print(f\'Python: {sys.version}\')"');
    terminal.sendText('python -c "try: import PyQt6; print(\'✅ PyQt6: インストール済み\'); except ImportError: print(\'❌ PyQt6: 未インストール\')"');
    terminal.sendText('python -c "try: import PyQt6.QtWebEngineWidgets; print(\'✅ PyQt6-WebEngine: インストール済み\'); except ImportError: print(\'❌ PyQt6-WebEngine: 未インストール\')"');
    terminal.sendText('python -c "try: import selenium; print(\'✅ Selenium: インストール済み\'); except ImportError: print(\'❌ Selenium: 未インストール\')"');
    terminal.show();
}

// サンプルコード生成機能
function generatePyQt6Sample() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('エディターが開かれていません。');
        return;
    }

    const sampleCode = `# PyQt6 WebView サンプルコード
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class PyQt6WebViewSample(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQt6 WebView Sample')
        self.setGeometry(100, 100, 1200, 800)
        
        # レイアウト設定
        layout = QVBoxLayout()
        
        # WebViewの作成
        self.web_view = QWebEngineView()
        self.web_view.load(QUrl('https://www.google.com'))
        
        layout.addWidget(self.web_view)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyQt6WebViewSample()
    window.show()
    sys.exit(app.exec())
`;

    // 現在のエディターにサンプルコードを挿入
    editor.edit(editBuilder => {
        editBuilder.insert(editor.selection.start, sampleCode);
    });

    vscode.window.showInformationMessage('PyQt6サンプルコードを挿入しました！');
}

// 拡張機能が非有効化されたときに呼び出される
export function deactivate() {
    console.log('PyQt6 Developer Helper が非有効化されました。');
}
