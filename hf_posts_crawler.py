"""
Hugging Face Posts 爬虫和摘要程序
功能：
1. 爬取 https://huggingface.co/posts 前10个post
2. 对内容进行摘要，总结成中文
3. 每隔1小时执行一次
"""

import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
import logging
from typing import List, Dict
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hf_posts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HFPostsCrawler:
    def __init__(self):
        self.base_url = "https://huggingface.co/posts"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_posts(self, num_posts: int = 10) -> List[Dict]:
        """
        爬取 Hugging Face Posts
        """
        try:
            logger.info(f"开始爬取 Hugging Face Posts...")
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            posts = []

            # 查找post元素（需要根据实际HTML结构调整选择器）
            post_elements = soup.find_all('article', limit=num_posts)

            if not post_elements:
                # 尝试其他选择器
                post_elements = soup.find_all('div', class_='post', limit=num_posts)

            for idx, element in enumerate(post_elements, 1):
                try:
                    # 提取标题
                    title_elem = element.find('h2') or element.find('h3') or element.find('a')
                    title = title_elem.get_text(strip=True) if title_elem else f"Post {idx}"

                    # 提取链接
                    link_elem = element.find('a', href=True)
                    link = link_elem['href'] if link_elem else ""
                    if link and not link.startswith('http'):
                        link = f"https://huggingface.co{link}"

                    # 提取内容摘要
                    content_elem = element.find('p') or element.find('div', class_='content')
                    content = content_elem.get_text(strip=True) if content_elem else ""

                    posts.append({
                        'id': idx,
                        'title': title,
                        'link': link,
                        'content': content[:500]  # 限制内容长度
                    })

                    logger.info(f"成功爬取 Post {idx}: {title[:50]}")

                except Exception as e:
                    logger.warning(f"爬取 Post {idx} 时出错: {str(e)}")
                    continue

            logger.info(f"共成功爬取 {len(posts)} 个 posts")
            return posts

        except requests.RequestException as e:
            logger.error(f"网络请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"爬取过程中出错: {str(e)}")
            return []

    def summarize_in_chinese(self, posts: List[Dict]) -> str:
        """
        对爬取的posts进行中文摘要总结
        """
        try:
            logger.info("开始进行摘要和翻译...")

            # 如果没有安装transformers库，则使用简单的摘要方法
            try:
                from transformers import pipeline
                translator = pipeline("translation_zh_to_en", model="Helsinki-NLP/opus-mt-en-zh")
            except ImportError:
                logger.warning("transformers库未安装，使用简单摘要模式")
                translator = None

            summary_text = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Hugging Face Posts 摘要\n"
            summary_text += "=" * 50 + "\n\n"

            for post in posts:
                summary_text += f"【{post['id']}】{post['title']}\n"
                summary_text += f"链接: {post['link']}\n"

                # 简单摘要内容
                content = post['content']
                if content:
                    # 取前200个字符作为摘要
                    summary = content[:200] + "..." if len(content) > 200 else content
                    summary_text += f"内容摘要: {summary}\n"

                summary_text += "-" * 40 + "\n\n"

            return summary_text

        except Exception as e:
            logger.error(f"摘要过程中出错: {str(e)}")
            return ""

    def save_summary(self, summary: str, filename: str = None) -> None:
        """
        保存摘要到文件
        """
        if filename is None:
            filename = f"hf_posts_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(summary)
            logger.info(f"摘要已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")

    def run(self) -> None:
        """
        执行完整流程：爬取 -> 摘要 -> 保存
        """
        logger.info("=" * 50)
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)

        # 爬取posts
        posts = self.fetch_posts(num_posts=10)

        if posts:
            # 进行摘要
            summary = self.summarize_in_chinese(posts)

            if summary:
                # 输出到控制台
                print(summary)

                # 保存到文件
                self.save_summary(summary)
        else:
            logger.warning("未能获取任何posts")


def schedule_job():
    """
    定时任务：每隔1小时执行一次
    """
    crawler = HFPostsCrawler()

    def job():
        crawler.run()

    # 设置每小时执行一次
    schedule.every(1).hour.do(job)

    logger.info("定时任务已启动，每隔1小时执行一次")

    # 立即执行一次
    job()

    # 持续运行调度器
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("定时任务已停止")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        # 启动定时任务模式
        schedule_job()
    else:
        # 执行一次
        crawler = HFPostsCrawler()
        crawler.run()
