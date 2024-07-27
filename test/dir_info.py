import time

from internal.dir_info import dirInfoManager

dirInfoManager.readDirAsync("/百度网盘/序列1", 4)

time0 = time.time()

while time.time() - time0 < 15000000:
    time.sleep(1)

# 任务完成后写入文件
with open('./dir_info.txt', 'w+', encoding='utf-8') as f:
    for i in dirInfoManager.dir_buffer:
        f.write(i + '\n')
        f.write(str(dirInfoManager.dir_buffer[i]) + '\n')
        f.write('\n')
