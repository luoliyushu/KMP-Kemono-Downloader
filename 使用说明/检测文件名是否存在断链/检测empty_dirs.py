#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：
    读取同级目录下 empty_dirs.json 中的“空目录”列表，
    从每个目录路径中提取 post_id（目录名开头的数字），
    调用外部接口检查该帖子的 attachments 字段，
    如果 attachments 非空，则打印并记录到 results_has_attachments.txt。
    全程捕获异常并写入 error_log.txt。

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

# 导入 requests 库
try:
    import requests
except ImportError:
    print("缺少 requests 库，请先运行：pip install requests")
    sys.exit(1)


def setup_logger(log_path):
    """
    配置日志记录器，将 ERROR 及以上级别的日志写入 log_path
    """
    logging.basicConfig(
        filename=log_path,
        filemode='a',                      # 追加写入
        level=logging.ERROR,               # 记录 ERROR 及以上级别
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_empty_dirs(json_path):
    """
    加载 empty_dirs.json，返回目录路径列表
    期望文件内容是 JSON 数组，如：
    [
      "F:/.../114109563 Post ...",
      "F:/.../125279098 Post ..."
    ]
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("empty_dirs.json 内容应为 JSON 数组")
        return data
    except Exception as e:
        raise RuntimeError(f"加载 JSON 文件失败：{e}")


def extract_post_id(dir_path):
    """
    从目录路径提取 post_id，规则：basename 开头连续数字
    例：".../114109563 Post ..." -> "114109563"
    """
    base = os.path.basename(dir_path.rstrip(os.sep))
    m = re.match(r'^(\d+)', base)
    if not m:
        raise ValueError(f"无法从路径中提取 post_id: {dir_path}")
    return m.group(1)


def check_attachments(api_base, post_id, timeout=10):
    """
    调用接口 GET {api_base}{post_id}，
    返回 True 如果 post.attachments 非空，否则 False。
    """
    url = urljoin(api_base, post_id)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()  # 若非 200 会抛异常
    data = resp.json()
    # 获取 attachments 字段
    post = data.get("post", {})
    attachments = post.get("attachments", None)
    # 非空列表、非空 dict 都视为有附件
    return bool(attachments)


def main():
    # 脚本所在目录，用于定位配置、日志和输出文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file   = os.path.join(script_dir, 'empty_dirs.json')
    log_file    = os.path.join(script_dir, 'error_log.txt')
    result_file = os.path.join(script_dir, 'results_has_attachments.txt')

    setup_logger(log_file)

    # 1. 读取 empty_dirs.json
    try:
        dirs = load_empty_dirs(json_file)
    except Exception as e:
        logging.error(traceback.format_exc())
        print(f"加载 empty_dirs.json 失败，请检查文件格式，详情见 error_log.txt")
        sys.exit(1)

    # 2. 配置 API 基础 URL（请根据实际情况修改，末尾需带斜杠 '/')
    api_base = "https://kemono.su/api/v1/patreon/user/2757009/post/"

    total = len(dirs)
    matched_dirs = []

    # 3. 遍历目录列表，逐个检查 attachments
    for idx, dpath in enumerate(dirs, start=1):
        print(f"[{idx}/{total}] 检测：{dpath}")
        try:
            post_id = extract_post_id(dpath)
        except Exception as e:
            logging.error(f"提取 post_id 失败 [{dpath}]: {e}")
            continue

        try:
            has_att = check_attachments(api_base, post_id)
        except Exception as e:
            logging.error(f"接口调用失败 [post_id={post_id}]: {e}")
            logging.error(traceback.format_exc())
            continue

        if has_att:
            print(f"  ➤ post_id={post_id} 的 attachments 非空")
            matched_dirs.append(dpath)

    # 4. 将检测到 attachments 非空的目录写入结果文件
    try:
        with open(result_file, 'w', encoding='utf-8') as fw:
            fw.write("附件非空的目录列表：\n")
            for p in matched_dirs:
                fw.write(p + "\n")
        print(f"\n检测完成，结果已保存到：{result_file}")
    except Exception as e:
        logging.error(f"写入结果文件失败：{e}")
        logging.error(traceback.format_exc())
        print("写入结果文件出错，请查看 error_log.txt")


if __name__ == '__main__':
    main()
