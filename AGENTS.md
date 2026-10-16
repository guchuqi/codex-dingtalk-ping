# Installing this repository's Codex Skill

This is a public Codex Skill source repository. When the user shares https://github.com/guchuqi/codex-dingtalk-ping and asks to install:

1. Read `README.md`, `skills/codex-dingtalk-ping/SKILL.md` and `skills/codex-dingtalk-ping/references/DINGTALK_SETUP.md`.
2. Use Codex's built-in `$skill-installer` to install the path `skills/codex-dingtalk-ping` from repository `guchuqi/codex-dingtalk-ping` into `${CODEX_HOME:-~/.codex}/skills/codex-dingtalk-ping`. Do not install the repository root as a Skill.
3. Run `python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --no-prompt` on the user's local machine to register the local notification trigger. Do not overwrite an unrelated existing `notify` command.
4. If credentials are missing, explain that the user must run `install.py --configure` in their own private terminal. Never solicit a Webhook or signing secret in chat.
5. **Mandatory final user guidance after every installation:** explain in the user's language how to find the existing DingTalk custom group robot from the target group's settings, copy its complete Webhook, and find its optional `SEC...` signing secret or configured keyword under security settings. Include official https://open.dingtalk.com/document/orgapp/custom-robot-access and retirement notice https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice. State that new legacy custom bots are no longer generally available and enterprise app robots are not supported by this Skill. Do not just say "read the docs".
6. Include the full private-terminal `install.py --configure` and real-send `notify.py --test` commands, plus instructions to restart local Codex. Distinguish installed vs credentials configured vs successfully tested; never claim to have sent a message without a successful real send.

Skill installation, local trigger setup, and DingTalk credential setup are separate stages. Pure Codex Cloud tasks cannot execute this user's local notifier.

For Mac approval-alert prototyping only: follow `skills/codex-dingtalk-ping/references/MACOS_APPROVAL_PROBE.md`. Run the read-only probe from an independent Terminal before creating a real Codex approval. Do not claim this experimental probe sends DingTalk messages, and never enable it as a launch agent during testing.