import time
import typing

meta = {
    'name': '百度网盘',
    'package_name': 'baidu_netdisk',
    'doc_link': '',
    'config': {
        'CloudRootPath': {
            'name': 'root_path',
            'desc': '需要挂载的百度网盘的根目录',
            'type': str,
            "default": "/",
            'required': True,
        },
        'RefreshToken': {
            'name': 'refresh_token',
            'desc': 'Refresh Token, 可以到下方链接获取',
            'link': 'https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id=iYCeC9g08h5vuP9UqvPHKKSVrKFXGa1v&redirect_uri=https://alist.nn.ci/tool/baidu/callback&scope=basic,netdisk&qrcode=1',
            'type': str,
            'required': True,
        },
        'ClientID': {
            "name": "client_id",
            'desc': '百度网盘开发者应用的Client ID，默认是AList的，需要的也可以自己去申请一个（企业特权）',
            'type': str,
            "required": True,
            "default": "iYCeC9g08h5vuP9UqvPHKKSVrKFXGa1v"
        },
        'ClientSecret': {
            "name": "client_secret",
            'desc': '上述 ClientID 的密钥',
            'type': str,
            "required": True,
            "default": "jXiFMOPVPCWlO2M5CwWQzffpNPaGTRBG"
        },
        'AccessToken': {
            "name": "access_token",
            "default": "",
            'type': str,
        },
        'AccessTokenTime': {
            "name": "access_token_time",
            "default": 0,
            'type': float,
        },
    },
}
