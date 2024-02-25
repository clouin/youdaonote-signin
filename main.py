import hashlib
import logging
import time

import ddddocr
import requests
import schedule

from config import ConfigManager
from notify.dingtalk import DingtalkPusher

config = ConfigManager().config
logging.basicConfig(
    level=config["log"]["loglevel"],
    format='time="%(asctime)s" level="%(levelname)s" msg="%(message)s"',
    datefmt="%Y-%m-%d %H:%M:%S %Z",
)


class YoudaoSign:
    """有道云签到类"""

    def __init__(self, username: str, password: str, retry_times: int = 3) -> None:
        """初始化"""
        self.username = username
        self.username_mask = "****"
        self.password = hashlib.md5(password.encode("utf-8")).hexdigest()
        self.session = requests.Session()
        self.retry_times = retry_times
        self.retry_interval = 5

        if len(username) > 4:
            self.username_mask = (
                username[:2] + "*" * int((len(username) - 4) / 2) + username[-2:]
            )

    def get_captcha(self) -> str:
        """获取验证码"""
        try:
            captcha_url = "https://note.youdao.com/login/acc/urs/verify/get?app=client&product=YNOTE&ClientVer=61000010000&GUID=PCe3ea009f17ce4a46c&client_ver=61000010000&device_id=PCe3ea009f17ce4a46c&device_name=DESKTOP-0PK60BL&device_type=PC&keyfrom=pc&os=Windows&os_ver=Windows%2010&vendor=website&vendornew=website"
            captcha_res = self.session.get(captcha_url)
            with open("captcha.png", "wb") as f:
                f.write(captcha_res.content)
            ocr = ddddocr.DdddOcr(show_ad=False)
            return ocr.classification(captcha_res.content)
        except requests.RequestException as e:
            logging.exception(f"Failed to get captcha: {e}")

    def login(self) -> bool:
        """登录"""
        for i in range(self.retry_times + 1):
            try:
                captcha_code = self.get_captcha()
                time.sleep(5)

                login_url = "https://note.youdao.com/login/acc/urs/verify/check?product=YNOTE&app=client&ClientVer=61000010000&GUID=PCe3ea009f17ce4a46c&client_ver=61000010000&device_id=PCe3ea009f17ce4a46c&device_name=DESKTOP-0PK60BL&device_type=PC&keyfrom=pc&os=Windows&os_ver=Windows%2010&vendor=website&vendornew=website&show=true&tp=urstoken&cf=6"
                data = {"username": self.username, "password": self.password}
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                res = self.session.post(
                    login_url,
                    data=data,
                    headers=headers,
                    params={"vcode": captcha_code},
                )
                if res.status_code == 200:
                    logging.info("登录成功")
                    return True

                logging.error(f"登录失败：{res.text}，验证码：{captcha_code}")
                # 失败重试
                if i < self.retry_times:
                    logging.info(
                        f"登录失败，将在{self.retry_interval}秒后第{i + 1}次重试"
                    )
                    time.sleep(self.retry_interval)
                    logging.info(f"清空 cookie 前的会话状态：{self.session.cookies}")
                    self.session.cookies.clear()
                    logging.info(f"清空 cookie 后的会话状态：{self.session.cookies}")
            except requests.RequestException as e:
                logging.info(
                    f"登录失败：{e}，将在{self.retry_interval}秒后第{i + 1}次重试"
                )
        logging.exception(f"登录失败，重试{self.retry_times}次未成功")
        return False

    def sign(self) -> str:
        """签到"""
        try:
            checkin_url = "https://note.youdao.com/yws/mapi/user?method=checkin"
            res = self.session.post(checkin_url)
            info = res.json()
            if res.status_code != 200:
                msg = f"签到失败：{res.text}"
                logging.exception(msg)
                return msg

            total = info["total"] / 1024 / 1024
            space = info["space"] / 1024 / 1024
            time_string = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(info["time"] / 1000)
            )

            message = [
                f"用户： {self.username_mask} 签到成功",
                f"签到时间：{time_string}",
                f"本次获得：{space:.1f}MB",
                f"总共获得：{total:.1f}MB",
            ]
            logging.info("签到成功," + ",".join(message))
            return "\n".join(message)
        except Exception as e:
            logging.exception(f"签到失败:{e}")


def main() -> None:
    """程序入口"""
    schedule.every().day.at(config["schedule"]["time"]).do(run_sign)

    next_run = schedule.next_run()
    next_run_formatted = next_run.strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Scheduling first run: {next_run_formatted}")

    while True:
        schedule.run_pending()
        time.sleep(1)


def run_sign() -> None:
    """运行签到"""
    username = config["account"]["username"]
    password = config["account"]["password"]
    retry_times = int(config["account"]["retry_times"])
    if not username or not password:
        logging.exception("未配置有道云笔记账号和密码")
        return

    signer = YoudaoSign(username, password, retry_times)
    if signer.login():
        time.sleep(5)
        message = signer.sign()
    else:
        message = f"{signer.username_mask} 登录失败，重试{signer.retry_times}次未成功"

    # 推送消息
    access_token = config["dingtalk"]["access_token"]
    secret = config["dingtalk"]["secret"]
    if not access_token or not secret:
        logging.exception("DingTalk 推送参数配置不完整")
        return
    pusher = DingtalkPusher(access_token, secret)
    pusher.send(message, "有道云笔记签到通知")


if __name__ == "__main__":
    main()
