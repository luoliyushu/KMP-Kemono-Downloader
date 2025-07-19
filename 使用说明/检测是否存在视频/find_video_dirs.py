#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re

def find_video_dirs(root_dir, video_exts):
    """
    遍历 root_dir，返回所有包含视频文件的目录列表
    """
    video_dirs = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in video_exts:
                video_dirs.append(dirpath)
                break
    return list(set(video_dirs))

def get_numeric_prefix(name):
    """
    如果 name 以数字开头，提取连续的数字作为整数返回；否则返回 None
    """
    m = re.match(r'^(\d+)', name)
    return int(m.group(1)) if m else None

def sort_dirs_with_numeric_prefix(dirs):
    """
    将以数字开头的目录按数字从小到大排序，
    非数字开头的目录保持在后，且顺序不变
    """
    digit_list = []
    other_list = []
    for d in dirs:
        prefix = get_numeric_prefix(os.path.basename(d))
        if prefix is not None:
            digit_list.append((d, prefix))
        else:
            other_list.append(d)

    # 按数字部分排序
    digit_list.sort(key=lambda x: x[1])
    sorted_digits = [d for d, _ in digit_list]

    # 合并：先数字目录，再其他目录
    return sorted_digits + other_list

def main():
    root_dir = input("请输入要检测的根目录路径：").strip()
    if not os.path.isdir(root_dir):
        print(f"错误：'{root_dir}' 不是有效目录")
        return

    video_exts = {'.mp4', '.avi', '.mkv', '.mov',
                  '.wmv', '.flv', '.rmvb', '.mpeg', '.mpg'}

    video_dirs = find_video_dirs(root_dir, video_exts)

    # 只有当至少一个目录以数字开头时，才执行排序；否则保持 os.walk 的原始顺序
    if any(get_numeric_prefix(os.path.basename(d)) is not None for d in video_dirs):
        video_dirs = sort_dirs_with_numeric_prefix(video_dirs)

    # 输出到脚本同级目录的 video_dirs.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'video_dirs.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        for d in video_dirs:
            f.write(d + '\n')

    print(f"检测完成，共找到 {len(video_dirs)} 个目录。结果已保存到：{output_path}")

if __name__ == "__main__":
    main()
