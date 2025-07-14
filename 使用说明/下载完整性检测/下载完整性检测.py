#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：
    检测 Post 目录本地文件数与接口返回的 post.attachments 数量是否异常：
      - attachments > 本地文件数 → 记录
      - attachments < 本地文件数 → 检查是否存在“0.*”文件，忽略后再比，仍不匹配则记录
      - attachments == 本地文件数 → 跳过
    支持两种模式：
      1. 从 JSON 文件读取目录列表（JSON 中需有 "empty_dirs" 列表）
      2. 手动输入根目录，递归收集以数字开头的子目录
    处理过的目录会即时写入 processed_dirs.json，下次运行跳过以节省时间  
    异常目录汇总到 results_summary.txt，所有异常写入 error_log.txt。

依赖：
    requests 库（pip install requests）
"""

import os
import sys
import json
import re
import logging
import traceback
from urllib.parse import urljoin
import time

# 检查并导入 requests 库
try:
    import requests
except ImportError:
    print("缺少 requests 库，请先运行：pip install requests")
    sys.exit(1)

def setup_logger(log_path):
    """
    配置日志记录器，将 ERROR 及以上消息追加写入 log_path
    """
    logging.basicConfig(
        filename=log_path,
        filemode='a',
        level=logging.ERROR,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def prompt_mode():
    """
    提示选择运行模式：
      1 - JSON 模式（默认，从 JSON 文件读取目录列表）
      2 - 目录模式（手动输入根目录，递归收集子目录）
    """
    while True:
        mode = input("请选择模式 (1=JSON文件; 2=手动目录)【默认1】：").strip()
        if mode in ('', '1', '2'):
            return '1' if mode in ('', '1') else '2'
        print("请输入 1 或 2。")

def prompt_json_path(default_path):
    """
    提示输入 JSON 文件路径，回车使用默认
    """
    while True:
        path = input(f"请输入 JSON 文件路径（回车默认：{default_path}）：").strip()
        if not path:
            path = default_path
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isfile(path):
            return path
        print(f"无效文件路径：{path}")

def load_dirs_from_json(json_path):
    """
    加载 JSON 文件，返回 "empty_dirs" 列表
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        dirs = data.get("empty_dirs")
        if not isinstance(dirs, list):
            raise ValueError('"empty_dirs" 字段缺失或不是列表')
        return dirs
    except Exception as e:
        raise RuntimeError(f"加载 JSON 失败：{e}")

def prompt_root_dir(default_dir):
    """
    提示输入根目录，回车使用默认
    """
    while True:
        path = input(f"请输入根目录路径（回车默认：{default_dir}）：").strip()
        if not path:
            path = default_dir
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(path):
            return path
        print(f"无效目录路径：{path}")

def collect_post_dirs(root_dir):
    """
    遍历 root_dir，收集所有以数字开头的目录
    """
    result = []
    for current, _, _ in os.walk(root_dir):
        name = os.path.basename(current.rstrip(os.sep))
        if re.match(r'^\d+', name):
            result.append(current)
    return result

def extract_post_id(dir_path):
    """
    从目录名提取 post_id (开头连续数字)
    """
    base = os.path.basename(dir_path.rstrip(os.sep))
    m = re.match(r'^(\d+)', base)
    if not m:
        raise ValueError(f"无法从目录名提取 post_id: {dir_path}")
    return m.group(1)

def count_local_files(dir_path):
    """
    列出目录下所有常规文件（不含子目录），
    排除 post__comments.txt 和 post__content.txt，
    返回文件名列表
    """
    try:
        names = os.listdir(dir_path)
    except Exception as e:
        raise RuntimeError(f"读取本地目录失败: {e}")
    files = []
    for fn in names:
        if fn in ("post__comments.txt", "post__content.txt"):
            continue
        full = os.path.join(dir_path, fn)
        if os.path.isfile(full):
            files.append(fn)
    return files

def fetch_attachments(api_base, post_id, timeout=20, max_retries=30, backoff=3):
    """
    调用 GET {api_base}{post_id} 并返回 post.attachments 列表。
    增加超时重试机制：遇到超时（requests.exceptions.Timeout）时，
    最多重试 max_retries 次，每次重试前等待 backoff 秒。

    参数：
      api_base    - API 基础 URL，末尾需包含 '/'
      post_id     - 要查询的帖子 ID
      timeout     - 单次请求超时时间（秒）
      max_retries - 最大重试次数（默认 30 次）
      backoff     - 每次重试前的等待时间（秒，默认 0.5）

    返回：
      attachments 列表；若字段缺失或非列表，则返回空列表。
    """
    url = urljoin(api_base, post_id)
    attempt = 0

    while attempt < max_retries:
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            post = data.get("post", {})
            atts = post.get("attachments", [])
            return atts if isinstance(atts, list) else []
        except requests.exceptions.Timeout:
            attempt += 1
            # 超时重试
            print(f"超时第 {attempt}/{max_retries} 次, retrying...")
            time.sleep(backoff)
            continue
        except requests.exceptions.RequestException as e:
            # 非超时的请求错误直接抛出
            raise RuntimeError(f"请求失败 [post_id={post_id}]: {e}")
        except ValueError as e:
            # JSON 解析错误
            raise RuntimeError(f"解析 JSON 失败 [post_id={post_id}]: {e}")

    # 如果所有重试都超时，则抛出异常
    raise RuntimeError(f"请求多次超时（{max_retries} 次）后放弃 [post_id={post_id}]")

def load_processed(json_path):
    """
    加载已处理目录列表（JSON 数组），若文件不存在返回空列表
    """
    if not os.path.isfile(json_path):
        return []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def append_processed(json_path, dir_path):
    """
    将单个目录路径追加到 processed_dirs.json 中，
    保持 JSON 数组格式，不重复写入
    """
    try:
        processed = load_processed(json_path)
        if dir_path not in processed:
            processed.append(dir_path)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"追加 processed_dirs.json 失败 [{dir_path}]: {e}")
        logging.error(traceback.format_exc())

def main():
    # 脚本目录与默认路径配置
    script_dir    = os.path.dirname(os.path.abspath(__file__))
    default_json  = os.path.join(script_dir, 'results.json')
    log_file      = os.path.join(script_dir, 'error_log.txt')
    summary_file  = os.path.join(script_dir, 'results_summary.txt')
    processed_file= os.path.join(script_dir, 'processed_dirs.json')

    # 初始化日志
    setup_logger(log_file)

    # 1. 选择模式并获取待检测目录列表
    mode = prompt_mode()
    try:
        if mode == '1':
            json_path = prompt_json_path(default_json)
            all_dirs = load_dirs_from_json(json_path)
        else:
            root_dir = prompt_root_dir(script_dir)
            all_dirs = collect_post_dirs(root_dir)
    except Exception:
        logging.error("初始化目录列表失败:\n" + traceback.format_exc())
        print("初始化失败，请查看 error_log.txt")
        sys.exit(1)

    # 2. 跳过已处理目录
    processed = set(load_processed(processed_file))
    to_test = [d for d in all_dirs if d not in processed]
    if not to_test:
        print("没有新目录需要检测，程序退出。")
        return

    # 3. 如果 summary_file 不存在，写入表头
    if not os.path.isfile(summary_file):
        with open(summary_file, 'w', encoding='utf-8') as fw:
            fw.write("目录 | post_id | attachments_count | local_count | 备注\n")
            fw.write("-" * 100 + "\n")

    # 4. API 基础 URL (末尾需 '/')
    api_base = "https://kemono.su/api/v1/patreon/user/2757009/post/" # 这个API需要自己设置

    total = len(to_test)
    # 5. 逐个检测并即时记录
    for idx, dpath in enumerate(to_test, start=1):
        print(f"[{idx}/{total}] 检测：{dpath}")
        try:
            pid       = extract_post_id(dpath)
            files     = count_local_files(dpath)
            local_cnt = len(files)
            atts      = fetch_attachments(api_base, pid)
        except Exception as e:
            logging.error(f"处理失败 [{dpath}]: {e}")
            logging.error(traceback.format_exc())
            # 无论成功与否，都标记为已处理，避免下次再检测
            append_processed(processed_file, dpath)
            continue

        att_cnt = len(atts)
        note = ""

        # 判断逻辑
        if att_cnt > local_cnt:
            note = f"attachments({att_cnt}) > 本地({local_cnt})"
        elif att_cnt < local_cnt:
            # 查看是否有 “0.*” 文件可忽略
            zero_files = [f for f in files if os.path.splitext(f)[0] == '0']
            if zero_files:
                new_cnt = local_cnt - 1
                if att_cnt == new_cnt:
                    print(f"  跳过：忽略文件'{zero_files[0]}'后匹配({att_cnt}=={new_cnt})")
                else:
                    note = f"忽略0.*后不匹配({att_cnt}!={new_cnt})"
            else:
                note = f"attachments({att_cnt}) < 本地({local_cnt})且无0.*可忽略"
        else:
            # 完全匹配，跳过记录
            print(f"  跳过：数量匹配({att_cnt}=={local_cnt})")
        
        # 若 note 不为空，说明需记录该目录
        if note:
            print(f"  ➤ post_id={pid} 异常: {note}")
            # 追加写入 summary_file
            try:
                with open(summary_file, 'a', encoding='utf-8') as fw:
                    line = f"{dpath} | {pid} | {att_cnt} | {local_cnt} | {note}\n"
                    fw.write(line)
            except Exception as e:
                logging.error(f"写入 summary 失败 [{dpath}]: {e}")
                logging.error(traceback.format_exc())

        # 完成本条检测后，立即追加到 processed_dirs.json
        append_processed(processed_file, dpath)

    print(f"\n检测完成。异常结果已保存：{summary_file}")

if __name__ == '__main__':
    main()
