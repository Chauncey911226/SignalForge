"""
rss_fetcher.py - RSS 信号抓取器
遍历 RSS 源列表，提取标题、链接、摘要，只保留过去 24 小时内的数据
"""

import time
from datetime import datetime, timezone, timedelta
import feedparser
import requests


RSS_SOURCES = [
    {
        "name": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
    },
    {
        "name": "Anthropic",
        "url": "https://rsshub.app/anthropic/news",
        "mirrors": [
            "https://rss.shoya.io/anthropic/news",
            "https://rsshub.liumingye.cn/anthropic/news",
        ],
    },
    {
        "name": "HackerNews",
        "url": "https://news.ycombinator.com/rss",
    },
    {
        "name": "Reddit-LocalLLaMA",
        "url": "https://www.reddit.com/r/LocalLLaMA.rss",
    },
    {
        "name": "ProductHunt",
        "url": "https://www.producthunt.com/feed",
    },
    {
        "name": "V2EX",
        "url": "https://www.v2ex.com/feed/create.xml",
    },
    {
        "name": "少数派",
        "url": "https://rsshub.rssforever.com/sspai/matrix",
    },
    {
        "name": "TechCrunch-AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/xml, application/rss+xml, application/atom+xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_REQUEST_TIMEOUT = 20
_MAX_RETRIES = 2


def _parse_published_time(entry) -> datetime | None:
    """
    尝试从 RSS 条目中解析发布时间
    feedparser 会把时间解析为 time.struct_time 存在 entry.published_parsed 中
    """
    parsed = None
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            break

    if not parsed:
        return None

    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except Exception:
        return None


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    """
    先用 requests 获取内容，再交给 feedparser 解析
    这样可以绕过 Cloudflare 的基础检测，也能获得更好的错误信息
    """
    resp = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type and "xml" not in content_type:
        snippet = resp.text[:200].replace("\n", " ")
        raise ValueError(f"返回了 HTML 而非 RSS: {snippet}")

    return feedparser.parse(resp.content)


def _fetch_with_retry(url: str, retries: int = _MAX_RETRIES) -> feedparser.FeedParserDict:
    """
    带重试的 feed 获取，遇到超时或 5xx 错误自动重试
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return _fetch_feed(url)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < retries:
                wait = attempt * 3
                print(f"  [重试 {attempt}/{retries}] {wait}s 后重试...")
                time.sleep(wait)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500 and attempt < retries:
                wait = attempt * 3
                print(f"  [重试 {attempt}/{retries}] 服务器 {e.response.status_code}，{wait}s 后重试...")
                time.sleep(wait)
            else:
                raise
    raise last_error


def _fetch_source(source: dict) -> feedparser.FeedParserDict | None:
    """
    尝试主 URL，失败则依次尝试镜像
    """
    urls = [source["url"]] + source.get("mirrors", [])
    for i, url in enumerate(urls):
        label = "主源" if i == 0 else f"镜像{i}"
        try:
            feed = _fetch_with_retry(url)
            if i > 0:
                print(f"  [镜像命中] 使用 {label}")
            return feed
        except Exception:
            if i == len(urls) - 1:
                return None
            print(f"  [{label}失败] 尝试下一个...")
            continue
    return None


def fetch_all(sources: list[dict] = None, hours: int = 24) -> list[dict]:
    """
    抓取所有 RSS 源，返回过去 N 小时内的条目列表

    参数:
        sources: RSS 源配置列表（默认使用 RSS_SOURCES）
        hours:   保留多少小时内的条目（默认 24）

    返回:
        [{"title": ..., "link": ..., "summary": ..., "source": ..., "published": ...}, ...]
    """
    sources = sources or RSS_SOURCES
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_entries = []

    for source in sources:
        name = source["name"]
        print(f"[抓取中] {name}")

        feed = _fetch_source(source)

        if feed is None:
            print(f"  [全部失败] {name} 所有源均不可用")
            continue

        if feed.bozo and not feed.entries:
            print(f"  [解析失败] {feed.bozo_exception}")
            continue

        count = 0
        for entry in feed.entries:
            pub_time = _parse_published_time(entry)

            if pub_time and pub_time < cutoff:
                continue

            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description

            all_entries.append({
                "title": getattr(entry, "title", "无标题"),
                "link": getattr(entry, "link", ""),
                "summary": summary[:500],
                "source": name,
                "published": pub_time.isoformat() if pub_time else None,
            })
            count += 1

        print(f"  [完成] {count} 条近 {hours}h / 共 {len(feed.entries)} 条")

    print(f"\n[汇总] 共 {len(all_entries)} 条近 {hours}h 资讯")
    return all_entries


if __name__ == "__main__":
    entries = fetch_all()

    print("\n" + "=" * 60)
    print(f"共 {len(entries)} 条资讯：")
    print("=" * 60)
    for i, e in enumerate(entries, 1):
        print(f"\n{i}. [{e['source']}] {e['title']}")
        print(f"   链接: {e['link']}")
        print(f"   时间: {e['published']}")
        print(f"   摘要: {e['summary'][:100]}...")
