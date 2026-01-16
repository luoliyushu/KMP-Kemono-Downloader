# 导入os模块用来遍历目录
import os
import shutil

# 定义要遍历的目录
root_dir = r'D:\Tool\scriptCode\KMP-Kemono-Downloader-final\download\hi-geepon'  

# 遍历root_dir下的所有子目录
for subdir in os.listdir(root_dir):
    subdir_path = os.path.join(root_dir, subdir)
    if os.path.isdir(subdir_path):
        #   只有压缩包，没有额外图片的目录
        if ("7408345" in subdir_path):
            continue
        try:
            # 判断子目录中是否只包含0.jpg和post__content.txt两个文件 post__comments.txt
            dir_contents = os.listdir(subdir_path)
            if set(dir_contents) == {'0.jpeg', 'post__content.txt', "post__comments.txt"}:
                # 如果是,则删除该子目录
                print(f'Deleting {subdir_path}') 
                # os.rmdir(subdir_path)
                shutil.rmtree(subdir_path)
                
            else:
                # 否则保留子目录
                print(f'Keeping {subdir_path}')
        except FileNotFoundError:
            with open("找不到的路径.txt", "a",  encoding="utf-8") as f:
                f.write(f"{subdir_path}\n")