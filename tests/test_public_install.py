"""Integration checks for the public GitHub installation layout."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'codex-dingtalk-ping'


class PublicInstallTests(unittest.TestCase):
    def test_skill_has_expected_entrypoint(self):
        text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\nname: codex-dingtalk-ping\n'))
        self.assertTrue((SKILL / 'agents' / 'openai.yaml').is_file())
        self.assertTrue((SKILL / 'scripts' / 'install.py').is_file())
        self.assertTrue((SKILL / 'scripts' / 'notify.py').is_file())

    def test_agent_can_register_without_secrets_or_tty(self):
        with tempfile.TemporaryDirectory() as directory:
            codex = Path(directory) / '.codex'
            dest = codex / 'skills' / 'codex-dingtalk-ping'
            dest.parent.mkdir(parents=True)
            shutil.copytree(SKILL, dest)
            (codex / 'config.toml').write_text('model = "test"\n', encoding='utf-8')
            env = dict(os.environ, CODEX_HOME=str(codex))
            result = subprocess.run([sys.executable, str(dest / 'scripts/install.py'), '--no-prompt'],
                                    stdin=subprocess.DEVNULL, text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = (codex / 'config.toml').read_text(encoding='utf-8')
            self.assertIn('notify = [', config)
            self.assertIn(str(dest / 'scripts/notify.py'), config)
            self.assertIn('model = "test"', config)
            self.assertFalse((codex / 'codex-dingtalk-ping.json').exists())
            self.assertIn('Webhook 尚未配置', result.stdout)
            again = subprocess.run([sys.executable, str(dest / 'scripts/install.py'), '--no-prompt'],
                                   stdin=subprocess.DEVNULL, text=True, capture_output=True, env=env)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual((codex / 'config.toml').read_text(encoding='utf-8'), config)
            preview = subprocess.run([sys.executable, str(dest / 'scripts/notify.py'), '--dry-run'],
                                     stdin=subprocess.DEVNULL, text=True, capture_output=True, env=env)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn('本轮已结束', preview.stdout)


if __name__ == '__main__':
    unittest.main()