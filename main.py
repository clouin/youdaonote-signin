import logging
import hashlib
import time
import requests
import ddddocr
import schedule

from config import ConfigManager
from notify.dingtalk import DingtalkPusher

logging.basicConfig(level=logging.INFO)

config = ConfigManager().config


class YoudaoSign:

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.username_mask = '****'
        self.password = hashlib.md5(password.encode('utf-8')).hexdigest()
        self.session = requests.Session()

        if len(username) > 4:
            self.username_mask = username[:2] + '*' * int((len(username) - 4) / 2) + username[-2:]

    def get_captcha(self) -> str:
        try:
            captcha_url = 'https://note.youdao.com/login/acc/urs/verify/get?app=client&product=YNOTE&ClientVer=61000010000&GUID=PCe3ea009f17ce4a46c&client_ver=61000010000&device_id=PCe3ea009f17ce4a46c&device_name=DESKTOP-0PK60BL&device_type=PC&keyfrom=pc&os=Windows&os_ver=Windows%2010&vendor=website&vendornew=website'
            captcha_res = self.session.get(captcha_url)
            # with open('captcha.png', 'wb') as f:
            #     f.write(captcha_res.content)
            ocr = ddddocr.DdddOcr(show_ad=False)
            return ocr.classification(captcha_res.content)
        except Exception as e:
            logging.exception(e)
            raise e

    def login(self) -> None:
        try:
            captcha_code = self.get_captcha()
            login_url = 'https://note.youdao.com/login/acc/urs/verify/check?product=YNOTE&app=client&ClientVer=61000010000&GUID=PCe3ea009f17ce4a46c&client_ver=61000010000&device_id=PCe3ea009f17ce4a46c&device_name=DESKTOP-0PK60BL&device_type=PC&keyfrom=pc&os=Windows&os_ver=Windows%2010&vendor=website&vendornew=website&show=true&tp=urstoken&cf=6&vcode=' + captcha_code
            payload = {
                'username': self.username,
                'password': self.password
            }
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            res = self.session.post(login_url, data=payload, headers=headers)
            if res.status_code != 200:
                raise Exception(f'登录失败:{res.text}')
        except Exception as e:
            logging.exception(e)
            raise e

    def sign(self) -> str:
        try:
            checkin_url = 'https://note.youdao.com/yws/mapi/user?method=checkin'
            res = self.session.post(checkin_url)
            info = res.json()

            if res.status_code != 200:
                raise Exception('签到失败')

            # 一共签到获得
            total = info['total'] / 1024 / 1024
            # 本次签到获得空间
            space = info['space'] / 1024 / 1024
            # 当前时间
            time_string = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info['time'] / 1000))

            message = [
                f'用户： {self.username_mask} 签到成功',
                f'签到时间：{time_string}',
                f'本次获得：{space:.1f}MB',
                f'总共获得：{total:.1f}MB'
            ]
            logging.info('，'.join(message))

            return '\n'.join(message)

        except Exception as e:
            logging.exception(e)
            raise e


def main():
    try:
        schedule_time = '08:00'
        if 'time' in config['schedule'] and config['schedule']['time']:
            schedule_time = config['schedule']['time']

        schedule.every().day.at(schedule_time).do(run_sign)

        next_run = schedule.next_run()
        next_run_formatted = next_run.strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Scheduling first run: {next_run_formatted}")

        while True:
            schedule.run_pending()
            time.sleep(1)

    except Exception as e:
        logging.exception(e)


def run_sign():
    try:
        username = config['account']['username']
        password = config['account']['password']
        if not username or not username:
            logging.error('请配置有道云笔记账号和密码')
            return
        signer = YoudaoSign(username, password)
        signer.login()
        message = signer.sign()

        # 推送消息
        access_token = config['dingtalk']['access_token']
        secret = config['dingtalk']['secret']
        if not access_token or not secret:
            logging.error('DingTalk 推送参数配置不完整')
            return
        pusher = DingtalkPusher(access_token, secret)
        pusher.send(message, "有道云笔记签到通知")

    except Exception as e:
        logging.exception(e)


if __name__ == '__main__':
    main()
