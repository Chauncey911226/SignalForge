"""
main.py - SignalForge 主入口
串联 RSS 抓取 → 大模型清洗 → 飞书推送
"""

from datetime import datetime, timezone, timedelta
from rss_fetcher import fetch_all
from llm_cleaner import clean
from feishu_bot import send_markdown


def run():
    now = datetime.now(timezone(timedelta(hours=8)))
    date_str = now.strftime("%Y-%m-%d")

    print(f"{'='*50}")
    print(f"SignalForge 每日资讯 - {date_str}")
    print(f"{'='*50}")

    print("\n[1/3] 抓取 RSS 源...")
    entries = fetch_all()

    if not entries:
        print("[跳过] 没有获取到任何资讯，发送空通知")
        msg = f"**SignalForge 日报 {date_str}**\n\n今日暂无相关资讯，RSS 源可能均未更新。"
        send_markdown(msg)
        return

    print(f"\n[2/3] 大模型清洗 {len(entries)} 条资讯...")
    summary = clean(entries)

    print(f"\n[3/3] 推送到飞书...")
    msg = f"**SignalForge 日报 {date_str}**\n\n{summary}"
    send_markdown(msg)

    print(f"\n{'='*50}")
    print(f"SignalForge 运行完毕 ✅")
    print(f"{'='*50}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run()
