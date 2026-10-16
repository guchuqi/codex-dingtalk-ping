# Installing this repository's Codex Skill

This is a public Codex Skill source repository. When the user shares https://github.com/guchuqi/codex-dingtalk-ping and asks to install:

1. Read README.md and skills/codex-dingtalk-ping/SKILL.md.
2. Use Codex's built-in $skill-installer to install the path skills/codex-dingtalk-ping from repository guchuqi/codex-dingtalk-ping into ${CODEX_HOME:-~/.codex}/skills/codex-dingtalk-ping. Do not install the repository root as a Skill.
3. Run python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --no-prompt on the user's local machine to register the local notification trigger. Do not overwrite an unrelated existing notify command.
4. If credentials are missing, explain that the user must run install.py --configure in their own private terminal. Never solicit a Webhook or signing secret in chat.
5. Explain how to test with scripts/notify.py --test and open a new local Codex session.

Skill installation, local trigger setup, and DingTalk credential setup are separate stages. Do not claim automatic messages are functioning until configured and tested. Pure Codex Cloud tasks cannot execute this user's local notifier.
