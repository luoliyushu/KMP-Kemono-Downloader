# 先使用 Notepad++ 打开包含日志内容的文本文件，
# 之后使用（Ctrl+F）查找 ‘ is completed’，将查找的结果（Ctrl+C）复制，
# 然后将所有内容（Ctrl+V）粘贴到下面的三引号内的 content 变量中。
# 之后运行代码，将代码的结果粘贴到 Everything 中进行批量筛选。
content = """
	行 1154: INFO (01/15/2026 06:13:45 PM): https://kemono.party/fanbox/user/22333059 is completed
	行 1155: INFO (01/15/2026 06:13:45 PM): https://kemono.party/patreon/user/92535202 is completed
	行 1156: INFO (01/15/2026 06:13:45 PM): https://kemono.party/fanbox/user/3041039 is completed
	行 1175: on 94: INFO (01/15/2026 06:16:19 PM): https://kemono.party/fanbox/user/1710711 is completed
	行 1176: on 108: INFO (01/15/2026 06:16:41 PM): https://kemono.party/fanbox/user/59336265 is completed
	行 1177: on 221: INFO (01/15/2026 06:18:30 PM): https://kemono.party/patreon/user/46802018 is completed
	行 1178: on 239: INFO (01/15/2026 06:18:47 PM): https://kemono.party/fanbox/user/35516002 is completed
	行 1194: on 344: INFO (01/15/2026 06:21:27 PM): https://kemono.party/fanbox/user/767724 is completed
	行 1195: on 344: INFO (01/15/2026 06:21:27 PM): https://kemono.party/patreon/user/57010059 is completed
	行 1196: on 344: INFO (01/15/2026 06:21:27 PM): https://kemono.party/patreon/user/7303006 is completed
	行 3506: on 6162: INFO (01/15/2026 11:25:08 PM): https://kemono.party/fanbox/user/17722960 is completed
	行 3507: on 6165: INFO (01/15/2026 11:25:12 PM): https://kemono.party/fanbox/user/54698934 is completed
	行 3513: on 6181: INFO (01/15/2026 11:25:58 PM): https://kemono.party/fanbox/user/16731 is completed
	行 3566: on 6300: INFO (01/15/2026 11:33:39 PM): https://kemono.party/patreon/user/69653195 is completed
	行 3567: on 6303: INFO (01/15/2026 11:33:44 PM): https://kemono.party/patreon/user/15084132 is completed
	行 3691: on 6516: INFO (01/15/2026 11:47:54 PM): https://kemono.party/fanbox/user/258003 is completed
	行 4482: on 7552: INFO (01/16/2026 01:01:26 AM): https://kemono.party/fanbox/user/1977144 is completed
"""


content = content.strip()
str_list = content.splitlines()
id_list = []
for line in str_list:
    if line:
        line = line.strip()
        index = line.rfind("/")+1
        id_list.append(int(line[index:line.find(" is completed")]))
print(r"%s .txt !216731.atlas.txt" % ("|".join(map(str, id_list))))