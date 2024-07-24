import time
from concurrent.futures import ThreadPoolExecutor

import requests

pool = ThreadPoolExecutor(max_workers=5)  # 可以指定最大工作线程数

url = "http://gzbh-cm01-2.baidupcs.com/file/cd87eb4c1r0f5706eef3b1e5d96eef0f?bkt=en-c58a217c5b5bf7b29c2b0b812f1445a6e9d9aedf1908acd6c7d6783b0f3d17e995e7f960589996bf&fid=1102622167898-250528-219082268519932&time=1721744804&sign=FDTAXUbGERQlBHSKfWaqi-DCb740ccc5511e5e8fedcff06b081203-vBhXdE1cKoZfZyejb8%2Bht8waLCI%3D&to=707&size=84155305&sta_dx=84155305&sta_cs=7&sta_ft=zip&sta_ct=5&sta_mt=5&fm2=MH%2CXian%2CAnywhere%2C%2C%E5%B1%B1%E8%A5%BF%2Ccnc&ctime=1713960136&mtime=1713960136&resv0=-1&resv1=0&resv2=rlim&resv3=5&resv4=84155305&vuk=1102622167898&iv=2&vl=3&htype=&randtype=&tkbind_id=0&newver=1&newfm=1&secfm=1&flow_ver=3&pkey=en-d0848c43ceda6788b04f6f6fdfdce6a586f8e89c88673eeb162f27e5af7622e4ad069490c3b5e771&expires=8h&rt=pr&r=890842847&vbdid=4061119132&fin=Typora.zip&rtype=1&dp-logid=2126752231402570351&dp-callid=0.1&tsl=0&csl=0&fsl=-1&csign=SLbmN3pVn8baCBwyvbG11fpdkyo%3D&so=1&ut=1&uter=0&serv=0&uc=1559654663&ti=068bcab50ae430c7cdf78797965ae98e0ecd2a98848fea40&hflag=30&from_type=1&adg=a_c2b39333fff693513f1bf67224df46b6&reqlabel=25571201_f_0d379c25691f1db02fd2dff786ffd19a_-1_f2996769182fed8a0e90fa661f67a3e1&by=themis"


headers = {
    "User-Agent": "pan.baidu.com",
    "Range": "bytes=-44154805"
}

# 发起GET请求，设置stream=True开始流式下载
with requests.get(url, headers=headers, stream=True) as r:
    r.raise_for_status()  # 确保请求成功
    total_size = int(r.headers.get('content-length', 0))  # 获取文件总大小
    start_time = time.time()
    downloaded_size = 0  # 已下载的数据量
    for chunk in r.iter_content(chunk_size=8192):  # 每次读取8192字节
        # 这里可以处理每个块，例如写入文件
        downloaded_size += len(chunk)  # 更新已下载的数据量
        print(f"已下载：{downloaded_size} / {total_size} 字节 下载速度：{((downloaded_size / (1024 * 1024)) / ((time.time() - start_time) if (time.time() - start_time) > 0 else 1e-10)):.2f} MB/秒")
        # 注意：在实际应用中，可能需要添加额外的逻辑来处理下载进度的显示，以避免过于频繁的输出
    end_time = time.time()
    print(f"下载完成，耗时：{end_time - start_time:.2f}秒")
    print("下载速度：{:.2f}字节/秒".format(total_size / (end_time - start_time)))

