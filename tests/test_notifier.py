import base64
import hashlib
import hmac
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "codex-dingtalk-ping" / "scripts"))
import notify
import install


TEST_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=dummy-token"


class MockResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data


class NotifierTests(unittest.TestCase):
    def test_signed_url_exact_hmac(self):
        url = notify.sign_webhook(TEST_WEBHOOK, "SEC123abc", now_ms=1750000123456)
        params = parse_qs(urlsplit(url).query)
        digest = hmac.new(b"SEC123abc", b"1750000123456\nSEC123abc", hashlib.sha256).digest()
        self.assertEqual(params["sign"][0], base64.b64encode(digest).decode())
        self.assertEqual(params["timestamp"], ["1750000123456"])
        self.assertEqual(params["access_token"], ["dummy-token"])

    def test_unsigned_url(self):
        self.assertEqual(notify.sign_webhook(TEST_WEBHOOK, ""), TEST_WEBHOOK)

    def test_only_dingtalk_secure_webhook(self):
        for url in (
            "https://evil.example/robot/send?access_token=123",
            "http://oapi.dingtalk.com/robot/send?access_token=123",
            "https://oapi.dingtalk.com.evil.org/robot/send?access_token=123",
            "https://oapi.dingtalk.com/robot/send",
            "https://oapi.dingtalk.com/robot/sendBySession?session=123",
        ):
            with self.subTest(url=url), self.assertRaises(notify.NotificationError):
                notify.validate_webhook(url)

    def test_status_is_conservative(self):
        self.assertEqual(notify.status_from_message("状态：完成\n已验证"), "已完成")
        self.assertEqual(notify.status_from_message("状态：未完成\n需要批准"), "未完成／需关注")
        self.assertIn("本轮已结束", notify.status_from_message("解决方案已列出，尚需测试"))

    def test_safe_summary_and_no_prompt_by_default(self):
        event = {
            "cwd": "/Users/example/Finance-center",
            "input-messages": ["这是敏感的用户完整需求，不要直接外传"],
            "last-assistant-message": "已调整系统并提交测试。token=secret123\n附件 https://example.com/private?key=123",
        }
        text = notify.render_message(event, {"keyword": "通知", "include_summary": True})
        self.assertIn("项目：Finance-center", text)
        self.assertIn("通知 | Codex 任务通知", text)
        self.assertNotIn("敏感的用户完整需求", text)
        self.assertNotIn("secret123", text)
        self.assertNotIn("private?key=123", text)

    def test_prompt_opt_in(self):
        event = {"cwd": "/x/myproject", "input-messages": ["修复按钮交互"], "last-assistant-message": "已修复"}
        text = notify.render_message(event, {"include_prompt": True, "include_summary": False})
        self.assertIn("任务：修复按钮交互", text)
        self.assertNotIn("结果摘要", text)

    def test_notify_and_hook_event_parsing(self):
        self.assertEqual(notify.normalize_event({"type": "agent-turn-complete"})["type"], "agent-turn-complete")
        self.assertEqual(notify.normalize_event({"hook_event_name": "Stop", "last_assistant_message": "done"})["last-assistant-message"], "done")
        self.assertIsNone(notify.normalize_event({"type": "approval-requested"}))

    def test_request_body_and_success(self):
        with patch.object(notify.request, "urlopen", return_value=MockResponse(b'{"errcode":0,"errmsg":"ok"}')) as call:
            notify.send_text("中文消息", {"webhook": TEST_WEBHOOK})
        req = call.call_args.args[0]
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body, {"msgtype": "text", "text": {"content": "中文消息"}})
        self.assertEqual(req.get_method(), "POST")

    def test_api_error_has_safe_error(self):
        with patch.object(notify.request, "urlopen", return_value=MockResponse(b'{"errcode":310000,"errmsg":"secret bad"}')):
            with self.assertRaises(notify.NotificationError) as raised:
                notify.send_text("test", {"webhook": TEST_WEBHOOK})
        self.assertIn("关键词", str(raised.exception))
        self.assertNotIn("dummy-token", str(raised.exception))

    def test_register_global_notify_idempotently(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / "config.toml"
            config.write_text("model = 'gpt-6'\n\n[projects]\nx = 3\n", encoding="utf-8")
            script = Path(d) / "notify.py"
            install.configure_notify(config, script, "/opt/python3")
            first = config.read_text(encoding="utf-8")
            self.assertTrue(first.startswith('notify = ["/opt/python3",'))
            self.assertIn("[projects]", first)
            install.configure_notify(config, script, "/opt/python3")
            self.assertEqual(config.read_text(encoding="utf-8"), first)

    def test_existing_other_notify_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / "config.toml"
            original = 'notify = ["sh", "other.sh"]\n[model_providers.x]\nx = 1\n'
            config.write_text(original, encoding="utf-8")
            result = install.configure_notify(config, Path(d) / "notify.py", "python3")
            self.assertIn("已有 notify", result)
            self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_hook_merge_and_idempotency(self):
        with tempfile.TemporaryDirectory() as d:
            hooks = Path(d) / "hooks.json"
            hooks.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": []}]}}))
            script = Path(d) / "notify.py"
            install.configure_stop_hook(hooks, script, "/opt/python3")
            initial = hooks.read_text()
            self.assertEqual(len(json.loads(initial)["hooks"]["Stop"]), 1)
            install.configure_stop_hook(hooks, script, "/opt/python3")
            self.assertEqual(hooks.read_text(), initial)
            self.assertIn("UserPromptSubmit", initial)


if __name__ == "__main__":
    unittest.main()