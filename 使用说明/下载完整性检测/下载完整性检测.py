#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：
    检测 Post 目录本地文件数 与 接口返回的
      post.attachments + post.file + post.content 中<img>标签数量
    合并后的数量 是否异常：
      - 接口资源总数 > 本地文件数 → 记录异常
      - 接口资源总数 < 本地文件数 → 忽略“0.*”文件后再比，仍不匹配则记录异常
      - 接口资源总数 == 本地文件数 → 跳过
    支持两种模式：
      1. 手动模式：输入根目录和 api_base
      2. 自动模式：从 JSON 读取 RECORDS 并自动派生根目录与 api_base
    可选功能：
      - 是否对 post.attachments + post.file 结果去重（默认不去重）
    检测完成一个目录后写入 processed_dirs.json；出错不写，下次继续重试
    异常目录汇总到 results_summary.txt（追加）；异常页面 URL 列表追加到 exception_urls.txt
    错误日志写入 error_log.txt。

依赖：
    requests 库（pip install requests）
"""

import os
import sys
import json
import re
import logging
import traceback
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# 检查并导入 requests 库
try:
    import requests
except ImportError:
    print("缺少 requests 库，请先运行：pip install requests")
    sys.exit(1)

# 全局请求头，模拟浏览器以防被服务端拒绝
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
}

def setup_logger(log_path):
    """
    配置日志：ERROR 及以上级别追加写入 log_path
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
    提示运行模式：1=手动；2=自动（默认1）
    """
    while True:
        m = input("请选择模式 (1=手动; 2=自动)【默认1】：").strip()
        if m in ('', '1', '2'):
            return '1' if m in ('', '1') else '2'
        print("请输入 1 或 2。")

def prompt_dedup_option():
    """
    提示是否启用去重（post.attachments + post.file）
    默认不去重，输入 y 则启用
    """
    while True:
        d = input("是否启用去重(post.attachments 与 post.file)? (y/N)【N】：").strip().lower()
        if d in ('y', 'n', ''):
            return d == 'y'
        print("请输入 y 或 n。")

def prompt_manual_inputs():
    """
    手动模式：
      1. 输入根目录 root_dir
      2. 输入 api_base（必须以 '/' 结尾）
    """
    while True:
        rd = input("请输入根目录路径：").strip()
        if os.path.isdir(rd):
            root_dir = os.path.abspath(rd)
            break
        print(f"无效目录：{rd}")
    while True:
        ab = input("请输入 api_base（末尾需 '/'）：").strip()
        if ab.endswith('/'):
            api_base = ab
            break
        print("api_base 必须以 '/' 结尾。")
    return root_dir, api_base

def prompt_json_path(default):
    """
    自动模式：提示 JSON 文件路径，回车使用默认
    """
    while True:
        p = input(f"请输入 JSON 文件路径（回车默认：{default}）：").strip()
        if not p:
            p = default
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isfile(p):
            return p
        print(f"无效文件：{p}")

def load_records_from_json(json_path):
    """
    从 JSON 文件读取 "RECORDS" 列表
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        recs = data.get("RECORDS")
        if not isinstance(recs, list):
            raise ValueError('"RECORDS" 字段缺失或非列表')
        return recs
    except Exception as e:
        raise RuntimeError(f"加载 JSON 失败：{e}")

def derive_api_base(user_url):
    """
    根据用户页 URL 派生 api_base
      示例：
        输入  : https://kemono.party/fanbox/user/12345
        输出  : https://kemono.su/api/v1/fanbox/user/12345/post/
    """
    parsed = urlparse(user_url)
    scheme = parsed.scheme or 'https'
    path = parsed.path.rstrip('/')
    return f"{scheme}://kemono.su/api/v1{path}/post/"

def api_to_page_url(api_base, post_id):
    """
    将 API URL 转为页面 URL
      去掉 '/api/v1' 前缀，再拼 post_id
    """
    parsed = urlparse(api_base)
    scheme, netloc, path = parsed.scheme, parsed.netloc, parsed.path
    if path.startswith('/api/v1'):
        page_path = path[len('/api/v1'):]
    else:
        page_path = path
    if not page_path.endswith('/'):
        page_path += '/'
    return f"{scheme}://{netloc}{page_path}{post_id}"

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
    从目录名开头提取 post_id（连续数字）
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

def fetch_resources(api_base, post_id, dedup=False, timeout=20, max_retries=30, backoff=3):
    """
    获取接口返回的 post.file、post.attachments 以及 post.content 中 <img> 标签数量
      - GET {api_base}{post_id}
      - 请求头包含 HEADERS
      - 对请求失败或 JSON 解析失败进行重试，重试 max_retries 次
      - 合并 post.file（单个）与 post.attachments（列表）返回路径列表
      - 解析 post.content 字段，统计 <img> 标签个数
      - 如果 dedup=True，则对合并的路径列表去重
    返回：
      tuple(merged_paths_list, img_tag_count)
    """
    url = urljoin(api_base, post_id)
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()

            # 1. 收集 post.file
            merged = []
            file_obj = data.get("post", {}).get("file")
            if isinstance(file_obj, dict):
                p = file_obj.get("path")
                if p:
                    merged.append(p)

            # 2. 收集 post.attachments
            for att in data.get("post", {}).get("attachments", []) or []:
                p = att.get("path")
                if p:
                    merged.append(p)

            # 3. 如需去重，则仅保留首次出现的路径
            if dedup:
                seen = set()
                unique = []
                for p in merged:
                    if p not in seen:
                        seen.add(p)
                        unique.append(p)
                merged = unique

            # 4. 解析 post.content，统计 <img> 标签数量
            img_count = 0
            try:
                content_html = data.get("post", {}).get("content", "")
                # 用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(content_html, 'html.parser')
                img_tags = soup.find_all('img')
                img_count = len(img_tags)
            except Exception:
                # 解析过程若出错，不终止，img_count 保持 0
                logging.warning(f"解析 post.content 时出错，忽略 content 图片统计 [post_id={post_id}]")

            return merged, img_count

        except (requests.exceptions.RequestException, ValueError) as e:
            # 包括超时、HTTP错误和 JSON 解析错误，均重试
            if attempt < max_retries:
                print(f"  请求/解析失败: {e}，重试 {attempt}/{max_retries}...")
                time.sleep(backoff)
                continue
            # 超过重试次数后抛出
            raise RuntimeError(f"重试 {max_retries} 次仍失败 [post_id={post_id}]: {e}")

    # 理论上不会到达这里
    raise RuntimeError(f"无法获取资源 [post_id={post_id}]")

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
    将已成功检测目录追加到 processed_dirs.json，保持唯一
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
    # 脚本目录 & 默认路径
    script_dir     = os.path.dirname(os.path.abspath(__file__))
    default_json   = os.path.join(script_dir, 'records.json')
    log_file       = os.path.join(script_dir, 'error_log.txt')
    summary_file   = os.path.join(script_dir, 'results_summary.txt')
    processed_file = os.path.join(script_dir, 'processed_dirs.json')
    exception_file = os.path.join(script_dir, 'exception_urls.txt')

    # 配置错误日志
    setup_logger(log_file)

    # 选择模式 & 去重选项
    mode  = prompt_mode()
    dedup = prompt_dedup_option()

    # 根据模式收集待检测目录列表 (目录路径, api_base)
    to_test = []
    if mode == '1':  # 手动模式
        root_dir, api_base = prompt_manual_inputs()
        dirs = collect_post_dirs(root_dir)
        to_test = [(d, api_base) for d in dirs]
    else:             # 自动模式
        json_path = prompt_json_path(default_json)
        try:
            records = load_records_from_json(json_path)
        except Exception:
            logging.error(traceback.format_exc())
            print("加载 RECORDS 失败，请查看 error_log.txt")
            sys.exit(1)

        # 逐条记录生成 (目录, api_base)
        for rec in records:
            try:
                user_url    = rec['url']
                artist      = rec['artist']
                destination = rec['destination']
                api_base    = derive_api_base(user_url)
                root_dir    = os.path.join(destination, artist)
                dirs        = collect_post_dirs(root_dir)
                to_test.extend((d, api_base) for d in dirs)
            except Exception as e:
                logging.error(f"自动模式处理记录失败 [{rec}]: {e}")
                logging.error(traceback.format_exc())

    # 过滤已处理目录
    processed = set(load_processed(processed_file))
    to_test = [(d, a) for d, a in to_test if d not in processed]

    if not to_test:
        print("没有新目录需要检测，程序退出。")
        return

    # 初始化 results_summary.txt（若不存在则写表头）
    if not os.path.isfile(summary_file):
        with open(summary_file, 'w', encoding='utf-8') as fw:
            fw.write("目录 | post_id | 接口资源数 | 本地文件数 | 备注\n")
            fw.write("-" * 100 + "\n")
    # 初始化 exception_urls.txt（若不存在创建空文件；存在保留内容，不清空）
    if not os.path.isfile(exception_file):
        open(exception_file, 'w', encoding='utf-8').close()

    total = len(to_test)

    # 逐个检测
    for idx, (dpath, api_base) in enumerate(to_test, start=1):
        print(f"[{idx}/{total}] 检测：{dpath}")
        try:
            pid         = extract_post_id(dpath)
            files       = count_local_files(dpath)
            local_cnt   = len(files)

            # 获取 attachments+file 列表 & content 中 img 标签数量
            resources, img_count = fetch_resources(api_base, pid, dedup=dedup)
            # 总资源数 = 附件数 + 文本内容 img 数
            res_cnt = len(resources) + img_count

            note = ""
            if res_cnt > local_cnt:
                note = f"接口({res_cnt}) > 本地({local_cnt})"
            elif res_cnt < local_cnt:
                zero_files = [f for f in files if os.path.splitext(f)[0] == '0']
                if zero_files:
                    new_cnt = local_cnt - 1
                    if res_cnt == new_cnt:
                        print(f"  跳过：忽略'{zero_files[0]}'后匹配({res_cnt}=={new_cnt})")
                    else:
                        note = f"忽略0.*后不匹配({res_cnt}!={new_cnt})"
                else:
                    note = f"接口({res_cnt}) < 本地({local_cnt})且无0.*可忽略"
            else:
                print(f"  跳过：数量匹配({res_cnt}=={local_cnt})")

            if note:
                page_url = api_to_page_url(api_base, pid)
                print(f"  ➤ 异常: {note}，记录 页面URL：{page_url}")

                # 写入 summary（追加）
                try:
                    with open(summary_file, 'a', encoding='utf-8') as fw:
                        fw.write(f"{dpath} | {pid} | {res_cnt} | {local_cnt} | {note}\n")
                except Exception as e:
                    logging.error(f"写入 {summary_file} 失败 [{dpath}]: {e}")
                    logging.error(traceback.format_exc())

                # 写入异常页面 URL（追加）
                try:
                    with open(exception_file, 'a', encoding='utf-8') as ef:
                        ef.write(page_url + "\n")
                except Exception as e:
                    logging.error(f"写入 {exception_file} 失败 [{page_url}]: {e}")
                    logging.error(traceback.format_exc())

            # 成功检测后标记 processed
            append_processed(processed_file, dpath)

        except Exception as e:
            # 处理目录过程中出错，不标记 processed，下次重试
            logging.error(f"处理失败 [{dpath}]: {e}")
            logging.error(traceback.format_exc())
            print(f"  错误: {e}，此目录保留，下次重试。")

    print(f"\n检测完成。异常结果已追加到：{summary_file}")
    print(f"异常页面 URL 已追加到：{exception_file}")

if __name__ == '__main__':
    main()
