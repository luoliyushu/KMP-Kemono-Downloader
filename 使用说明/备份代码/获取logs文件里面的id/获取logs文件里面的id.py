#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用途：
    从指定的日志文本文件中逐行读取内容，使用正则表达式提取目录路径里的 post_id，
    如“78257449”、“78078138” 等数字编号，并去重后打印和保存到同级的 ids.txt 文件中。

功能：
    1. 手动输入日志文件路径，回车使用默认同级的 logs.txt。
    2. 匹配模式：反斜杠“\”后面紧跟一串数字，接着空格和“Post”关键词。
    3. 去重并保持原始匹配顺序输出。
    4. 捕获并记录所有运行时错误到同级的 error_log.txt。

依赖：
    标准库，无需额外安装，适用于 Python3.7+。
"""

import os
import re
import sys
import logging
import traceback

def setup_logger(log_path):
    """
    配置日志记录，将 ERROR 及以上级别写入 error_log.txt
    """
    logging.basicConfig(
        filename=log_path,
        filemode='a',               # 追加模式
        level=logging.ERROR,        # 记录 ERROR 及以上
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def prompt_log_file():
    """
    提示用户输入日志文本文件路径。回车则使用脚本同级的 logs.txt。
    验证文件存在且为可读文件，否则重试或退出。
    """
    base = os.path.dirname(os.path.abspath(__file__))
    default = os.path.join(base, 'logs.txt')
    while True:
        try:
            inp = input(f"请输入日志文件路径（回车使用默认：{default}）：").strip()
            path = default if not inp else os.path.abspath(os.path.expanduser(inp))
            if not os.path.exists(path):
                print(f"文件不存在：{path}")
                continue
            if not os.path.isfile(path):
                print(f"不是文件：{path}")
                continue
            return path
        except KeyboardInterrupt:
            print("\n用户取消，程序退出。")
            sys.exit(1)
        except Exception as e:
            print(f"路径输入异常，请重试：{e}")

def extract_ids_from_file(file_path, pattern):
    """
    从 file_path 文件中逐行读取，并使用 pattern 正则提取所有匹配的 post_id。
    返回按出现顺序去重后的 ID 列表（字符串）。
    """
    ids = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, start=1):
                match = pattern.search(line)
                if match:
                    ids.append(match.group(1))
    except Exception as e:
        raise RuntimeError(f"读取或处理文件失败: {e}")
    # 去重并保留原始顺序
    # dict.fromkeys 会保留插入顺序，从 Python3.7+ 确保有序
    unique_ids = list(dict.fromkeys(ids))
    return unique_ids

def main():
    # 脚本所在目录，用于存放日志和输出
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file    = os.path.join(script_dir, 'error_log.txt')
    result_file = os.path.join(script_dir, 'ids.txt')

    setup_logger(log_file)

    # 1. 获取日志文件路径
    log_path = prompt_log_file()

    # 2. 编译正则：匹配 "\<数字>  Post"
    #    r"\\(\d+)\s+Post" —— 反斜杠要转义成 "\\"
    pattern = re.compile(r"\\(\d+)\s+Post")

    # 3. 提取 ID
    try:
        ids = extract_ids_from_file(log_path, pattern)
    except Exception as e:
        logging.error(traceback.format_exc())
        print(f"提取 ID 失败，详情请查看 error_log.txt")
        sys.exit(1)

    # 4. 打印并写入结果
    if not ids:
        print("未从日志中匹配到任何 post_id。")
    else:
        print("提取到以下 post_id：")
        for pid in ids:
            print(f"  - {base_url + pid}")
        try:
            with open(result_file, 'w', encoding='utf-8') as fw:
                fw.write("提取的 post_id 列表：\n")
                for pid in ids:
                    fw.write(base_url + pid + "\n")
            print(f"\n已将结果保存到：{result_file}")
        except Exception as e:
            logging.error(traceback.format_exc())
            print("写入结果文件出错，请查看 error_log.txt")

if __name__ == '__main__':
    base_url = "https://kemono.su/patreon/user/2757009/post/"
    main()
