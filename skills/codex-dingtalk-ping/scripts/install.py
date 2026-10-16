#!/usr/bin/env python3
"""Install the Codex Skill plus a real, automatic end-of-turn trigger.

Does not overwrite existing notification commands or unrelated hooks.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

from notify import validate_webhook, NotificationError

SKILL_NAME = "codex-dingtalk-ping"


def root_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser()


def install_dir() -> Path:
    return root_dir() / "skills" / SKILL_NAME


def backup_file(path: Path) -> None:
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = path.with_name(path.name + ".bak-" + stamp)
        count = 1
        while destination.exists():
            destination = path.with_name(path.name + ".bak-" + stamp + f"-{count}")
            count += 1
        shutil.copy2(path, destination)
        print(f"已备份原配置：{destination}")


def save_private_config(path: Path) -> None:
    if path.exists():
        if not path.is_file() or path.is_symlink():
            raise NotificationError("现有钉钉配置路径不是普通文件")
        os.chmod(path, 0o600)
        print(f"已存在钉钉配置，保持内容并设为私有权限：{path}")
        return
    if not sys.stdin.isatty():
        raise NotificationError("首次安装需要交互式终端录入 Webhook（或自行创建私有配置）")
    print("配置钉钉自定义群机器人。Webhook 和加签密钥不会写入 Skill 或 Codex config.toml。")
    webhook = getpass.getpass("粘贴已验证的钉钉 Webhook（输入时不显示）：").strip()
    validate_webhook(webhook)
    secret = getpass.getpass("加签密钥 SEC...（未开启加签请直接回车）：").strip()
    keyword = input("机器人安全关键词（未启用关键词校验请直接回车）：").strip()
    payload = {
        "webhook": webhook,
        "secret": secret,
        "keyword": keyword,
        "include_prompt": False,
        "include_summary": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use O_EXCL to avoid replacing credentials, and 0600 to limit access.
    file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"已保存私有配置（仅当前用户可读写）：{path}")


def top_level_notify_line(text: str) -> str | None:
    section = False
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if trimmed.startswith("["):
            section = True
        if not section and re.match(r"^notify\s*=", trimmed):
            return line
    return None


def remove_own_notify(content: str, script: Path) -> str:
    """Remove a previously installed single-line notify; preserve everything else."""
    line = top_level_notify_line(content)
    if line and str(script) in line:
        return content.replace(line + "\n", "", 1)
    return content


def configure_notify(config_file: Path, script: Path, python_bin: str) -> str:
    original = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    previous = top_level_notify_line(original)
    if previous:
        if str(script) in previous:
            return "Codex notify 已配置，无需重复写入"
        return "发现已有 notify 配置。为了不覆盖你的现有通知程序，自动注册已跳过（见 README 中的合并方式）。"
    new_line = "notify = " + json.dumps([python_bin, str(script)], ensure_ascii=False) + "\n\n"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file(config_file)
    config_file.write_text(new_line + original, encoding="utf-8")
    return "已启用 Codex notify 自动触发"


def configure_stop_hook(hooks_file: Path, script: Path, python_bin: str) -> str:
    """Alternative for local clients that don't emit notify, requiring /hooks trust."""
    if hooks_file.exists():
        try:
            data = json.loads(hooks_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise NotificationError("已有 hooks.json 解析失败；为了安全不覆盖") from exc
    else:
        data = {}
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise NotificationError("已有 hooks.json 不是受支持的对象结构；未覆盖")
    hooks = data.setdefault("hooks", {})
    stops = hooks.setdefault("Stop", [])
    if not isinstance(stops, list):
        raise NotificationError("已有 Stop hooks 结构不正确；未覆盖")
    command = f'{json.dumps(python_bin, ensure_ascii=False)} {json.dumps(str(script), ensure_ascii=False)} --hook'
    for group in stops:
        if not isinstance(group, dict):
            continue
        for handler in group.get("hooks", []):
            if isinstance(handler, dict) and handler.get("command") == command:
                return "Stop Hook 已配置，无需重复写入；在 Codex 内检查 /hooks 信任状态"
    stops.append({"hooks": [{"type": "command", "command": command, "timeout": 15}]})
    backup_file(hooks_file)
    hooks_file.parent.mkdir(parents=True, exist_ok=True)
    hooks_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return "已写入 Stop Hook；必须在 Codex 通过 /hooks 审阅并信任才能触发"


def remove_own_stop_hook(hooks_file: Path, script: Path) -> bool:
    """Undo only this skill's Stop handlers when switching back to notify."""
    if not hooks_file.exists():
        return False
    try:
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NotificationError("hooks.json 无法读取；请手动核对是否会重复通知") from exc
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise NotificationError("hooks.json 结构异常；请手动核对是否会重复通知")
    hooks = data["hooks"]
    old_groups = hooks.get("Stop", [])
    if not isinstance(old_groups, list):
        raise NotificationError("Stop Hook 结构异常；请手动核对是否会重复通知")
    new_groups = []
    removed = False
    for group in old_groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            new_groups.append(group)
            continue
        keep = [handler for handler in group["hooks"] if not (
            isinstance(handler, dict)
            and str(script) in str(handler.get("command", ""))
            and "--hook" in str(handler.get("command", ""))
        )]
        if len(keep) != len(group["hooks"]):
            removed = True
            if keep:
                new_groups.append({**group, "hooks": keep})
        else:
            new_groups.append(group)
    if removed:
        if new_groups:
            hooks["Stop"] = new_groups
        else:
            hooks.pop("Stop", None)
        backup_file(hooks_file)
        hooks_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="安装和配置 Codex DingTalk Ping")
    parser.add_argument("--method", choices=("notify", "hook"), default="notify",
                        help="默认 notify；hook 是兼容性备选，须在 Codex 手动信任")
    parser.add_argument("--no-prompt", action="store_true", help="安装触发器，但不交互录入私密 Webhook")
    parser.add_argument("--configure", action="store_true", help="在用户自己的终端私密录入 Webhook")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent.parent
    dest = install_dir()
    codex = root_dir()
    script = dest / "scripts" / "notify.py"
    try:
        if source != dest:
            if dest.exists():
                if not (dest / "SKILL.md").is_file():
                    raise NotificationError(f"目标位置已存在但不是 Skill：{dest}")
                print(f"Skill 已存在，不覆盖文件：{dest}")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                print(f"Skill 已安装：{dest}")
        else:
            print(f"Skill 已安装：{dest}")
        private_config = codex / "codex-dingtalk-ping.json"
        if private_config.exists():
            # Validate shape without ever echoing credentials.
            if not private_config.is_file() or private_config.is_symlink():
                raise NotificationError("私密配置路径不可用或是符号链接")
            os.chmod(private_config, 0o600)
            print("钉钉私密配置已存在，未覆盖")
        elif args.configure or (sys.stdin.isatty() and not args.no_prompt):
            save_private_config(private_config)
        else:
            print("钉钉 Webhook 尚未配置。请在本地终端使用 --configure 私密录入；勿粘贴到 Codex 聊天。")

        if args.method == "notify":
            result = configure_notify(codex / "config.toml", script, sys.executable)
            if "已有 notify" not in result and remove_own_stop_hook(codex / "hooks.json", script):
                print("已停用本 Skill 的旧 Stop Hook，避免重复通知")
        else:
            current_config = codex / "config.toml"
            if current_config.exists():
                original = current_config.read_text(encoding="utf-8")
                previous = top_level_notify_line(original)
                if previous and str(script) not in previous:
                    print("提醒：已有其他 notify 命令，可能存在重复提醒。")
                if previous and str(script) in previous:
                    backup_file(current_config)
                    current_config.write_text(remove_own_notify(original, script), encoding="utf-8")
                    print("已停用本 Skill 旧 notify，避免重复通知")
            result = configure_stop_hook(codex / "hooks.json", script, sys.executable)
        print(result)
        print(f"私密配置命令：{sys.executable} {script.parent / 'install.py'} --configure")
        print(f"测试发送命令：{sys.executable} {script} --test")
        print("重新开启一个 Codex 本地会话后，测试自动通知是否触发。纯 Codex Cloud 不支持本地触发。")
        return 0
    except (NotificationError, OSError, ValueError) as exc:
        print("安装未完全启用：" + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())