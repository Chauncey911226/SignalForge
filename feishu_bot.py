"""
feishu_bot.py - 飞书自定义机器人推送模块
支持签名校验方式发送 Markdown 格式消息
"""

import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests


def _gen_sign(secret: str) -> tuple[str, str]:
    """
    根据飞书签名密钥生成 timestamp 和 sign
    飞书签名规则：timestamp + "\n" + secret → HMAC-SHA256 → Base64 → URL编码
    """
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_markdown(content: str, webhook_url: str = None, secret: str = None) -> dict:
    """
    发送 Markdown 格式消息到飞书群

    参数:
        content:     Markdown 格式的消息内容
        webhook_url: 飞书机器人 Webhook 地址（默认从环境变量 FEISHU_WEBHOOK_URL 读取）
        secret:      飞书签名密钥（默认从环境变量 FEISHU_SECRET 读取）

    返回:
        飞书接口的 JSON 响应
    """
    webhook_url = webhook_url or os.environ.get("FEISHU_WEBHOOK_URL")
    secret = secret or os.environ.get("FEISHU_SECRET")

    if not webhook_url:
        raise ValueError("缺少 webhook_url，请设置环境变量 FEISHU_WEBHOOK_URL 或传入参数")
    if not secret:
        raise ValueError("缺少 secret，请设置环境变量 FEISHU_SECRET 或传入参数")

    timestamp, sign = _gen_sign(secret)

    url = f"{webhook_url}?timestamp={timestamp}&sign={sign}"

    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                }
            ]
        }
    }

    resp = requests.post(url, json=payload, timeout=10)
    result = resp.json()

    if result.get("code") != 0:
        print(f"[飞书推送失败] {result}")
    else:
        print("[飞书推送成功]")

    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    test_msg = """**SignalForge 测试消息**

这是一条来自 SignalForge 的测试推送 ✅

如果你在飞书群里看到了这条消息，说明推送通道已经打通！"""

    send_markdown(test_msg)
