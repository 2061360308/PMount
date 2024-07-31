import os
import time
from pprint import pprint

import requests
from requests import Request
from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util.retry import Retry
from urllib3.util.retry import Retry
import json
import logging
from easydict import EasyDict


class BaiduNetdisk:
    def __init__(self, config, debug=False):
        self.DEBUG = debug
        self.config = config
        self.client_id = config.client_id
        self.client_secret = config.client_secret
        self.access_token = config.access_token
        self.refresh_token = config.refresh_token

        self.session = requests.Session()

        self.check_access_token()

        if not self.access_token:
            if self.refresh_token:
                print("No access token, refreshing")
                self.refresh_access_token()
            else:
                raise Exception("No access token or refresh token")

        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def check_access_token(self):
        if time.time() - self.config.access_token_time > 1728000:
            self.refresh_access_token()

    def _refresh_token(self):
        """
        刷新 access_token
        :return:
        """
        print("Refreshing access token")
        url = "https://openapi.baidu.com/oauth/2.0/token"
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            return Exception("Failed to refresh token")
        data = response.json()
        if "error" in data:
            return Exception(f"{data['error']} : {data['error_description']}")
        if "refresh_token" not in data or data["refresh_token"] == "":
            return Exception("EmptyToken")
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        # print(self.access_token, self.refresh_token)
        # Save tokens for persistence
        self.config.access_token = self.access_token
        self.config.refresh_token = self.refresh_token
        print(self.config.access_token, self.config.refresh_token)
        self.config.access_token_time = time.time()
        return None

    def refresh_access_token(self):
        error = self._refresh_token()
        if error and str(error) == "EmptyToken":
            error = self._refresh_token()
        return error

    def request(self, furl, method, params, form_data=None, callback=None, rest=True):
        # 拼接得到完整的请求url
        if rest:
            url = "https://pan.baidu.com/rest/2.0" + furl
        else:
            url = "https://pan.baidu.com" + furl
        # 如果没有传入params，则初始化为空字典
        if params is None:
            params = {}
        # 装载access_token
        params["access_token"] = self.access_token

        if callback:
            callback(params)

        if method.upper() == "GET":
            # Prepare the request
            req = Request('GET', url, params=params)
        elif method.upper() == "POST":
            if form_data is None:
                form_data = {}
            req = Request('POST', url, params=params, data=form_data)
        else:
            raise ValueError("Unsupported HTTP method")
        # Use the session to prepare the request
        prepped = self.session.prepare_request(req)
        if self.DEBUG:
            print(f'url: {prepped.url}')
            print(f'headers: {prepped.headers}')
            print(f'body: {prepped.body}')
        response = self.session.send(prepped)

        logging.debug(f"[baidu_netdisk] req: {furl}, resp: {response.text}")
        if response.status_code != 200:
            if response.status_code in [111, -6]:  # Assuming these are token error codes
                logging.info("Refreshing baidu_netdisk token.")
                error = self.refresh_access_token()  # Corrected method name
                if error:
                    raise Exception(error)
            else:
                raise Exception(
                    f"req: [{furl}] ,errno: {response.status_code}, {response.text}, refer to https://pan.baidu.com"
                    f"/union/doc/")
        return response

    def get(self, pathname, params, callback=None, rest=True):
        return self.request(furl=pathname, method="GET", params=params,
                            form_data=None, callback=callback, rest=rest)

    def post(self, pathname, params, form_data=None, callback=None, rest=True):
        return self.request(furl=pathname, method="POST", params=params,
                            form_data=form_data, callback=callback, rest=rest)

    def user_info(self):
        response = self.get("/xpan/nas", {"method": "uinfo"})
        return response.json()

    def quota(self, use_gb=False):
        response = self.get("/api/quota", {}, rest=False)
        data = response.json()

        def b_to_gb(b):
            return round(b / 1024 / 1024 / 1024, 2)

        if use_gb:
            total = b_to_gb(data["total"])
            used = b_to_gb(data["used"])
        else:
            total = data["total"]
            used = data["used"]
        return EasyDict({"total": total, "used": used})

    def list(self, **kwargs):
        """
        列出目录

        以下参数可选：
            dir：        需要list的目录，以/开头的绝对路径, 默认为/
            order：      排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；
                         name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发)
                         size表示先按文件类型排序，后按文件大小排序。
            desc：       默认为升序，设置为1实现降序 （注：排序的对象是当前目录下所有文件，不是当前分页下的文件）
            start：      起始位置，从0开始
            limit：      查询数目，默认为1000，建议最大不超过1000
            web：        值为1时，返回dir_empty属性和缩略图数据
            folder：     是否只返回文件夹，0 返回所有，1 只返回文件夹，且属性只返回path字段
            showempty：  是否返回dir_empty属性，0 不返回，1 返回
        :return:
        """
        kwargs["method"] = 'list'
        response = self.get("/xpan/file", kwargs)
        return EasyDict(response.json())

    def list_doc(self, **kwargs):
        """
        列出文档

        以下参数可选：
            parent_path：需要list的目录，以/开头的绝对路径, 默认为/
            order：      排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；
                         name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发)
                         size表示先按文件类型排序，后按文件大小排序。
            desc：       默认为升序，设置为1实现降序 （注：排序的对象是当前目录下所有文件，不是当前分页下的文件）
            start：      起始位置，从0开始
            limit：      查询数目，默认为1000，建议最大不超过1000
            web：        值为1时，返回dir_empty属性和缩略图数据
        :return:
        """
        kwargs["method"] = 'doclist'
        response = self.get("/xpan/file", kwargs)
        return EasyDict(response.json())

    def list_pic(self, **kwargs):
        """
        列出图片

        以下参数可选：
            parent_path：需要list的目录，以/开头的绝对路径, 默认为/
            order：      排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；
                         name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发)
                         size表示先按文件类型排序，后按文件大小排序。
            desc：       默认为升序，设置为1实现降序 （注：排序的对象是当前目录下所有文件，不是当前分页下的文件）
            start：      起始位置，从0开始
            limit：      查询数目，默认为1000，建议最大不超过1000
            web：        值为1时，返回dir_empty属性和缩略图数据
        :return:
        """
        kwargs["method"] = 'imagelist'
        response = self.get("/xpan/file", kwargs)
        return EasyDict(response.json())

    def list_video(self, **kwargs):
        """
        列出视频

        以下参数可选：
            parent_path：需要list的目录，以/开头的绝对路径, 默认为/
            order：      排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；
                         name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发)
                         size表示先按文件类型排序，后按文件大小排序。
            desc：       默认为升序，设置为1实现降序 （注：排序的对象是当前目录下所有文件，不是当前分页下的文件）
            start：      起始位置，从0开始
            limit：      查询数目，默认为1000，建议最大不超过1000
            web：        值为1时，返回dir_empty属性和缩略图数据
        :return:
        """
        kwargs["method"] = 'videolist'
        response = self.get("/xpan/file", kwargs)
        return EasyDict(response.json())

    def list_bt(self, **kwargs):
        """
        列出bt

        以下参数可选：
            parent_path：需要list的目录，以/开头的绝对路径, 默认为/
            order：      排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；
                         name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发)
                         size表示先按文件类型排序，后按文件大小排序。
            desc：       默认为升序，设置为1实现降序 （注：排序的对象是当前目录下所有文件，不是当前分页下的文件）
            start：      起始位置，从0开始
            limit：      查询数目，默认为1000，建议最大不超过1000
            web：        值为1时，返回dir_empty属性和缩略图数据
        :return:
        """
        kwargs["method"] = 'btlist'
        response = self.get("/xpan/file", kwargs)
        return EasyDict(response.json())

    def _categoryinfo(self, params):
        response = self.get("/api/categoryinfo", params, rest=False)
        return EasyDict(response.json())

    def count_ca_vidoe(self, **kwargs):
        kwargs["category"] = 1
        return self._categoryinfo(kwargs)

    def count_ca_song(self, **kwargs):
        kwargs["category"] = 2
        return self._categoryinfo(kwargs)

    def count_ca_pic(self, **kwargs):
        kwargs["category"] = 3
        return self._categoryinfo(kwargs)

    def count_ca_doc(self, **kwargs):
        kwargs["category"] = 4
        return self._categoryinfo(kwargs)

    def count_ca_app(self, **kwargs):
        kwargs["category"] = 5
        return self._categoryinfo(kwargs)

    def count_ca_other(self, **kwargs):
        kwargs["category"] = 6
        return self._categoryinfo(kwargs)

    def count_ca_bt(self, **kwargs):
        kwargs["category"] = 7
        return self._categoryinfo(kwargs)

    def _categorylist(self, params):
        """

        列出分类
        :param params:
        :return:
        """
        params["method"] = 'categorylist'
        response = self.get("/xpan/multimedia", params)
        return EasyDict(response.json())

    def list_ca_vidoe(self, **kwargs):
        """
        列出视频分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 1
        return self._categorylist(kwargs)

    def list_ca_song(self, **kwargs):
        """
        列出音频分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 2
        return self._categorylist(kwargs)

    def list_ca_pic(self, **kwargs):
        """
        列出图片分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 3
        return self._categorylist(kwargs)

    def list_ca_doc(self, **kwargs):
        """
        列出文档分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 4
        return self._categorylist(kwargs)

    def list_ca_app(self, **kwargs):
        """
        列出应用分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 5
        return self._categorylist(kwargs)

    def list_ca_other(self, **kwargs):
        """
        列出其他分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 6
        return self._categorylist(kwargs)

    def list_ca_bt(self, **kwargs):
        """
        列出bt分类
        可选的参数如下：
            show_dir：是否显示文件夹，0 不显示，1 显示
            parent_path：目录名称，为空时，parent_path = "/" && recursion = 1 ；
            recursion：是否递归，0 不递归，1 递归
            ext：需要的文件格式，多个格式以英文逗号分隔，示例: txt,epub，默认为category下所有格式
            start：起始位置，从0开始
            limit：查询数目，默认为1000，建议最大不超过1000
            order：排序字段：默认为name；time表示先按文件类型排序，后按修改时间排序；name表示先按文件类型排序，后按文件名称排序；(注意，此处排序是按字符串排序的，如果用户有剧集排序需求，需要自行开发) size表示先按文件类型排序，后按文件大小排序。
            desc：默认为升序，设置为1实现降序
            device_id：设备ID，硬件设备必传，例如144213733w02217w8v
        :param kwargs:
        :return:
        """
        kwargs["category"] = 7
        return self._categorylist(kwargs)

    def search(self, key, **kwargs):
        """
        搜索文件

        可选参数如下：
            dir：       搜索目录，默认根目录
            category：  搜索分类，默认为全部分类
            page：      页码，默认为1
            num：       默认为500，不能修改
            recursion： 是否递归，带这个参数就会递归，否则不递归
            web：       默认为0 是否展示缩略图信息，带这个参数会返回缩略图信息，否则不展示缩略图信息
        :param key:
        :param kwargs:
        :return:
        """
        kwargs["method"] = 'search'
        kwargs["key"] = key
        response = self.get("/xpan/file", kwargs)

        return EasyDict(response.json())

    def files(self, fsids, **kwargs):
        """
        获取文件信息

        可选参数如下：
            dlink：是否返回下载链接，0 不返回，1 返回，默认为0
            thumb：是否需要缩略图地址，0为否，1为是，默认为0
            extra：图片是否需要拍摄时间、原图分辨率等其他信息，0 否、1 是，默认0
            needmedia：视频是否需要展示时长信息，needmedia=1时，返回 duration 信息时间单位为秒 （s），转换为向上取整。0 否、1 是，默认0
            detail：视频是否需要展示长，宽等信息。0 否、1 是，默认0

        :param fsids: 文件fsid列表, 上限100
        :param kwargs:
        :return:
        """
        if not isinstance(fsids, list):
            fsids = [fsids, ]

        fsids_str = f'[{",".join(map(str, fsids))}]'

        kwargs["method"] = 'filemetas'
        kwargs["fsids"] = fsids_str
        response = self.get("/xpan/multimedia", kwargs)
        return EasyDict(response.json())

    def manage(self, opera, filelist):
        """
        文件管理

        filelist示例：
            [{"path":"/test/123456.docx","dest":"/test/abc","newname":"11223.docx"}]【copy/move示例】
            [{"path":"/test/123456.docx","newname":"123.docx"}]【rename示例】
            ["/test/123456.docx"]【delete示例】

        :param opera: 文件操作参数，可实现文件复制、移动、重命名、删除，依次对应的参数值为：copy、move、rename、delete
        :param filelist: 文件列表
        :return:
        """
        params = {
            "method": "filemanager",
            "opera": opera,
        }

        form_data = {
            "async": 1,  # 自适应选择同步还是异步， 0 同步，1 自适应，2 异步
            "filelist": json.dumps(filelist)
        }

        response = self.post("/xpan/file", params, form_data=form_data)
        return EasyDict(response.json())

    def copy(self, filePath, destPath):
        """
        文件复制
        :param filePath: 文件路径
        :param destPath: 目标路径
        :return:
        """
        fileName = os.path.split(filePath)[1]

        filelist = [{"path": filePath, "dest": destPath, "newname": fileName}]
        return self.manage("copy", filelist)

    def move(self, filePath, destPath):
        """
        文件移动
        :param filePath: 文件路径
        :param destPath: 目标路径
        :return:
        """
        fileName = os.path.split(filePath)[1]

        filelist = [{"path": filePath, "dest": destPath, "newname": fileName}]
        return self.manage("move", filelist)

    def rename(self, filePath, newName):
        """
        文件重命名
        :param filePath: 文件路径
        :param newName: 新文件名
        :return:
        """
        filelist = [{"path": filePath, "newname": newName}]
        return self.manage("rename", filelist)

    def delete(self, filePath):
        """
        删除文件
        :param filePath: 文件路径
        :return:
        """
        return self.manage("delete", [filePath])

    def get_final_download_link(self, url):
        # 创建一个会话对象
        session = requests.Session()
        # 拼接access_token到url
        url = f'{url}&access_token={self.access_token}'
        return url  # 直接返回url
        print(url)
        # 发送 HEAD 请求
        response = session.head(url, allow_redirects=False, headers={'User-Agent': 'pan.baidu.com'})
        # 从响应头中获取最终的下载链接
        final_url = response.headers.get('Location')
        return final_url

    def get_res_url(self, fsids):
        """
        获取资源链接(单个资源)
        :return:
        """
        """
        'https://d.pcs.baidu.com/file/099a1e8a4sfb9a56bbaff2c9cd15a4fd?fid=1102622167898-250528-617439386979391&rt=pr&sign=FDtAERK-DCb740ccc5511e5e8fedcff06b081203-38lyfHqiuy42swSiz8pyA3CZR7E%3D&expires=8h&chkbd=0&chkv=0&dp-logid=3028221541306415243&dp-callid=0&dstime=1721667913&r=917247469&vuk=1102622167898&origin_appid=25571201&file_type=0'
        
        """
        res_url = self.files(fsids, dlink=1).list[0].dlink
        # return res_url
        return self.get_final_download_link(res_url)

    def path_to_fsid(self, path):
        """
        根据路径获取文件fsid
        :param path:
        :return:
        """
        dir, file = os.path.split(path)
        fsid = self.search(file, dir=dir).list[0].fs_id

        return fsid

    def get_m3u8(self, path, definition_type=1080):
        """
        获取m3u8文件
        :param definition_type: 清晰度类型，1080、720、480
        :param path:
        :return:
        """
        definition_type = " M3U8_AUTO_" + str(definition_type)
        params = {
            "method": "streaming",
            "path": path,
            "type": definition_type,
            "nom3u8": 0
        }
        response = self.get("/xpan/file", params)
        return response.text

if __name__ == '__main__':
    baidu_netdisk = BaiduNetdisk(True)
    # baidu_netdisk.refresh_access_token()
    user_info = baidu_netdisk.get_m3u8("/计算机组成原理 6小时突击课/课时7 CPU的结构和功能 .mp4")
    # print("user_info::")
    pprint(user_info)
    with open("x.m3u8", 'w+', encoding='utf-8') as f:
        f.write(user_info)
