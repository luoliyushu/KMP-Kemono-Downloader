#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    用途：检测指定目录及所有子目录中，文件名以 0~n 数字命名的文件是否存在连续断缺，
          同时可选记录那些根本没有纯数字文件的目录，并支持导出 TXT/JSON/CSV 格式结果。
    功能：
        1. 手动输入待检测目录，或直接回车使用脚本所在目录。
        2. 可指定要排除的文件后缀（默认不过滤任何后缀）。
        3. 遍历目录及子目录，筛选纯数字命名文件，忽略指定后缀。
        4. 可选记录“无纯数字文件”目录；检测缺号目录。
        5. 支持导出 TXT/JSON/CSV 三种格式结果，或自定义组合。
        6. 显示检测进度，并将所有异常写入 error_log.txt。
"""

import os
import sys
import json
import csv
import logging
import traceback

def setup_logger(log_path):
    """
    配置日志记录器，将错误写入指定的 error_log.txt
    """
    logging.basicConfig(
        filename=log_path,
        filemode='a',
        level=logging.ERROR,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def prompt_directory():
    """
    提示用户输入目录路径，空回车则默认脚本所在目录。
    验证路径存在且为目录，否则循环重试或退出。
    """
    base = os.path.dirname(os.path.abspath(__file__))
    while True:
        try:
            inp = input(f"请输入要检测的目录（回车使用默认：{base}）：").strip()
            target = base if not inp else os.path.abspath(os.path.expanduser(inp))
            if not os.path.exists(target):
                print(f"路径不存在：{target}")
                continue
            if not os.path.isdir(target):
                print(f"不是目录：{target}")
                continue
            return target
        except KeyboardInterrupt:
            print("\n用户取消，程序退出。")
            sys.exit(1)
        except Exception as e:
            print(f"输入异常，请重试：{e}")

def prompt_exclude_exts():
    """
    提示用户输入要排除的后缀（逗号分隔），默认不过滤任何后缀。
    返回小写、带点前缀的后缀集合。
    """
    inp = input("请输入要排除的文件后缀（逗号分隔，默认不过滤）：").strip()
    if not inp:
        return set()
    exts = set()
    for part in inp.split(','):
        ext = part.strip().lower()
        if not ext:
            continue
        if not ext.startswith('.'):
            ext = '.' + ext
        exts.add(ext)
    return exts

def prompt_record_empty():
    """
    提示是否记录没有纯数字文件的目录，默认记录（Y）。
    返回布尔值。
    """
    inp = input("是否记录没有纯数字文件的目录？(Y/n)：").strip().lower()
    return False if inp in ('n','no') else True

def prompt_output_formats():
    """
    提示用户选择输出格式：txt、json、csv（逗号分隔，默认全选）。
    返回格式集合。
    """
    choices = {'txt','json','csv'}
    inp = input("请选择输出格式(可选 txt,json,csv，逗号分隔，默认全选)：").strip().lower()
    if not inp:
        return choices
    selected = set()
    for part in inp.split(','):
        fmt = part.strip()
        if fmt in choices:
            selected.add(fmt)
    return selected or choices

def collect_all_dirs(root_dir):
    """
    遍历 root_dir，返回包含所有目录（含子目录）的列表。
    """
    dirs = []
    for cur, subs, files in os.walk(root_dir):
        dirs.append(cur)
    return dirs

def find_numeric_files(dir_path, exclude_exts):
    """
    列出 dir_path 下所有纯数字命名文件的编号列表，忽略 exclude_exts 中的后缀。
    返回编号列表（int）。
    """
    nums = []
    try:
        for fname in os.listdir(dir_path):
            name, ext = os.path.splitext(fname)
            if ext.lower() in exclude_exts:
                continue
            if name.isdigit():
                nums.append(int(name))
    except Exception as e:
        raise RuntimeError(f"读取目录列表失败: {e}")
    return nums

def write_txt(missing_dirs, empty_dirs, script_dir, record_empty):
    """
    将 missing_dirs 和 empty_dirs 写入同目录下的 TXT 文件。
    """
    miss_file = os.path.join(script_dir, 'missing_dirs.txt')
    with open(miss_file, 'w', encoding='utf-8') as f:
        f.write("存在断连的目录：\n")
        for d in missing_dirs:
            f.write(d + "\n")
    print(f"TXT 缺号目录已保存：{miss_file}")

    if record_empty:
        empty_file = os.path.join(script_dir, 'empty_dirs.txt')
        with open(empty_file, 'w', encoding='utf-8') as f:
            f.write("无纯数字文件的目录：\n")
            for d in empty_dirs:
                f.write(d + "\n")
        print(f"TXT 空目录已保存：{empty_file}")

def write_json(missing_dirs, empty_dirs, script_dir, record_empty):
    """
    将结果写入 JSON 文件。
    """
    data = {
        "missing_dirs": missing_dirs
    }
    if record_empty:
        data["empty_dirs"] = empty_dirs
    json_file = os.path.join(script_dir, 'results.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON 结果已保存：{json_file}")

def write_csv(missing_dirs, empty_dirs, script_dir, record_empty):
    """
    将结果写入单个 CSV 文件，包含目录与类型两列。
    """
    csv_file = os.path.join(script_dir, 'results.csv')
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["directory", "status"])
        for d in missing_dirs:
            writer.writerow([d, "missing"])
        if record_empty:
            for d in empty_dirs:
                writer.writerow([d, "empty"])
    print(f"CSV 结果已保存：{csv_file}")

def main():
    # 脚本目录，用于存放日志和结果
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, 'error_log.txt')
    setup_logger(log_file)

    # 1. 获取用户输入
    root = prompt_directory()
    exclude_exts = prompt_exclude_exts()
    record_empty = prompt_record_empty()
    out_formats = prompt_output_formats()
    print(f"\n开始检测：\n  根目录：{root}\n  排除后缀：{sorted(exclude_exts)}\n"
          f"  记录空目录：{record_empty}\n  输出格式：{sorted(out_formats)}\n")

    try:
        all_dirs = collect_all_dirs(root)
        total = len(all_dirs)
        missing_dirs = []
        empty_dirs = []

        # 遍历所有目录
        for idx, d in enumerate(all_dirs, start=1):
            print(f"[{idx}/{total}] {d}")
            try:
                nums = find_numeric_files(d, exclude_exts)
                if not nums:
                    if record_empty:
                        empty_dirs.append(d)
                    continue
                max_num = max(nums)
                full_set = set(range(max_num + 1))
                missing = sorted(full_set - set(nums))
                if missing:
                    missing_dirs.append(d)
            except Exception as e:
                logging.error(f"检测目录出错 [{d}]: {e}")
                logging.error(traceback.format_exc())

        # 根据用户选择导出结果
        if 'txt' in out_formats:
            write_txt(missing_dirs, empty_dirs, script_dir, record_empty)
        if 'json' in out_formats:
            write_json(missing_dirs, empty_dirs, script_dir, record_empty)
        if 'csv' in out_formats:
            write_csv(missing_dirs, empty_dirs, script_dir, record_empty)

        print("\n检测完成。")

    except Exception as e:
        logging.error(f"程序运行出错: {e}")
        logging.error(traceback.format_exc())
        print("发生严重错误，请查看 error_log.txt")

if __name__ == '__main__':
    main()
