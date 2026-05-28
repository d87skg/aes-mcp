import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as cp from 'child_process';
let statusBarItem;
let outputChannel;
export function activate(context) {
    outputChannel = vscode.window.createOutputChannel('AES Security');
    outputChannel.appendLine('AES Runtime Security activated');
    // 状态栏
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'aes.showStatus';
    statusBarItem.text = '$(shield) AES';
    statusBarItem.tooltip = 'AES Runtime Security';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // 命令：安装 AES
    context.subscriptions.push(vscode.commands.registerCommand('aes.install', async () => {
        const result = await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Installing AES-MCP...',
            cancellable: false
        }, async (progress) => {
            return new Promise((resolve) => {
                const child = cp.exec('pip install aes-mcp', (error, stdout, stderr) => {
                    if (error) {
                        resolve(`Installation failed: ${stderr}`);
                    }
                    else {
                        resolve(`AES-MCP installed successfully.`);
                    }
                });
            });
        });
        outputChannel.appendLine(result);
        vscode.window.showInformationMessage(result);
    }));
    // 命令：配置 Cursor/VS Code MCP
    context.subscriptions.push(vscode.commands.registerCommand('aes.configure', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }
        const mcpConfigPath = path.join(workspaceFolders[0].uri.fsPath, '.cursor', 'mcp.json');
        const mcpConfigDir = path.dirname(mcpConfigPath);
        if (!fs.existsSync(mcpConfigDir)) {
            fs.mkdirSync(mcpConfigDir, { recursive: true });
        }
        const mcpConfig = {
            mcpServers: {
                aes: {
                    command: 'python',
                    args: ['-m', 'aes_mcp.server']
                }
            }
        };
        fs.writeFileSync(mcpConfigPath, JSON.stringify(mcpConfig, null, 2));
        outputChannel.appendLine(`MCP config written to ${mcpConfigPath}`);
        vscode.window.showInformationMessage('AES MCP configured! Restart Cursor to activate. $(shield)');
    }));
    // 命令：显示状态
    context.subscriptions.push(vscode.commands.registerCommand('aes.showStatus', () => {
        vscode.window.showInformationMessage('AES Runtime Security v2.0.0 — Active $(shield)');
    }));
    // 命令：运行 Demo
    context.subscriptions.push(vscode.commands.registerCommand('aes.demo', async () => {
        const terminal = vscode.window.createTerminal('AES Demo');
        terminal.show();
        terminal.sendText('aes-mcp --demo episode_1');
    }));
    // 命令：打开 Trace Viewer
    context.subscriptions.push(vscode.commands.registerCommand('aes.traceViewer', async () => {
        const traceViewerPath = path.join(context.extensionPath, '..', '..', 'trace_viewer', 'index.html');
        if (fs.existsSync(traceViewerPath)) {
            vscode.env.openExternal(vscode.Uri.file(traceViewerPath));
        }
        else {
            vscode.window.showErrorMessage('Trace Viewer not found. Run pip install aes-mcp first.');
        }
    }));
    outputChannel.appendLine('AES Runtime Security ready');
}
export function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
    if (outputChannel) {
        outputChannel.dispose();
    }
}
