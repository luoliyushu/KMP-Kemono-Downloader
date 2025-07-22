# -*- coding: utf-8 -*-
"""
cleanup_duplicates.py

用途：对比同一 post ID 的多个下载文件夹，保留最新创建的，旧版移入回收站，并记录日志。
环境：Windows 11，Python 3.x
依赖：Send2Trash（pip install Send2Trash）
说明：
  链接格式中“fanbox”部分不再固定，脚本改用通用正则来提取 user_id 和 post_id。
  脚本启动时通过 input() 提示用户输入文件路径，而非命令行参数。
"""

import os
import sys
import json
import traceback
from pathlib import Path
from send2trash import send2trash
import re
import datetime

def log_message(log_file: Path, message: str):
    """
    将 message 追加写入 log_file，保证 UTF-8 编码
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def main(txt_path: Path, json_path: Path):
    # 日志文件：与脚本同级目录
    script_dir = Path(__file__).parent
    log_file = script_dir / "cleanup.log"

    try:
        # 1. 读取 JSON 配置
        with json_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        records = config.get("RECORDS", [])

        # 2. 从 JSON url 通用提取 user_id，建立映射
        user_map = {}
        uid_pattern = re.compile(r"/user/(\d+)$")
        for rec in records:
            url = rec.get("url", "")
            m = uid_pattern.search(url)
            if m:
                user_map[m.group(1)] = rec

        # 3. 读取 TXT 文件，提取每行的 user_id 和 post_id
        url_pattern = re.compile(r"https?://[^/]+/[^/]+/user/(\d+)/post/(\d+)")
        with txt_path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        for line in lines:
            m = url_pattern.match(line)
            if not m:
                log_message(log_file, f"无法解析 URL（非标准托管类型），跳过: {line}")
                continue

            user_id, post_id = m.group(1), m.group(2)

            # 4. 在 JSON 中查找对应记录
            rec = user_map.get(user_id)
            if not rec:
                log_message(log_file, f"JSON 中未找到 user_id={user_id}，跳过 URL: {line}")
                continue

            artist = rec.get("artist")
            dest = rec.get("destination")
            if not artist or not dest:
                log_message(log_file, f"配置缺失 artist 或 destination，user_id={user_id}，跳过")
                continue

            artist_dir = Path(dest) / artist
            if not artist_dir.exists() or not artist_dir.is_dir():
                log_message(log_file, f"artist 目录不存在: {artist_dir}")
                continue

            # 5. 查找同一 post_id 的所有下载子目录
            same_id_dirs = []
            for child in artist_dir.iterdir():
                if child.is_dir() and child.name.startswith(post_id + " "):
                    same_id_dirs.append(child)

            if len(same_id_dirs) <= 1:
                log_message(log_file, f"{artist_dir} 中 post_id={post_id} 共 {len(same_id_dirs)} 个，无需处理")
                continue

            # 6. 按创建时间选最新的保留，其他移至回收站
            times = {p: p.stat().st_ctime for p in same_id_dirs}
            keep_dir = max(times, key=times.get)
            del_dirs = [p for p in same_id_dirs if p != keep_dir]

            log_message(log_file, f"保留 (最新创建): {keep_dir}")
            for d in del_dirs:
                try:
                    send2trash(str(d))
                    log_message(log_file, f"移至回收站: {d}")
                except Exception:
                    err = traceback.format_exc()
                    log_message(log_file, f"删除失败: {d}，错误详情:\n{err}")

    except Exception:
        # 捕获所有意外异常并记录
        err = traceback.format_exc()
        log_message(log_file, f"脚本执行异常:\n{err}")
        sys.exit(1)

if __name__ == "__main__":
    # 通过 input() 获取文件路径
    txt_input = input("请输入包含 URL 的 TXT 文件路径：").strip()
    json_input = input("请输入 JSON 配置文件路径：").strip()

    txt_path = Path(txt_input)
    json_path = Path(json_input)

    # 路径校验
    if not txt_path.is_file():
        print(f"错误：TXT 文件不存在或不是文件：{txt_path}")
        sys.exit(1)
    if not json_path.is_file():
        print(f"错误：JSON 文件不存在或不是文件：{json_path}")
        sys.exit(1)

    main(txt_path, json_path)
