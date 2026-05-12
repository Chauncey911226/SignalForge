"""
llm_cleaner.py - 大模型清洗大脑
接入阿里云百炼 API（兼容 OpenAI 格式），对 RSS 原始数据进行过滤和摘要
"""

import os
import json
from openai import OpenAI


SYSTEM_PROMPT = """你是一个专业的 AI 科技资讯编辑。你的任务是：

1. 浏览所有获取到的信息，过滤闲聊和纯学术代码更新
2. 只保留与以下领域相关的资讯：AI应用、独立开发、AI工具、微型SaaS
3. 将筛选后的资讯按照重要程度排序（重要在前）
4. 每个条目用一个标题加一段概括呈现
5. 最终以 Markdown 有序列表形式输出

输出格式要求：
- 使用中文概括
- 每个条目格式为：**标题** + 换行 + 一段概括（2-3句话）+ 换行 + 原文链接
- 链接格式为：🔗 [查看原文](链接地址)
- 每个条目必须附带原文链接，链接来自输入数据中的"链接"字段
- 如果没有任何相关资讯，输出"今日暂无相关资讯"

示例：
1. **GPT-5 发布：多模态能力大幅提升**
   OpenAI 今日正式发布 GPT-5，在多模态理解和代码生成方面有显著提升，API 价格与 GPT-4o 持平，对独立开发者友好。
   🔗 [查看原文](https://openai.com/blog/gpt5)

2. **开源 AI Agent 框架 AutoGen 更新 v0.3**
   微软开源的 AI Agent 框架 AutoGen 发布 v0.3 版本，新增工作流可视化编辑器，降低了 AI Agent 应用的开发门槛。
   🔗 [查看原文](https://reddit.com/r/autogen/xxx)"""


def _build_user_message(entries: list[dict]) -> str:
    """
    将 RSS 条目列表拼成大模型可读的文本
    """
    parts = []
    for i, e in enumerate(entries, 1):
        block = f"【{i}】来源: {e['source']}\n标题: {e['title']}\n链接: {e['link']}\n摘要: {e['summary']}"
        parts.append(block)

    return f"以下是从各 RSS 源获取的近 24 小时资讯，共 {len(entries)} 条：\n\n" + "\n\n".join(parts)


def clean(entries: list[dict],
          api_key: str = None,
          base_url: str = None,
          model: str = None) -> str:
    """
    调用大模型对 RSS 条目进行过滤和摘要

    参数:
        entries:  RSS 条目列表（来自 rss_fetcher.fetch_all 的返回值）
        api_key:  API 密钥（默认从环境变量 LLM_API_KEY 读取）
        base_url: API 基础地址（默认从环境变量 LLM_BASE_URL 读取）
        model:    模型名称（默认从环境变量 LLM_MODEL 读取）

    返回:
        大模型输出的 Markdown 格式资讯摘要
    """
    api_key = api_key or os.environ.get("LLM_API_KEY")
    base_url = base_url or os.environ.get("LLM_BASE_URL")
    model = model or os.environ.get("LLM_MODEL")

    if not api_key:
        raise ValueError("缺少 API Key，请设置环境变量 LLM_API_KEY 或传入参数")
    if not base_url:
        raise ValueError("缺少 Base URL，请设置环境变量 LLM_BASE_URL 或传入参数")
    if not model:
        raise ValueError("缺少模型名称，请设置环境变量 LLM_MODEL 或传入参数")

    client = OpenAI(api_key=api_key, base_url=base_url)

    user_message = _build_user_message(entries)

    print(f"[大模型] 发送 {len(entries)} 条资讯给 {model} 进行清洗...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=4000,
    )

    result = response.choices[0].message.content.strip()
    print(f"[大模型] 清洗完成，输出 {len(result)} 字符")

    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from rss_fetcher import fetch_all

    entries = fetch_all()
    if not entries:
        print("[跳过] 没有获取到任何资讯，无需清洗")
    else:
        result = clean(entries)
        print("\n" + "=" * 60)
        print("清洗结果：")
        print("=" * 60)
        print(result)
