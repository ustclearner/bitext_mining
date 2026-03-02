# Hugging Face Posts 爬虫程序

## 功能描述

这个程序实现了以下功能：

1. **爬取 Hugging Face Posts**
   - 从 https://huggingface.co/posts 爬取前10个最新post
   - 提取标题、链接和内容摘要

2. **中文摘要**
   - 对爬取的内容进行摘要和总结
   - 输出中文格式的总结报告

3. **定时执行**
   - 每隔1小时自动执行一次爬取和摘要任务
   - 生成日志记录和摘要文件

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 执行一次

```bash
python hf_posts_crawler.py
```

### 启动定时任务（每小时执行一次）

```bash
python hf_posts_crawler.py --schedule
```

## 输出

程序会：
- 在控制台输出摘要内容
- 将摘要保存到 `hf_posts_summary_YYYYMMDD_HHMMSS.txt` 文件
- 所有操作日志记录到 `hf_posts.log` 文件

## 日志文件

- `hf_posts.log` - 程序运行的详细日志
- `hf_posts_summary_*.txt` - 生成的摘要文件

## 示例输出

```
[2024-01-15 10:30:45] Hugging Face Posts 摘要
==================================================

【1】Model Zoo Updated
链接: https://huggingface.co/posts/...
内容摘要: This is a summary of the post content...
----------------------------------------
```

## 注意事项

- 确保网络连接正常
- transformers库用于更高级的文本处理（可选）
- 首次运行可能需要下载预训练模型
- 定时任务模式会一直运行，按 Ctrl+C 停止
