"""
Hugging Face Posts 监控与中文摘要程序

功能：
  1. 每次爬取 https://huggingface.co/posts 前 10 个帖子
  2. 对帖子内容进行中文摘要并打印输出
  3. 每隔 1 小时自动重复执行

用法：
  # 执行一次后退出
  python hf_posts_monitor.py

  # 持续运行，每小时自动执行
  python hf_posts_monitor.py --loop

中文摘要策略（按优先级）：
  1. 若设置了环境变量 OPENAI_API_KEY，调用 OpenAI API 生成摘要
  2. 否则使用内置规则摘要（截取首句，不依赖任何额外模型）

依赖安装：
  pip install requests beautifulsoup4 schedule
  pip install openai          # 可选，启用 LLM 摘要
"""

import re
import os
import time
import logging
import schedule
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─────────────────────────── 日志 ─────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("hf_monitor.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────── 数据结构 ─────────────────────────────
@dataclass
class Post:
    rank: int
    author: str
    url: str
    text: str
    summary_zh: str = ""

    def preview(self, n: int = 100) -> str:
        t = self.text[:n].replace("\n", " ")
        return t + ("…" if len(self.text) > n else "")


# ─────────────────────────── 爬虫 ─────────────────────────────────
HF_URL = "https://huggingface.co/posts"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
# 匹配帖子正文 div 开头的 "Post 1234 " 这类前缀
_POST_PREFIX = re.compile(r"^Post\s+\d+\s*")


def fetch_posts(n: int = 10, timeout: int = 15) -> list[Post]:
    """请求 HuggingFace Posts 页面，解析前 n 条帖子。"""
    log.info("正在请求 %s …", HF_URL)
    try:
        resp = requests.get(HF_URL, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("网络请求失败：%s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # 帖子列表容器：class 含 mt-7 flex-col gap-10
    list_div = soup.find(
        "div",
        class_=lambda c: c and "mt-7" in c and "flex-col" in c and "gap-10" in c,
    )
    if list_div is None:
        log.error("未找到帖子列表容器，页面结构可能已变化。")
        return []

    # 每个直接子 div 是一个帖子完整单元（含作者行 + article）
    wrappers = [c for c in list_div.children if getattr(c, "name", None) == "div"]
    posts: list[Post] = []

    for wrapper in wrappers:
        if len(posts) >= n:
            break

        # ── 帖子链接 (/posts/<user>/<id>)
        article = wrapper.find("article")
        post_link_tag = (
            article.find("a", href=re.compile(r"^/posts/[\w-]+/\d+"))
            if article
            else None
        )
        if post_link_tag is None:
            continue
        url = "https://huggingface.co" + post_link_tag["href"]

        # ── 作者名 (href="/username")
        author_tag = wrapper.find("a", href=re.compile(r"^/[A-Za-z0-9_-]+$"))
        author = author_tag["href"].strip("/") if author_tag else "unknown"

        # ── 正文 (div.cursor-pointer，去掉 "Post 1234" 前缀)
        body_div = wrapper.find("div", class_="cursor-pointer")
        raw_text = body_div.get_text(" ", strip=True) if body_div else ""
        text = _POST_PREFIX.sub("", raw_text).strip()

        posts.append(Post(rank=len(posts) + 1, author=author, url=url, text=text))
        log.debug("  [%d] @%s  %s", len(posts), author, text[:60])

    log.info("共解析到 %d 条帖子。", len(posts))
    return posts


# ─────────────────────────── 中文摘要 ─────────────────────────────
def _llm_summarize(text: str) -> Optional[str]:
    """调用 OpenAI API 生成中文摘要（需要 OPENAI_API_KEY）。"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        import openai  # type: ignore
        client = openai.OpenAI(api_key=api_key)
        rsp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一名技术写手。"
                        "请把下列英文帖子内容总结成 60 字以内的简洁中文摘要，"
                        "突出最核心的信息，不加任何多余说明。"
                    ),
                },
                {"role": "user", "content": text[:2000]},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return rsp.choices[0].message.content.strip()
    except Exception as exc:
        log.warning("OpenAI 摘要失败（%s），改用规则摘要。", exc)
        return None


def _rule_summarize(text: str, limit: int = 120) -> str:
    """规则摘要：取第一句有效内容，截断到 limit 字符。"""
    sentence = re.split(r"[.!?。！？\n]", text)[0].strip()
    result = sentence if sentence else text
    if len(result) > limit:
        result = result[:limit] + "……"
    return result


def summarize_zh(post: Post) -> str:
    """对单条帖子生成中文摘要（优先 LLM，降级规则）。"""
    if not post.text:
        return "（暂无正文内容）"
    zh = _llm_summarize(post.text)
    return zh if zh else _rule_summarize(post.text)


# ─────────────────────────── 主任务 ─────────────────────────────
SEP = "═" * 62


def run_job() -> None:
    """完整执行一次：爬取 → 摘要 → 打印报告。"""
    start = datetime.now()

    print(f"\n{SEP}")
    print(f"  📋 Hugging Face Posts 中文摘要报告")
    print(f"  执行时间：{start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    posts = fetch_posts(n=10)
    if not posts:
        print("  ⚠  未能获取帖子，请检查网络连接。")
        print(f"{SEP}\n")
        return

    use_llm = bool(os.getenv("OPENAI_API_KEY"))
    print(f"  摘要模式：{'OpenAI LLM' if use_llm else '规则摘要（未设置 OPENAI_API_KEY）'}")
    print(SEP)

    for post in posts:
        post.summary_zh = summarize_zh(post)

    for post in posts:
        print(f"\n  #{post.rank:02d}  @{post.author}")
        print(f"  链接    : {post.url}")
        print(f"  原文    : {post.preview(120)}")
        print(f"  中文摘要: {post.summary_zh}")
        print(f"  {'─' * 58}")

    elapsed = (datetime.now() - start).seconds
    print(f"\n  共 {len(posts)} 条帖子，耗时 {elapsed}s")
    print(f"  下次执行：1 小时后")
    print(f"{SEP}\n")


# ─────────────────────────── 入口 ─────────────────────────────────
if __name__ == "__main__":
    import sys

    loop_mode = "--loop" in sys.argv

    log.info("=== hf_posts_monitor 启动 ===")
    run_job()  # 立即执行一次

    if loop_mode:
        schedule.every(1).hour.do(run_job)
        log.info("定时模式已启动，每隔 1 小时执行一次（Ctrl+C 退出）。")
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            log.info("用户中断，程序退出。")
    else:
        log.info("单次模式完成。如需持续运行，请加 --loop 参数。")
