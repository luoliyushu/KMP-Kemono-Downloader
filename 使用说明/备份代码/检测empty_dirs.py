#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：
    检测 Post 目录下本地文件数与接口返回的 post.attachments 数量：
      - 当 attachments 数量 > 本地文件数 时，记录该目录。
      - 当 attachments 数量 < 本地文件数 时：
          1. 检查是否存在名为 0.[任意后缀] 的文件，若存在则忽略它再比较；
          2. 若忽略后仍不相等，则记录该目录；否则跳过。
      - 当 attachments 数量 == 本地文件数 时，跳过不记录。
    支持两种模式：
      1. 从 JSON 文件读取目录列表（JSON 格式需含 "empty_dirs" 字段）
      2. 手动输入根目录，递归查找以数字开头的子目录
    将异常写入 error_log.txt，将不正常目录汇总到 results_summary.txt。

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

# 检查 requests 库
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
    提示用户选择运行模式：
      1 - 从 JSON 文件读取目录列表
      2 - 手动输入根目录路径（递归收集子目录）
    默认回车或输入 1 为 JSON 模式
    """
    while True:
        mode = input("请选择模式(1=JSON文件,2=根目录模式)[默认1]: ").strip()
        if mode in ('', '1', '2'):
            return '1' if mode in ('', '1') else '2'
        print("输入不合法，请输入 1 或 2。")

def prompt_json_path(default):
    """
    提示用户输入 JSON 文件路径，回车使用默认
    """
    while True:
        path = input(f"请输入 JSON 文件路径（回车默认：{default}）：").strip()
        if not path:
            path = default
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isfile(path):
            return path
        print(f"无效路径或非文件：{path}")

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
    提示用户输入根目录，回车使用默认
    """
    while True:
        path = input(f"请输入根目录路径（回车默认：{default}）：").strip()
        if not path:
            path = default
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(path):
            return path
        print(f"无效目录：{path}")

def collect_post_dirs(root_dir):
    """
    遍历 root_dir，收集所有目录名以数字开头的子目录
    """
    result = []
    for cur, _, _ in os.walk(root_dir):
        name = os.path.basename(cur.rstrip(os.sep))
        if re.match(r'^\d+', name):
            result.append(cur)
    return result

def extract_post_id(dir_path):
    """
    从目录名提取 post_id（开头数字序列）
    """
    name = os.path.basename(dir_path.rstrip(os.sep))
    m = re.match(r'^(\d+)', name)
    if not m:
        raise ValueError(f"无法提取 post_id：{dir_path}")
    return m.group(1)

def count_local_files(dir_path):
    """
    统计目录下文件数，排除 post__comments.txt 和 post__content.txt
    返回文件名列表，用于后续忽略 0.* 文件
    """
    try:
        names = os.listdir(dir_path)
    except Exception as e:
        raise RuntimeError(f"列出本地文件失败：{e}")
    files = []
    for fn in names:
        # 跳过指定 txt
        if fn in ("post__comments.txt", "post__content.txt"):
            continue
        full = os.path.join(dir_path, fn)
        if os.path.isfile(full):
            files.append(fn)
    return files

def fetch_attachments(api_base, post_id, timeout=10):
    """
    调用 API 获取 post.attachments 列表，若缺失或非列表返回空列表
    """
    url = urljoin(api_base, post_id)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    obj = resp.json()
    post = obj.get("post", {})
    atts = post.get("attachments", [])
    return atts if isinstance(atts, list) else []

def main():
    # 脚本目录与默认文件路径
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    default_json = os.path.join(script_dir, 'results.json')
    log_file     = os.path.join(script_dir, 'error_log.txt')
    summary_file = os.path.join(script_dir, 'results_summary.txt')

    setup_logger(log_file)

    # 1. 选择模式并获取待检测目录列表
    mode = prompt_mode()
    try:
        if mode == '1':
            json_path = prompt_json_path(default_json)
            dirs = load_dirs_from_json(json_path)
        else:
            root = prompt_root_dir(script_dir)
            dirs = collect_post_dirs(root)
    except Exception:
        logging.error(traceback.format_exc())
        print("初始化目录列表失败，请查看 error_log.txt")
        sys.exit(1)

    # 2. 配置 API 地址（末尾需 '/')
    api_base = "https://xxxxxx.xx/api/v1/xxxxxxx/user/xxxxxxx/post/"

    total = len(dirs)
    records = []

    # 3. 遍历每个目录，比较 attachments_count 与 local_count
    for idx, dpath in enumerate(dirs, start=1):
        print(f"[{idx}/{total}] 处理：{dpath}")
        try:
            pid   = extract_post_id(dpath)
            files = count_local_files(dpath)
            local_cnt = len(files)
            atts = fetch_attachments(api_base, pid)
        except Exception as e:
            logging.error(f"处理失败 [{dpath}]: {e}")
            logging.error(traceback.format_exc())
            continue

        att_cnt = len(atts)

        # Case 1: attachments > 本地文件数，记录
        if att_cnt > local_cnt:
            reason = "attachments数大于本地文件数"
            print(f"  ➤ post_id={pid} {reason}({att_cnt} > {local_cnt})，记录")
            records.append((dpath, pid, att_cnt, local_cnt, reason))
            continue

        # Case 2: attachments < 本地文件数，尝试忽略 0.* 再比较
        if att_cnt < local_cnt:
            # 找到名为 "0.*" 的文件
            zero_files = [f for f in files if os.path.splitext(f)[0] == '0']
            if zero_files:
                # 忽略一个 0.* 文件
                new_local_cnt = local_cnt - 1
                if att_cnt == new_local_cnt:
                    print(f"  跳过：post_id={pid} 忽略 '{zero_files[0]}' 后数目匹配({att_cnt} == {new_local_cnt})")
                    continue
                else:
                    reason = f"忽略0.*后不匹配({att_cnt} != {new_local_cnt})"
            else:
                reason = f"attachments数小于本地文件数且无0.*可忽略({att_cnt} < {local_cnt})"
            print(f"  ➤ post_id={pid} {reason}，记录")
            records.append((dpath, pid, att_cnt, local_cnt, reason))
            continue

        # Case 3: attachments == 本地文件数，正常跳过
        print(f"  跳过：post_id={pid} 数量匹配({att_cnt} == {local_cnt})")

    # 4. 写入 summary
    if records:
        try:
            with open(summary_file, 'w', encoding='utf-8') as fw:
                fw.write("目录 | post_id | attachments_count | local_count | 备注\n")
                fw.write("-" * 100 + "\n")
                for dpath, pid, ac, lc, note in records:
                    fw.write(f"{dpath} | {pid} | {ac} | {lc} | {note}\n")
            print(f"\n检测完成，结果已保存：{summary_file}")
        except Exception as e:
            logging.error(f"写入汇总失败：{e}")
            logging.error(traceback.format_exc())
            print("写入汇总文件出错，请查看 error_log.txt")
    else:
        print("\n所有目录均正常，无需生成结果文件。")

if __name__ == '__main__':
    main()
