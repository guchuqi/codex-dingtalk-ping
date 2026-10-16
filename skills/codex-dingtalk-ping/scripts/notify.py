#!/usr/bin/env python3
"""Send Codex completion events to a DingTalk custom group robot.

Python 3.10+; standard library only. No credentials live in the skill folder.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import error, parse, request


class NotificationError(Exception):
    """A safe-to-display notification failure."""


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser()


def config_path() -> Path:
    return codex_home() / "codex-dingtalk-ping.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    file_path = path or config_path()
    settings: dict[str, Any] = {}
    if file_path.exists():
        try:
            parsed = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise NotificationError("通知配置文件无法读取或不是有效 JSON") from exc
        if not isinstance(parsed, dict):
            raise NotificationError("通知配置文件根节点必须是 JSON 对象")
        settings = parsed
    # Useful for CI or a one-off test. For Desktop, the private JSON file is preferred.
    if os.environ.get("DINGTALK_WEBHOOK"):
        settings["webhook"] = os.environ["DINGTALK_WEBHOOK"]
    if os.environ.get("DINGTALK_SECRET"):
        settings["secret"] = os.environ["DINGTALK_SECRET"]
    if os.environ.get("DINGTALK_KEYWORD"):
        settings["keyword"] = os.environ["DINGTALK_KEYWORD"]
    if not settings.get("webhook"):
        raise NotificationError("未配置钉钉 Webhook；请先运行 scripts/install.py")
    validate_webhook(str(settings["webhook"]))
    return settings


def validate_webhook(webhook: str) -> None:
    parts = parse.urlsplit(webhook)
    # The supported integration is the permanent custom group robot webhook.
    if (
        parts.scheme.lower() != "https"
        or (parts.hostname or "").lower() != "oapi.dingtalk.com"
        or parts.port not in (None, 443)
        or parts.path != "/robot/send"
        or not parse.parse_qs(parts.query).get("access_token")
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise NotificationError("Webhook 格式无效：需要 https://oapi.dingtalk.com/robot/send?access_token=...")


def sign_webhook(webhook: str, secret: str, now_ms: int | None = None) -> str:
    """Optionally apply DingTalk HMAC-SHA256 signing security."""
    validate_webhook(webhook)
    if not secret:
        return webhook
    timestamp = str(now_ms if now_ms is not None else int(time.time() * 1000))
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}\n{secret}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(digest).decode("ascii")
    parts = parse.urlsplit(webhook)
    params = [(k, v) for k, v in parse.parse_qsl(parts.query, keep_blank_values=True)
              if k not in ("timestamp", "sign")]
    params.extend((("timestamp", timestamp), ("sign", signature)))
    return parse.urlunsplit((parts.scheme, parts.netloc, parts.path,
                             parse.urlencode(params), ""))


def short_safe(text: str, max_length: int) -> str:
    """Send only a short, lightly redacted excerpt, never a full transcript."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"```[\s\S]*?```", "[代码省略]", text)
    text = re.sub(r"https?://[^\s<>)\]]+", "[链接省略]", text)
    text = re.sub(r"(?i)\b(?:sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9_]{10,})\b", "[凭据省略]", text)
    text = re.sub(r"(?i)\b(access[_-]?token|api[_-]?key|password|secret|token|webhook|密钥)\s*[:=：]\s*\S+", r"\1=[隐藏]", text)
    text = " ".join(text.split())
    return (text[:max_length] + "…") if len(text) > max_length else text


def status_from_message(message: str) -> str:
    """Avoid claiming success unless Codex explicitly declares its status."""
    explicit = re.search(r"(?im)^\s*(?:\*\*)?(?:状态|status)(?:\*\*)?\s*[:：]\s*(已完成|未完成|完成|成功|失败|阻塞|success|done|failed|blocked)(?=\s|$|[.,，。；;*])", message)
    if not explicit:
        return "本轮已结束（结果见摘要）"
    state = explicit.group(1).lower()
    if state in ("完成", "成功", "已完成", "success", "done"):
        return "已完成"
    return "未完成／需关注"


def normalize_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Support Codex notify argv and the optional Stop hook stdin format."""
    kind = raw.get("type")
    if kind == "agent-turn-complete":
        return raw
    if raw.get("hook_event_name") == "Stop":
        # A stop hook may observe a resumed turn; both are a completed turn.
        return {
            "type": "agent-turn-complete",
            "thread-id": raw.get("session_id", ""),
            "turn-id": raw.get("turn_id", ""),
            "cwd": raw.get("cwd", ""),
            "last-assistant-message": raw.get("last_assistant_message", ""),
            "input-messages": [],
        }
    return None


def render_message(event: dict[str, Any], settings: dict[str, Any]) -> str:
    cwd = str(event.get("cwd") or "").strip()
    project = short_safe((Path(cwd).name or "未指定") if cwd else "未指定", 50)
    reply = str(event.get("last-assistant-message") or "")
    keyword = short_safe(str(settings.get("keyword") or ""), 40)
    header = f"{keyword} | Codex 任务通知" if keyword else "Codex 任务通知"
    lines = [header, f"项目：{project}", f"状态：{status_from_message(reply)}"]
    if settings.get("include_prompt", False):
        prompts = event.get("input-messages") or []
        if isinstance(prompts, list) and prompts:
            task = short_safe(str(prompts[0]), 90)
            if task:
                lines.append(f"任务：{task}")
    if settings.get("include_summary", True):
        summary = short_safe(reply, 180)
        lines.append(f"结果摘要：{summary or 'Codex 已结束当前轮次，可查看会话详情'}")
    lines.append("时间：" + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)


def send_text(message: str, settings: dict[str, Any]) -> None:
    url = sign_webhook(str(settings["webhook"]), str(settings.get("secret") or ""))
    body = json.dumps({"msgtype": "text", "text": {"content": message}}, ensure_ascii=False).encode("utf-8")
    outgoing = request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with request.urlopen(outgoing, timeout=8) as response:
            payload = response.read(16384)
    except error.HTTPError as exc:
        raise NotificationError(f"HTTP {exc.code}，请检查钉钉机器人状态及网络") from None
    except (error.URLError, TimeoutError, OSError) as exc:
        # Never print webhook URL (which includes the access token).
        raise NotificationError("网络连接失败，请确认 Codex 所在设备可连接 oapi.dingtalk.com") from exc
    try:
        result = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise NotificationError("钉钉响应不是有效 JSON") from exc
    if not isinstance(result, dict):
        raise NotificationError("钉钉响应格式异常")
    if str(result.get("errcode")) != "0":
        errcode = str(result.get("errcode", "未知"))
        if errcode == "310000":
            raise NotificationError("钉钉拒绝消息 (310000)：检查关键词、加签或 IP 白名单")
        raise NotificationError(f"钉钉拒绝消息 (错误码 {short_safe(errcode, 20)})")


def run() -> int:
    parser = argparse.ArgumentParser(description="Codex 钉钉任务完成通知")
    parser.add_argument("event_json", nargs="?", help="Codex notify 传入的 JSON 参数")
    parser.add_argument("--test", action="store_true", help="实际发送一条测试消息")
    parser.add_argument("--dry-run", action="store_true", help="只预览消息，不向钉钉发送")
    parser.add_argument("--hook", action="store_true", help="从 stdin 读取 Codex Stop hook JSON")
    args = parser.parse_args()
    if sum(bool(x) for x in (args.test, args.dry_run, args.hook, bool(args.event_json))) != 1:
        parser.error("请选择 --test、--dry-run、--hook 或提供通知 JSON")

    try:
        settings = {} if args.dry_run else load_config()
        if args.test:
            message = render_message({"cwd": os.getcwd(), "last-assistant-message": "钉钉通知接口连接测试成功。"}, settings)
        elif args.dry_run:
            message = render_message({"cwd": os.getcwd(), "last-assistant-message": "这是预览消息，不会实际发送。"}, settings)
        else:
            raw_json = sys.stdin.read() if args.hook else args.event_json
            raw = json.loads(raw_json or "{}")
            if not isinstance(raw, dict):
                raise NotificationError("事件 JSON 必须是对象")
            event = normalize_event(raw)
            if not event:
                return 0  # Ignore unsupported event types.
            message = render_message(event, settings)
        if args.dry_run:
            print(message)
            return 0
        send_text(message, settings)
        if args.test:
            print("钉钉测试消息发送成功")
        return 0
    except (NotificationError, ValueError, TypeError) as exc:
        print("Codex 钉钉通知：" + str(exc), file=sys.stderr)
        # A notification failure must never change the outcome of the Codex task.
        return 1 if args.test or args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(run())