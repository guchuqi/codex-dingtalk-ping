# Codex DingTalk Ping

**Automatically send a DingTalk message when a local Codex task turn finishes.** A small, open-source Codex Skill and notification script powered by Python's standard library. / Codex 本地任务轮次结束后，自动通过钉钉群机器人发送通知。

> A Codex Skill alone does not create completion events. The included setup script also configures a local Codex `notify` trigger. **This does not run on purely remote Codex Cloud tasks.**

## Install by sending this GitHub link to Codex / 直接把链接发给 Codex

Send Codex this message (no ZIP download required):

```text
Install Codex DingTalk Ping from https://github.com/guchuqi/codex-dingtalk-ping
Use your skill-installer to install skills/codex-dingtalk-ping and run its local setup script with --no-prompt. Do not ask me to paste the DingTalk webhook or signing secret in chat. Explain how I can securely configure the webhook afterwards.
```

**中文：** 也可以只发这个仓库地址，并告诉 Codex「安装这个 Skill 并启用任务结束时的钉钉通知」。仓库结构和 [AGENTS.md](AGENTS.md) 均注明了准确的 Skill 目录，让 Codex 能够找到安装入口。是否允许本地执行操作，仍取决于你的 Codex 安全权限设置。

Codex's built-in `$skill-installer` can install the directory `skills/codex-dingtalk-ping` from this repository into `${CODEX_HOME:-~/.codex}/skills/codex-dingtalk-ping`.

After installation, Codex can run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --no-prompt
```

The command registers Codex's task-end notification trigger and safely preserves unrelated existing settings. **It intentionally does not ask for credentials from a noninteractive agent shell.**

## After installation: how to get DingTalk credentials / 安装后钉钉配置指引

**Codex must proactively show these steps immediately after installation** — installing the Skill is not the same as configuring a robot.

1. **确认机器人类型。** 本项目使用旧版 **钉钉群自定义机器人** Webhook；不支持企业内部应用机器人的 AppKey/AppSecret 或单聊 API。**钉钉已公告停止新增旧版自定义机器人，已有机器人不受该次调整影响。** 如果找不到新建入口，不能直接用企业机器人替代。请查阅[官方下线公告](https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice)。
2. **进入群机器人设置。** 在钉钉电脑端打开目标群 → **群设置 → 智能群助手 / 机器人** → 找到已有的**自定义机器人** → 设置或详情。入口会随客户端版本有所变化；旧版创建步骤可参考[钉钉官方自定义机器人文档](https://open.dingtalk.com/document/orgapp/custom-robot-access)。
3. **复制 Webhook。** 在机器人详情里复制完整的 `https://oapi.dingtalk.com/robot/send?access_token=...`，不要仅复制 `access_token`，不要分享给 Codex 聊天或提交到公开仓库。
4. **查看密钥与关键词。** 在**安全设置 → 加签**中复制以 `SEC...` 开头的**加签密钥**（仅开启加签时需要）；若启用了**自定义关键词**，记下其中一个已配置关键词（如 `Codex`）。`SEC...` 不是企业应用的 `AppSecret`。未启用相应安全项时留空。
5. **本地私密录入并测试。** 使用下一节的 `install.py --configure` 命令；然后运行 `notify.py --test`，在钉钉群确认收到消息，再开启新的本地 Codex 会话进行自动通知验证。

详细图文入口及注意事项：[**DingTalk 机器人配置完整指南**](skills/codex-dingtalk-ping/references/DINGTALK_SETUP.md)。钉钉[创建安装官方说明（历史教程）](https://open.dingtalk.com/document/orgapp/custom-bot-creation-and-installation)也可对照阅读。

## One-time private DingTalk setup / 首次配置 Webhook

**Run this yourself in a local terminal** (not in Codex chat):

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --configure
```

Enter your existing **DingTalk custom group robot Webhook**, optional `SEC...` signing secret, and optional security keyword. The Webhook and secret input do not echo to your terminal and are kept only in `${CODEX_HOME:-~/.codex}/codex-dingtalk-ping.json` with file permissions `0600`. If the config already exists, the script preserves it.

Restart Codex / open a new **local** session, then test (this sends a real message):

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/notify.py" --test
```

To preview the message without sending or providing credentials:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/notify.py" --dry-run
```

## What gets sent / 通知内容

```text
Codex 任务通知
项目：your-project
状态：本轮已结束（结果见摘要）
结果摘要：本轮回复的简短摘录
时间：2026-10-16 14:35
```

- Each supported end-of-turn event sends one message, **not** each tool call. It cannot infer that the task passed tests merely from the event. Explicit `状态：完成` / `状态：未完成` markers in Codex's final reply are recognized; otherwise status is neutral.
- By default it includes project folder name, status, reply excerpt (up to 180 characters), and local time. The original user prompt is **not sent** by default. It attempts to redact obvious URL/token patterns, but no redaction is perfect. For sensitive projects, set `"include_summary": false` in the private JSON settings.
- This package supports **DingTalk custom group robots** (`https://oapi.dingtalk.com/robot/send?access_token=...`), with optional keyword/signature. It does **not** target individual one-to-one chats or the different enterprise app robot APIs.
- macOS / Linux with Python 3.10+. Purely remote Codex Cloud tasks cannot use a notifier installed on your computer.

## Existing Codex configuration / 已有通知配置

The setup inserts a top-level `notify = [...]` into `${CODEX_HOME:-~/.codex}/config.toml` **only if none exists**. It backs up the previous file and preserves existing keys. If an unrelated `notify` command already exists, it **does not overwrite** that command: manually combine the notification handlers or choose a trigger after reviewing the original config.

For a local client that does not emit `notify` but supports trusted `Stop` hooks, use the alternative:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --method hook --no-prompt
```

Review/trust the new hook with `/hooks`, then restart Codex. Do **not** run both this project's `notify` and `Stop` hook for the same task, or duplicate messages may occur.

The installer never commits credentials into this repository. Do not store them in Git, Codex chat, or a project file.

## Experimental macOS Desktop approval probe / macOS 审批检测实机验证

针对 **Codex 桌面 App（macOS）**，新增一个**只读辅助功能检测探针**，用于验证“审批出现 → 5 秒仍未操作 → 审批按钮消失”这三个信号。此工具**不发送钉钉、不自动安装、不修改 Codex 设置**，尚须在真实 Codex App 上验证是否能观察后台/未选中会话的审批卡片。

先在独立的 macOS 终端运行（需 Apple Xcode Command Line Tools）：

```bash
sh skills/codex-dingtalk-ping/scripts/run-approval-probe.sh --self-test
sh skills/codex-dingtalk-ping/scripts/run-approval-probe.sh --watch
```

首次运行编译为 `~/.local/bin/codex-approval-probe`。macOS 可能需要你在 **系统设置 → 隐私与安全性 → 辅助功能** 中手动授权终端或探针。然后在 **另一个 Codex App 会话**触发真实审批，保留 5 秒再点击批准/拒绝，观察终端中 `approval_detected`、`approval_pending_5s`、`approval_cleared` 事件。5 秒内处理时不应出现超时事件。按 `Ctrl+C` 停止，不会留下常驻程序。

详细验收步骤、调试命令和已知局限：[**macOS 审批探针实机测试说明**](skills/codex-dingtalk-ping/references/MACOS_APPROVAL_PROBE.md)。这不是已经完成的审批通知功能，请勿混同现有“任务轮次结束通知”。

## Tests / 开发测试

```bash
python3 -m unittest discover -s tests -v
```

Source: [`skills/codex-dingtalk-ping`](skills/codex-dingtalk-ping) · License: [MIT](LICENSE)