import base64
import hashlib
import hmac
import logging
import time
from typing import Tuple
from urllib.parse import quote_plus

import requests


class DingtalkPusher:
    API_URL = "https://oapi.dingtalk.com/robot/send"

    def __init__(self, access_token: str, secret: str):
        self.access_token = access_token
        self.secret = secret

    def get_signature(self) -> Tuple[str, str]:
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{self.secret}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(
            secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def send(self, message: str, title: str) -> None:
        timestamp, sign = self.get_signature()
        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "text", "text": {"content": f"{title}\n\n{message}"}}
        url = f"{self.API_URL}?access_token={self.access_token}&timestamp={timestamp}&sign={sign}"

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"DingTalk 发送失败,错误:{e}")
            return

        resp = response.json()
        if resp["errcode"] != 0:
            logging.error(f"DingTalk 发送失败,错误:{resp['errmsg']}")
            return

        logging.info("DingTalk 发送成功")


if __name__ == "__main__":
    # 示例
    access_token = "xxx"
    secret = "xxx"
    message = "您的账单已出帐"
    title = "账单通知"

    pusher = DingtalkPusher(access_token, secret)
    pusher.send(message, title)
