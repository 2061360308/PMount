import json
import os.path

import requests

access_token = "121.19928a1378b8a8613fcaca80d0000848.YB3Hmj6xv6jFjKywKyhSYapnSdl5qynjDbjvxmL.kSXNLA"
path = r"D:\LUAO\Desktop\2085.png_860.png"
cloud_path = r'/test/2085.png_860.png'
url = f"http://pan.baidu.com/rest/2.0/xpan/file?method=precreate&access_token={access_token}"


def get_md5(file_path):
    import hashlib
    with open(file_path, 'rb') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(10240)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


block_list = [get_md5(path)]

payload = {'path': cloud_path,
           'size': os.path.getsize(path),
           'rtype': '1',
           'isdir': '0',
           'autoinit': '1',
           'block_list': json.dumps(block_list)}

response = requests.request("POST", url, data=payload)

print(response.text.encode('utf8'))

uploadid = json.loads(response.text)['uploadid']

url = f"https://c3.pcs.baidu.com/rest/2.0/pcs/superfile2?method=upload&access_token={access_token}&path={cloud_path}&type=tmpfile&uploadid={uploadid}&partseq=0"

payload = {}
files = [
    ('file', open(path, 'rb'))
]
headers = {
}

response = requests.request("POST", url, headers=headers, data=payload, files=files)

print(response.text.encode('utf8'))

url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=create&access_token={access_token}"

payload = {'path': cloud_path,
           'size': os.path.getsize(path),
           'rtype': '1',
           'isdir': '0',
           'uploadid': uploadid,
           'block_list': json.dumps(block_list)}


response = requests.request("POST", url, data=payload)

print(response.text.encode('utf8'))
