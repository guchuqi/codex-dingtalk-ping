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

## After installation: configure your DingTalk robot / 安装后配置指引

**Codex must proactively explain these steps after installation.** This Skill supports existing legacy custom **group** robots, not enterprise application robots. DingTalk has announced that new legacy custom robots are no longer available; see the [official notice](https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice).

1. 在钉钉电脑端打开接收通知的群 → **群设置 → 智能群助手 / 机器人** → 找到已有的**自定义机器人** → 机器人设置 / 详情。
2. 在机器人详情中复制完整 **Webhook**，格式为 `https://oapi.dingtalk.com/robot/send?access_token=...`。这是私密信息，不能发到 Codex 聊天或公开仓库。
3. 在同一个机器人的 **安全设置 → 加签** 中，复制 `SEC...` **密钥**（只有开启加签时才需要）；如果启用了**自定义关键词**，记下其中一个已经设置的关键词。不要把企业应用的 AppSecret 当作加签密钥。
4. 在自己的私密本地终端运行下一节的 `install.py --configure`，然后执行 `notify.py --test`。确认群内收到消息后，重新开启本地 Codex 会话验证自动通知。

官方参考：[自定义机器人说明](https://open.dingtalk.com/document/orgapp/custom-robot-access) · [旧版机器人下线公告](https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice)。

完整操作流程见 [DINGTALK_SETUP.md](skills/codex-dingtalk-ping/references/DINGTALK_SETUP.md)。

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

## Tests / 开发测试

```bash
python3 -m unittest discover -s tests -v
```

Source: [`skills/codex-dingtalk-ping`](skills/codex-dingtalk-ping) · License: [MIT](LICENSE)