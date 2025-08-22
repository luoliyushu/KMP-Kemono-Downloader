import requests
import os, random, time
import json

# https://kemono.su/api/v1/fanbox/user/1977144/posts-legacy?o=100
# https://kemono.su/api/v1/patreon/user/12733350/posts-legacy?o=50
# 手动输入
# authors = [
#     ("patreon", 2757009),
# ]

# 自动输入
authors = []
with open(r"C:\Users\lenovo\Desktop\Parent2.json", "r", encoding="utf-8") as f:
    json_data = json.load(f).get("RECORDS")
    for item in json_data:
        url_split = item.get("url").split("/")
        if url_split[-3] and url_split[-1]:
            authors.append((url_split[-3], int(url_split[-1])))


       
headers = {
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
}
for author_sponsor, author_id in authors:
    ids_list = []
    page = 1

    api_url = f"https://kemono.su/api/v1/{author_sponsor}/user/{author_id}/posts-legacy"
    print(api_url)
    response = requests.get(api_url, headers=headers)
    info_text = f"{author_id}，第{page}页"
    if response.status_code != 200:
        print(f"{info_text}，状态码为：{response.status_code}")
    print(info_text)
    props = response.json().get('props')  # 替换 'props_key' 为实际的键名
    results = response.json().get('results')  # 替换 'results_key' 为实际的键名
    
    ids_list.extend([(item.get("id"), "https://kemono.su/%s/user/%d/post/%s" % (author_sponsor, author_id, item.get("id"))) for item in results])

    count = props.get("count")
    limit = props.get("limit")
    author_name = props.get("name")
    while page * limit < count:
        api_url = f"https://kemono.su/api/v1/{author_sponsor}/user/{author_id}/posts-legacy?o={page * limit}"
        response = requests.get(api_url, headers=headers)
        info_text = f"{author_id}，{author_name}，第{page + 1}页"
        if response.status_code != 200:
            print(f"{info_text}，状态码为：{response.status_code}")
            sleep_time = random.uniform(5, 10)
            print("睡眠时间：%.2f" % sleep_time)
            time.sleep(sleep_time)
            continue
        print(info_text)
        results = response.json().get('results')  # 替换 'results_key' 为实际的键名
        ids_list.extend([(item.get("id"), "https://kemono.su/%s/user/%d/post/%s" % (author_sponsor, author_id, item.get("id"))) for item in results])
        page += 1
        sleep_time = random.uniform(3, 5)
        print("睡眠时间：%.2f" % sleep_time)
        time.sleep(sleep_time)
    if len(ids_list) == count:
        save_path = os.path.join(r"使用说明\作者所有作品的id", f"{author_id}_{author_name}_{author_sponsor}.txt")
        for i, url in ids_list:
            with open(save_path, "a", encoding="utf-8") as f:
                f.write(f"{i} ☆ {url}\n")