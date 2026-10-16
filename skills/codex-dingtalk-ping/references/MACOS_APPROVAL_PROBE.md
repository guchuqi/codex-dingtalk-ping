# macOS Codex 审批状态探针（实机验证版）

**状态：实验性诊断工具，不是钉钉通知功能。** 用于确认 macOS Codex 桌面 App 是否能通过辅助功能 API 稳定暴露实际可操作的审批按钮。尚未在真实 Codex App 上验收。

## 范围和原理

- 只检查 Bundle ID `com.openai.codex` 的窗口，通过 macOS Accessibility（AX）读取控件的 **Role、按钮标题、启用状态和屏幕位置**。
- 同一窗口发现相距较近的“同意/运行”与“拒绝/取消”**可点击按钮**时，视为一个候选审批；不依赖侧边栏的“待批准”文字状态。
- 检测到候选审批后计时；在连续可观测的情况下，5 秒后仍存在才输出 `approval_pending_5s`。已消失输出 `approval_cleared`。同一次持续出现只输出一次超时事件。
- **不会**自动批准/拒绝、点击按钮、截屏、读取聊天正文、访问网络、发送钉钉消息、安装 Hook、修改 Codex 配置或常驻后台。
- **局限：** 审批卡片可能不暴露为 AX Button / RadioButton；未显示的会话、最小化窗口或视图切换可能无法观察。无法观察时绝不声称已审批或已超时。按钮对识别是启发式，仍需用真实的任务审批流程验证误报和漏报。

## 准备

需 **macOS 13+**、Codex 桌面 App，以及可用的 Apple Swift 编译器（Xcode Command Line Tools）。无需额外 Python / 第三方库或服务。

在本地终端运行（从仓库根目录）：

```bash
sh skills/codex-dingtalk-ping/scripts/run-approval-probe.sh --self-test
sh skills/codex-dingtalk-ping/scripts/run-approval-probe.sh --watch
```

首次执行脚本会把编译后的验证程序放到 `~/.local/bin/codex-approval-probe`，之后源码没有更新则直接执行。同一个目录下的原版 `install.py` 和 `notify.py` **不会被调用或改变**。

如果输出 `accessibility_permission_required`：到 **macOS 系统设置 → 隐私与安全性 → 辅助功能**，允许承载程序的终端（Terminal / iTerm）或 macOS 提示的验证程序；然后重新运行。不同系统版本可能显示不同的负责进程。**不要尝试通过脚本绕过授权**。不需要屏幕录制权限。

## 推荐的实机测试顺序

1. **先在独立终端启动 `--watch`，让它持续运行**。不应从即将等待审批的同一 Codex 任务里启动，否则 Codex 自己可能被阻塞。
2. 在 macOS Codex 桌面 App 触发**真实的执行审批**。不要提前同意。输出应包含 `approval_detected`；等待约 5 秒后应出现 **一次** `approval_pending_5s`。
3. 点击批准或拒绝。若卡片真的消失，应出现 `approval_cleared`；继续等待不应出现第二次超时。
4. 再次触发审批，这次在 **5 秒内处理**：应有 `approval_detected` 与 `approval_cleared`，**不能**出现 `approval_pending_5s`。
5. 尝试 Codex 失去焦点、切换会话、最小化窗口。记录是否出现 `windows_not_accessible`、无法识别或丢失事件。失败直接报告，不据此启用自动钉钉提醒。
6. `Ctrl+C` 停止探针；不会留下守护进程、启动项或系统 Hook。

## 输出说明

默认一行一个 JSON 事件：

```json
{"event":"scanner_status","status":"ok","timestamp":"..."}
{"event":"approval_detected","approval_id":"123:window-0:row-2","timestamp":"..."}
{"event":"approval_pending_5s","approval_id":"123:window-0:row-2","elapsed_s":5.1,"timestamp":"..."}
{"event":"approval_cleared","approval_id":"123:window-0:row-2","elapsed_s":7.2,"timestamp":"..."}
```

- `codex_not_running`：未检测到 Codex 桌面 App。
- `accessibility_permission_required`：缺少 macOS AX 授权。
- `windows_not_accessible`：应用存在，但其窗口不可读；可能是应用最小化、AX 接口限制或暂时不可用。
- 真实等待状态仍存在但没有 `approval_detected`：用下面的调试命令确认按钮是否出现在 AX 树中。

```bash
sh skills/codex-dingtalk-ping/scripts/run-approval-probe.sh --inspect
```

`--inspect` 只输出可访问的**按钮标签**，不读取聊天消息或命令正文。但少数按钮标题可能包含敏感内容，分享日志前请自行检查并删去敏感信息。`--once` 只输出状态和当前发现的候选审批数量。调试参数：`--interval 0.5`、`--delay 5`（默认值）。

## 验收标准

同一台 Mac 的真实 Codex App 中，需至少通过 **未处理 5 秒通知一次、5 秒内处理不通知、审批后清除状态、后台可观察性** 四项，才值得将这个探针接入现有钉钉通知器。未通过前，**不得**对外宣称 Codex DingTalk Ping 已支持自动审批超时提醒。
