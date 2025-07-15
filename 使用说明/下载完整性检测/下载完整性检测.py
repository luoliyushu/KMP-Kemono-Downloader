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
    每检测完一个目录即刻写入 processed_dirs.json，下次运行跳过
    异常目录汇总到 results_summary.txt，异常 URL 列表写入 exception_urls.txt，
    所有错误写入 error_log.txt。

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
    配置日志记录器，将 ERROR 及以上级别日志追加写入 log_path
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
    提示运行模式：
      1. 从 JSON 文件读取目录列表（默认）
      2. 手动输入根目录，递归收集子目录
    """
    while True:
        m = input("请选择模式 (1=JSON 文件; 2=手动目录)【默认1】：").strip()
        if m in ('', '1', '2'):
            return '1' if m in ('', '1') else '2'
        print("请输入 1 或 2。")

def prompt_json_path(default):
    """
    提示 JSON 文件路径，回车使用默认
    """
    while True:
        p = input(f"请输入 JSON 文件路径（回车默认：{default}）：").strip()
        if not p:
            p = default
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isfile(p):
            return p
        print(f"无效文件：{p}")

def load_dirs_from_json(json_path):
    """
    从 JSON 文件读取 "empty_dirs" 列表
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        dirs = data.get("empty_dirs")
        if not isinstance(dirs, list):
            raise ValueError('"empty_dirs" 字段缺失或非列表')
        return dirs
    except Exception as e:
        raise RuntimeError(f"加载 JSON 失败：{e}")

def prompt_root_dir(default):
    """
    提示根目录路径，回车使用默认
    """
    while True:
        p = input(f"请输入根目录路径（回车默认：{default}）：").strip()
        if not p:
            p = default
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(p):
            return p
        print(f"无效目录：{p}")

def collect_post_dirs(root_dir):
    """
    递归遍历 root_dir，收集所有目录名以数字开头的子目录
    """
    result = []
    for cur, _, _ in os.walk(root_dir):
        name = os.path.basename(cur.rstrip(os.sep))
        if re.match(r'^\d+', name):
            result.append(cur)
    return result

def extract_post_id(dir_path):
    """
    从目录路径中提取 post_id：basename 开头连续数字
    """
    base = os.path.basename(dir_path.rstrip(os.sep))
    m = re.match(r'^(\d+)', base)
    if not m:
        raise ValueError(f"无法提取 post_id: {dir_path}")
    return m.group(1)

def count_local_files(dir_path):
    """
    列出目录下所有常规文件，排除 post__comments.txt 和 post__content.txt
    返回文件名列表
    """
    try:
        names = os.listdir(dir_path)
    except Exception as e:
        raise RuntimeError(f"读取目录失败: {e}")
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
    GET {api_base}{post_id} 并返回 post.attachments 列表
    超时重试 max_retries 次，每次等待 backoff 秒
    """
    url = urljoin(api_base, post_id)
    for attempt in range(1, max_retries+1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            atts = data.get("post", {}).get("attachments", [])
            return atts if isinstance(atts, list) else []
        except requests.exceptions.Timeout:
            print(f"  超时重试 {attempt}/{max_retries} ...")
            time.sleep(backoff)
            continue
        except requests.exceptions.RequestException as e:
            # 非超时的请求错误直接抛出
            raise RuntimeError(f"请求失败 [post_id={post_id}]: {e}")
        except ValueError as e:
            raise RuntimeError(f"JSON 解析失败 [post_id={post_id}]: {e}")
    raise RuntimeError(f"重试 {max_retries} 次超时，放弃 [post_id={post_id}]")

def load_processed(json_path):
    """
    加载已处理目录列表（JSON 数组），不存在返回空列表
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
    追加单个目录到 processed_dirs.json，保持唯一
    """
    try:
        procs = load_processed(json_path)
        if dir_path not in procs:
            procs.append(dir_path)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(procs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"追加 processed_dirs.json 失败 [{dir_path}]: {e}")
        logging.error(traceback.format_exc())

def main():
    # 基础路径配置
    script_dir     = os.path.dirname(os.path.abspath(__file__))
    default_json   = os.path.join(script_dir, 'results.json')
    log_file       = os.path.join(script_dir, 'error_log.txt')
    summary_file   = os.path.join(script_dir, 'results_summary.txt')
    processed_file = os.path.join(script_dir, 'processed_dirs.json')
    exception_file = os.path.join(script_dir, 'exception_urls.txt')

    setup_logger(log_file)

    # 选择模式并获取目录列表
    mode = prompt_mode()
    try:
        if mode == '1':
            json_path = prompt_json_path(default_json)
            all_dirs = load_dirs_from_json(json_path)
        else:
            root_dir = prompt_root_dir(script_dir)
            all_dirs = collect_post_dirs(root_dir)
    except Exception:
        logging.error(traceback.format_exc())
        print("初始化目录列表失败，请查看 error_log.txt")
        sys.exit(1)

    # 过滤已处理目录
    processed = set(load_processed(processed_file))
    to_test = [d for d in all_dirs if d not in processed]
    if not to_test:
        print("没有新目录需要检测，程序退出。")
        return

    # 初始化 summary 与 exception 文件
    if not os.path.isfile(summary_file):
        with open(summary_file, 'w', encoding='utf-8') as fw:
            fw.write("目录 | post_id | attachments_count | local_count | 备注\n")
            fw.write("-" * 100 + "\n")
    # 清空或创建 exception_urls.txt
    open(exception_file, 'w', encoding='utf-8').close()

    # API 基础 URL（末尾需 '/')
    api_base = "https://xxxxxx.xx/api/v1/xxxxxxx/user/xxxxxxx/post/"

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

        # 判断条件
        if att_cnt > local_cnt:
            note = f"attachments({att_cnt}) > 本地({local_cnt})"
        elif att_cnt < local_cnt:
            # 查看是否有 “0.*” 文件可忽略
            zero_files = [f for f in files if os.path.splitext(f)[0] == '0']
            if zero_files:
                new_cnt = local_cnt - 1
                if att_cnt == new_cnt:
                    print(f"  跳过：忽略'{zero_files[0]}'后匹配({att_cnt}=={new_cnt})")
                else:
                    note = f"忽略0.*后不匹配({att_cnt}!={new_cnt})"
            else:
                note = f"attachments({att_cnt}) < 本地({local_cnt})且无0.*可忽略"
        else:
            # 完全匹配，跳过记录
            print(f"  跳过：数量匹配({att_cnt}=={local_cnt})")

        # 若异常则记录 summary + exception URL
        if note:
            full_url = api_base + pid
            print(f"  ➤ 异常: {note}，记录 URL：{full_url}")
            # 写入汇总结果
            try:
                with open(summary_file, 'a', encoding='utf-8') as fw:
                    fw.write(f"{dpath} | {pid} | {att_cnt} | {local_cnt} | {note}\n")
            except Exception as e:
                logging.error(f"写入 summary 失败 [{dpath}]: {e}")
                logging.error(traceback.format_exc())
            # 写入 Exception URL
            try:
                with open(exception_file, 'a', encoding='utf-8') as ef:
                    ef.write(full_url + "\n")
            except Exception as e:
                logging.error(f"写入 exception_urls.txt 失败 [{full_url}]: {e}")
                logging.error(traceback.format_exc())

        # 标记已处理
        append_processed(processed_file, dpath)

    print(f"\n检测完成。异常结果已保存：{summary_file}")
    print(f"异常 URL 已保存：{exception_file}")

if __name__ == '__main__':
    main()
