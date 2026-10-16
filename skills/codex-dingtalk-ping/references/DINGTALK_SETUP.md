# 配置钉钉群自定义机器人 / DingTalk Setup

本 Skill 仅支持旧版**群自定义机器人 Webhook**，不是企业内部应用机器人或单聊机器人。钉钉已公告停止新增旧版自定义机器人；已存在的机器人可继续按其平台规则使用。新用户找不到创建入口时，不能使用 AppKey/AppSecret 冒充 Webhook。详见[钉钉下线公告](https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice)。

## 第一步：在目标群中找到机器人

钉钉电脑端 → 希望收到 Codex 通知的群聊 → **群设置** → **智能群助手 / 机器人 / 群机器人**（不同客户端的名称可能不同）→ 找到**已有的自定义机器人** → **设置 / 详情**。如果仍显示新增入口，可参照官方步骤，但不保证新建功能开放。

官方说明：[自定义机器人接入](https://open.dingtalk.com/document/orgapp/custom-robot-access)。

## 第二步：复制 Webhook

机器人详情 / 创建完成页面中复制**完整 Webhook**，例如：

```text
https://oapi.dingtalk.com/robot/send?access_token=...
```

包括完整 `access_token`；这是敏感凭据，绝不可发布到 GitHub、贴在 Codex 聊天中或放在项目源码里。

## 第三步：取得加签密钥和安全关键词

在**同一个机器人**的**安全设置**里：

- **加签**：如启用，复制加签密钥，通常以 `SEC...` 开头；未启用则在配置时留空。它**不是**企业应用的 `AppSecret`。
- **自定义关键词**：如启用，记下一个已经在钉钉设置好的关键词，例如 `Codex`，在配置时填写。程序会将它插入消息以匹配校验；没有启用则留空。
- **IP 白名单**：如启用，确认运行 Codex 的设备 / 代理所用**出口公网 IP**在允许名单内。

按真实启用的安全方式填写，不能自己编造 `SEC` 密钥。

## 第四步：在个人本地终端配置

不要把 Webhook 或 SEC 密钥发送到聊天窗口。在自己的终端运行：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/install.py" --configure
```

凭据会写在本机 `${CODEX_HOME:-~/.codex}/codex-dingtalk-ping.json` 中，文件权限为 `0600`；Webhook / 密钥输入不回显。现有配置不会覆盖，修改前先在自己的电脑上安全备份。

## 第五步：测试并启用

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/codex-dingtalk-ping/scripts/notify.py" --test
```

这个操作会**真实向钉钉群发送一条测试消息**。确认群里收到之后，重新开启**本地 Codex** 并完成一轮任务以验证自动触发。测试无法送达时，检查 Webhook、SEC、关键词、IP 白名单和旧机器人是否可用；测试送达但任务完成没有通知时，检查本地 Codex 触发器。纯 Codex Cloud 任务不会自动执行本地通知脚本。

**English:** Open the target DingTalk group → Group settings → Robots → existing legacy Custom Robot → Settings. Copy the full Webhook; from Security Settings copy `SEC...` if signing is enabled, and record a configured keyword if keyword validation is enabled. Run the private local configure command, then the real-send test command above. Official documentation and sunset notice are linked above.
