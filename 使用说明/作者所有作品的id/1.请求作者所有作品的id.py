import requests
import os
import json
import time
import random
import re

# -----------------------------------------------------------------------------
# 1. 手动输入作者列表
#    将想要抓取的作者信息，按照 ("平台标识", 作者ID) 的格式添加到下面列表中
#    平台标识示例："patreon"、"fanbox" 等
# -----------------------------------------------------------------------------
manual_authors = [
    # 示例：("patreon", 2757009),
    # 示例：("fanbox", 1977144),
]

# -----------------------------------------------------------------------------
# 2. 自动读取作者列表
#    从本地 JSON 文件中读取作者 URL，自动解析出平台标识和作者 ID
#    JSON 文件应包含一个顶级字段 "RECORDS"，其值为数组，每项含 "url" 字段
# -----------------------------------------------------------------------------
auto_authors = []
json_file = r"C:\Users\lenovo\Desktop\Parent2.json"
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)
    records = data.get("RECORDS", [])
    for item in records:
        url = item.get("url", "")
        parts = url.split("/")
        # URL 示例: https://kemono.cr/api/v1/patreon/user/12733350/...
        # 提取倒数第3段作为平台标识，最后一段作为作者 ID
        if len(parts) >= 4:
            sponsor = parts[-3]
            uid_str = parts[-1]
            if sponsor and uid_str.isdigit():
                auto_authors.append((sponsor, int(uid_str)))

# 合并手动和自动列表，得到最终待抓取作者列表
authors = manual_authors + auto_authors

# -----------------------------------------------------------------------------
# 3. 输出目录初始化
#    用于保存每个作者所有作品 ID 的 txt 文件
# -----------------------------------------------------------------------------
save_dir = r"使用说明\作者所有作品的id"
os.makedirs(save_dir, exist_ok=True)

# -----------------------------------------------------------------------------
# 4. 通用请求头设置
#    伪装成正常浏览器，Accept 设置为 text/css 以绕过 JSON/Spa 限制
# -----------------------------------------------------------------------------
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept": "text/css",
}

# -----------------------------------------------------------------------------
# 5. 主抓取流程：遍历每个作者
# -----------------------------------------------------------------------------
for sponsor, author_id in authors:
    # 5.1 请求 profile 接口，获取作者基本信息
    profile_url = f"https://kemono.cr/api/v1/{sponsor}/user/{author_id}/profile"
    resp = requests.get(profile_url, headers=headers)
    if resp.status_code != 200:
        print(f"作者 {author_id} profile 接口错误，状态码：{resp.status_code}，跳过该作者")
        continue

    profile = resp.json()
    author_name_raw = profile.get("name", "unknown")     # 原始作者名称
    total_posts = profile.get("post_count", 0)           # 作者作品总数

    # 5.2 清洗作者名称，替换文件名中非法字符
    #    Windows 下文件名不能包含 \ / : * ? " < > |
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', author_name_raw)

    # 5.3 构造文件名：authorId_authorName_platform.txt
    filename = f"{author_id}_{safe_name}_{sponsor}.txt"
    save_path = os.path.join(save_dir, filename)

    # 5.4 检查文件是否已存在，若存在则跳过该作者
    if os.path.exists(save_path):
        print(f"跳过 {author_name_raw}({author_id})：文件已存在 -> {save_path}")
        continue

    print(f"开始抓取 -> {author_name_raw}({author_id}) 共 {total_posts} 条帖子")

    # 5.5 分页抓取帖子列表
    limit = 50      # 每页最大数量
    offset = 0      # 偏移量
    collected = []  # 存放 (post_id, post_url) 的列表

    while offset < total_posts:
        # 构造 posts 接口 URL，使用 o 参数控制偏移量
        posts_url = f"https://kemono.cr/api/v1/{sponsor}/user/{author_id}/posts"
        if offset > 0:
            posts_url += f"?o={offset}"

        resp = requests.get(posts_url, headers=headers)
        page_no = offset // limit + 1

        # 如果请求失败，随机等待后重试
        if resp.status_code != 200:
            wait = random.uniform(5, 10)
            print(f"{author_name_raw} 第{page_no}页 请求失败({resp.status_code})，等待 {wait:.1f}s 重试")
            time.sleep(wait)
            continue

        posts = resp.json()
        print(f"{author_name_raw} 第{page_no}页 获取 {len(posts)} 条")

        # 收集每条帖子的 ID 及访问链接
        for post in posts:
            pid = post.get("id")
            post_url = f"https://kemono.cr/{sponsor}/user/{author_id}/post/{pid}"
            collected.append((pid, post_url))

        # 递增 offset，准备抓取下一页
        offset += limit
        wait_short = random.uniform(3, 5)
        print(f"睡眠 {wait_short:.1f}s 后抓取下一页")
        time.sleep(wait_short)

    # 5.6 将抓取到的结果写入 txt 文件
    with open(save_path, "w", encoding="utf-8") as f:
        for pid, link in collected:
            f.write(f"{pid} ☆ {link}\n")

    print(f"完成：{author_name_raw}({author_id}) 共抓取 {len(collected)} 条，已保存 -> {save_path}\n")
