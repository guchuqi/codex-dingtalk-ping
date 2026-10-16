---
name: codex-dingtalk-ping
description: Install, configure, test, and troubleshoot automatic DingTalk robot messages after local Codex task turns finish. Use when a user asks to install Codex DingTalk Ping from GitHub, enable DingTalk task-completion notifications, configure a DingTalk group robot Webhook, or diagnose missing notifications. The notification is dispatched by a local Codex lifecycle trigger, not by asking the model to remember to send one.
---

# Codex DingTalk Ping

Send a short completion-of-turn message to a DingTalk custom **group** robot, using Codex's local `notify` event (or an optional trusted `Stop` hook). A Skill without a lifecycle trigger cannot send automatic completion alerts.

## Setup

1. If the skill is not installed, install this directory with Codex's built-in `$skill-installer` from `guchuqi/codex-dingtalk-ping`, path `skills/codex-dingtalk-ping`. For a repository URL alone, resolve the directory from the repository README; do **not** treat the root as the Skill.
2. Run `python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --no-prompt` on the user's local machine. This safely registers the `notify` command, unless an unrelated `notify` is already present. It does not demand credentials in an agent's noninteractive shell.
3. If credentials are missing, tell the user to run `python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --configure` in their own terminal. **Never request Webhook or signing secret in the chat**, and never print them. This command prompts privately and creates the local configuration file with restrictive permissions.
4. After configuration, only with the user's permission, run `python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/notify.py" --test` (this genuinely sends a message). `--dry-run` previews without sending or credentials.
5. Have the user start a **new local Codex session** and complete a turn; verify the robot receives a message. If test messages arrive but automatic ones do not, inspect the trigger and client support, not the Webhook.
6. If a local client does not fire `notify`, offer `install.py --method hook --no-prompt` as an alternative, requiring user trust via Codex `/hooks`. Use exactly one trigger to avoid duplicates. Do not overwrite an unrelated existing notification command.

See the repository [README](../../README.md) for complete human-facing instructions.

## Safety and event contract

- Support Codex `agent-turn-complete`, accepting a single JSON command argument. Optional trusted `Stop` hook sends JSON on stdin through `notify.py --hook`.
- Report project basename, conservative status, optional 180-character final-response excerpt, and local completion time. Never send full transcripts or source files. User prompts are **off by default**.
- Ending a turn does **not** prove successful completion; mark success or failure only when the final reply explicitly includes a status marker.
- Keep credentials exclusively in `${CODEX_HOME:-~/.codex}/codex-dingtalk-ping.json` (mode `0600`) or in the user's process environment. Never store secrets in this repository, Skill, `config.toml`, or messages.
- Avoid duplicate manual notifications when lifecycle triggering is installed. Notification failure must not alter the Codex task result.
- This integration supports `https://oapi.dingtalk.com/robot/send?access_token=...` for DingTalk **custom group robots**. Enterprise app robots and individual chat require a different API.
- Local CLI / desktop / supported IDE clients may trigger locally; **pure Codex Cloud tasks do not execute a user's local notifier**. Python 3.10+ standard library only.