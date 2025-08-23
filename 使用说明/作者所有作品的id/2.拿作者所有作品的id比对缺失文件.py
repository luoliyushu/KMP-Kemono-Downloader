import os
# # 手动添加
# compare_list = [
#     (r"G:\CloneCode_1\KMP-Kemono-Downloader-final\使用说明\作者所有作品的id\1977144_nanikairu_fanbox.txt", r"G:\CloneCode_1\KMP-Kemono-Downloader-final\#更新缺少的作品\nanikairu"),
# ]

# 自动添加
compare_list = []
auto_path = r"使用说明\作者所有作品的id" # [492048_sbfanbo_fanbox.txt, 3041039_咸鱼喵CAT_fanbox.txt]
dir_path = r"G:\CloneCode_1\KMP-Kemono-Downloader\download"
for i in os.listdir(auto_path):
    if i != "example_缺少.txt" and i.endswith(".txt"):
        s = i.find("_") + 1
        e = i.rfind("_")
        author_name = i[s:e].replace("＠", "")
        compare_list.append((
            os.path.join(auto_path, i), 
            os.path.join(dir_path, author_name)
            ))



example_path = r"使用说明\作者所有作品的id\example_缺少.txt"
f2 = open(example_path, "w", encoding="utf-8")
absence_list = []
for id_path, dir_path in compare_list:
    id_url_list = []
    f1 = open(id_path, "r", encoding="utf-8")
    id_url_list = f1.readlines()
    
    # 检测是否存在相同id和url
    check_same_list = []
    for id_url in id_url_list:
        if id_url:
            id, url = id_url.split(" ☆ ")
            if id_url not in check_same_list:
                check_same_list.append(id_url)
            else:
                id, url = id_url.split(" ☆ ")
                print(f"已经存在相同的id：{id}")
    print("="*20)
    
    # 检测缺少的id
    for id_url in id_url_list:
        if id_url:
            id, url = id_url.split(" ☆ ")
            dir_id_list = [i[:i.find(" ")] for i in os.listdir(dir_path)]
            if id not in dir_id_list:
                absence_list.append(url)
    f1.close()
f2.writelines(absence_list)
f2.close()