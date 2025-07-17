# -*- coding: utf-8 -*-
"""
功能：从 txt 文件中批量提取下载链接、目录和文件名，调用 download_file() 函数下载，
      并对失败任务构建重试队列，隔一段时间后重新尝试下载。最终将多次重试仍失败的任务
      导出为 JSON 便于手动处理。所有生成文件都保存在脚本同级目录下。
"""

import os
import re
import json
import time
import random
import logging
from datetime import datetime
from collections import deque
from mymodule import download_file, size_display

# ========== 配置区 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 输入 txt
INPUT_TXT = os.path.join(BASE_DIR, r"F:\CloneCode_2\KMP-Kemono-Downloader\logs\LOG - Thu Jul 17 15-17-46 UTC 2025.txt")

# 已下载记录（JSON）
DOWNLOADED_JSON = os.path.join(BASE_DIR, "downloaded.json")

# 错误日志（仅记录下载失败信息）
ERROR_LOG = os.path.join(BASE_DIR, "error.log")

# 手动失败导出列表（JSON）
MANUAL_FAILURES_JSON = os.path.join(BASE_DIR, "manual_failures.json")

# 正则：SRC: <url>, FNAME: <full_path>
LINE_PATTERN = re.compile(
    r"SRC:\s*(?P<url>[^,]+),\s*FNAME:\s*(?P<full_path>.+)",
    re.IGNORECASE
)

# 下载函数参数（与 download_file 通用）
PROXIES = None
HEADERS = {"user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"}
MAX_RETRIES = 60
MAX_DOWNLOAD_SECONDS = 30
PLAY_SOUND = False
CHUNK_SIZE = 8192
VERIFY_SSL = True
MAX_FILENAME_LENGTH = 20
RETRY_SLEEP_RANGE = (5, 20)

# 日志配置：只记录错误
error_logger = logging.getLogger("error")
error_logger.setLevel(logging.ERROR)
err_handler = logging.FileHandler(ERROR_LOG, encoding="utf-8")
err_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
error_logger.addHandler(err_handler)


def load_downloaded_records(json_path: str) -> list:
    """
    读取已下载记录的 JSON 文件，返回 list。如果不存在或格式错误，返回空列表。
    """
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_downloaded_records(records: list, json_path: str):
    """
    将下载记录列表写入 JSON 文件，ensure_ascii=False 保持中文不转义，缩进格式化。
    """
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def load_downloaded_urls(records: list) -> set:
    """
    从记录列表中提取所有已下载 URL，用于去重。
    """
    return {entry["url"] for entry in records if "url" in entry}


def parse_input_file(txt_path: str) -> list:
    """
    解析 txt，每行符合格式时提取 url、parent_dir、filename，返回字典列表。
    """
    entries = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = LINE_PATTERN.search(line)
            if not m:
                continue
            url = m.group("url").strip()
            full_path = m.group("full_path").strip()
            parent_dir = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            entries.append({
                "url": url,
                "parent_dir": parent_dir,
                "filename": filename,
                # 初始化重试次数字段
                "retry_count": 0
            })
    return entries


def ensure_directory(path: str):
    """
    如果目录不存在则创建，支持多级创建。
    """
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def extract_directory_id(path: str) -> str:
    """
    从 parent_dir 路径末尾目录名中提取数字 ID。
    例如 ".../47233473 Post .../" 取 "47233473"。
    """
    base = os.path.basename(path.rstrip(os.sep))
    token = base.split()[0] if base else ""
    return token if token.isdigit() else ""


def main():
    # 1. 已下载记录和 URL 缓存
    records = load_downloaded_records(DOWNLOADED_JSON)
    downloaded_urls = load_downloaded_urls(records)

    # 2. 解析所有待下载 entries，初始队列过滤已下载
    all_entries = parse_input_file(INPUT_TXT)
    queue = deque(e for e in all_entries if e["url"] not in downloaded_urls)

    total_tasks = len(queue)
    print(f"共 {len(all_entries)} 条记录，{total_tasks} 条待下载，开始执行队列...")

    manual_failures = []

    # 3. 处理队列：成功记录、失败重试、超次导出
    while queue:
        entry = queue.popleft()
        url = entry["url"]
        parent_dir = entry["parent_dir"]
        filename = entry["filename"]
        retry_count = entry["retry_count"]

        print(f"[{total_tasks - len(queue)}/{total_tasks}] 尝试下载: {filename} （已重试 {retry_count} 次）")

        try:
            ensure_directory(parent_dir)
            download_result = download_file(
                url=url,
                filename=filename,
                parent_dir=parent_dir,
                proxies=PROXIES,
                headers=HEADERS,
                max_retries=MAX_RETRIES,
                max_download_seconds=MAX_DOWNLOAD_SECONDS,
                play_sound=PLAY_SOUND,
                chunk_size=CHUNK_SIZE,
                verify_ssl=VERIFY_SSL,
                max_filename_length=MAX_FILENAME_LENGTH,
                retry_sleep_range=RETRY_SLEEP_RANGE
            )

            if download_result in ['下载成功', '下载成功，但文件大小未知', '跳过下载']:
                # 下载完成后记录并保存
                full_path = os.path.join(parent_dir, filename)
                raw_size = os.path.getsize(full_path)
                size_str = size_display(raw_size)
                dir_id = extract_directory_id(parent_dir)

                record = {
                    "url": url,
                    "parent_dir": parent_dir,
                    "filename": filename,
                    "download_time": datetime.now().isoformat(),
                    "file_size": size_str,
                    "directory_id": dir_id
                }
                records.append(record)
                save_downloaded_records(records, DOWNLOADED_JSON)
            else:
                raise "下载失败"

        except Exception as ex:
            # 下载失败：记录日志
            error_logger.error(f"URL={url} 文件={filename} 错误：{ex}")

            # 若重试次数未达上限（同 download_file()），则排队重试
            if retry_count < MAX_RETRIES:
                entry["retry_count"] += 1
                wait_sec = random.uniform(*RETRY_SLEEP_RANGE)
                print(f"  !! 失败，{wait_sec:.1f}s 后重试 (第 {entry['retry_count']} 次)")
                time.sleep(wait_sec)
                queue.append(entry)
            else:
                # 超过重试上限，加入手动失败列表
                print(f"  !! 超过最大重试次数 {MAX_RETRIES}，加入手动失败列表")
                manual_failures.append({
                    "url": url,
                    "parent_dir": parent_dir,
                    "filename": filename,
                    "last_error": str(ex),
                    "retry_count": retry_count
                })

    # 4. 导出手动失败列表
    if manual_failures:
        with open(MANUAL_FAILURES_JSON, "w", encoding="utf-8") as f:
            json.dump(manual_failures, f, ensure_ascii=False, indent=2)
        print(f"部分任务多次重试仍失败，已导出至 {MANUAL_FAILURES_JSON}")

    print("所有下载和重试任务已完成。")


if __name__ == "__main__":
    main()
