#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：
    在“自动模式”下，将由主程序生成的 results_summary.txt
    转换成 exception_urls.txt。流程如下：
      1. 读取 records.json 中的 RECORDS 列表，派生每条记录的 api_base 与根目录路径
      2. 解析 results_summary.txt，每行取出目录路径和 post_id
      3. 在上一步派生出的记录映射中，找到匹配该目录的 api_base
      4. 调用 api_to_page_url 拼出页面 URL，写入 exception_urls.txt

使用方式：
    把本脚本放在与 records.json、results_summary.txt 同一目录下，
    直接运行即可生成 exception_urls.txt。
"""

import os
import sys
import json
from urllib.parse import urlparse

def load_records(json_path):
    """
    从 JSON 读取 RECORDS 列表，并派生出每条的 api_base 与根目录路径
    
    Args:
        json_path (str): records.json 文件路径
    
    Returns:
        list of dict: 每项包含：
            - root_dir: 自动模式下的目录路径（destination/artist）
            - api_base: 对应的 API 根地址（以 /post/ 结尾）
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    recs = data.get("RECORDS")
    if not isinstance(recs, list):
        raise RuntimeError('"RECORDS" 字段缺失或格式错误，需为列表')
    
    mapping = []
    for rec in recs:
        # 每条记录必须含有 url、artist、destination
        user_url = rec.get('url')
        artist      = rec.get('artist')
        destination = rec.get('destination')
        if not user_url or not artist or not destination:
            # 跳过不完整的记录
            continue
        
        # derive_api_base：参考主程序逻辑
        parsed = urlparse(user_url)
        scheme = parsed.scheme or 'https'
        path = parsed.path.rstrip('/')
        api_base = f"{scheme}://kemono.su/api/v1{path}/post/"
        
        # 根目录：destination/artist
        root_dir = os.path.abspath(os.path.join(destination, artist))
        mapping.append({
            'root_dir': root_dir,
            'api_base': api_base
        })
    return mapping

def api_to_page_url(api_base, post_id):
    """
    将 API URL 转成页面 URL：
      1. 去掉 '/api/v1' 前缀
      2. 拼接 post_id（确保末尾 '/')
    """
    parsed = urlparse(api_base)
    scheme, netloc, path = parsed.scheme, parsed.netloc, parsed.path
    # 去掉 '/api/v1' 前缀
    if path.startswith('/api/v1'):
        page_path = path[len('/api/v1'):]
    else:
        page_path = path
    # 确保路径以 '/' 结尾
    if not page_path.endswith('/'):
        page_path += '/'
    return f"{scheme}://{netloc}{page_path}{post_id}"

def parse_summary_line(line):
    """
    从 summary 文本行中提取目录路径和 post_id
    每行格式：目录 | post_id | 接口资源数 | 本地文件数 | 备注
    返回 (目录绝对路径, post_id)，无法解析返回 (None, None)
    """
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 2:
        return None, None
    dir_path, pid = parts[0], parts[1]
    # 转为绝对路径
    dir_path = os.path.abspath(dir_path)
    # pid 必须是纯数字
    if not pid.isdigit():
        return None, None
    return dir_path, pid

def main():
    # 脚本当前目录（假设 records.json 和 summary 文件放在此处）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path     = os.path.join(script_dir, 'Parent2.json')
    summary_path  = os.path.join(script_dir, 'results_summary.txt')
    output_path   = os.path.join(script_dir, 'exception_urls.txt')

    # 1. 加载记录映射
    if not os.path.isfile(json_path):
        print(f"错误：找不到 records.json：{json_path}")
        sys.exit(1)
    mapping = load_records(json_path)
    if not mapping:
        print("警告：从 records.json 未派生出任何有效记录，程序退出")
        sys.exit(0)

    # 2. 打开 summary，读取每一行
    if not os.path.isfile(summary_path):
        print(f"错误：找不到 results_summary.txt：{summary_path}")
        sys.exit(1)

    urls = []
    with open(summary_path, 'r', encoding='utf-8') as fr:
        for line in fr:
            line = line.strip()
            # 跳过表头、分割线或空行
            if not line or line.startswith('目录 ') or set(line) == {'-'}:
                continue

            dir_path, pid = parse_summary_line(line)
            if not dir_path:
                print(f"警告：无法解析行，跳过：{line}")
                continue

            # 3. 在 mapping 中找到与 dir_path 匹配的记录
            matched = None
            for rec in mapping:
                # 如果 summary 中的目录以 rec['root_dir'] 开头，视为匹配
                if dir_path.startswith(rec['root_dir'] + os.sep):
                    matched = rec
                    break
            if not matched:
                print(f"警告：未在 records.json 中找到匹配目录，跳过：{dir_path}")
                continue

            # 4. 拼出页面 URL
            page_url = api_to_page_url(matched['api_base'], pid)
            urls.append(page_url)

    # 5. 写入 exception_urls.txt
    with open(output_path, 'w', encoding='utf-8') as fw:
        for u in urls:
            fw.write(u + '\n')

    print(f"共生成 {len(urls)} 条异常 URL，已保存到：{output_path}")

if __name__ == '__main__':
    main()
