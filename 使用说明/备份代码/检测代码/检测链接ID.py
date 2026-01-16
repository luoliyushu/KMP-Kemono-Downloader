import requests
from bs4 import BeautifulSoup
import time, random
import os

dir_path = r"G:\MyCode\KMP-Kemono-Downloader-final\download\muk-monsieur"
url = "https://kemono.su/fanbox/user/4234383"
start_num = 0
end_num = 400



ids = []
page = 0
for num in range(start_num, end_num+50, 50):
    page += 1
    print(f"第{page}页，获取ID的URL：{url}?o={num}")
    r = requests.get(f"{url}?o={num}")
    soup = BeautifulSoup(r.text, 'html.parser')
    # 使用CSS选择器获取所有具有data-id属性的元素
    elements_with_data_id = soup.select('[data-id]')
    # 遍历这些元素并打印其文本和data-id
    for element in elements_with_data_id:
        ids.append(element.get('data-id'))
        with open(r"G:\MyCode\KMP-Kemono-Downloader-final\使用说明\检测代码\临时保存的html.html", "a", encoding="utf-8") as f:
            f.write(str(element.prettify()))
    time.sleep(random.randint(5, 10))
print(f"获取到的ID数量：{len(ids)}")



dirs = os.listdir(dir_path)
dir_ids = []
for dir in dirs:
    if dir.split(" ")[0].isdigit():
        dir_ids.append(dir.split(" ")[0])
print(f"目录的ID数量：{len(dir_ids)}")



for dir_id in dir_ids:
    try:
        ids.remove(dir_id)
    except ValueError:
        print(f"ID {dir_id} 不存在于列表中")
print(f"最终结果：{ids}")