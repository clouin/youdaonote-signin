import glob
import hashlib
import logging
import os
import random
import time
from datetime import datetime, timedelta

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
        self.password = hashlib.md5(password.encode("utf-8")).hexdigest()
        self.session = requests.Session()
        self.retry_times = retry_times
        self.username_mask = self._mask_username(username)

        # 从配置获取验证码长度要求
        captcha_length_str = config["account"].get("captcha_length", "")
        self.captcha_length = int(captcha_length_str) if captcha_length_str else None

    @staticmethod
    def _mask_username(username: str) -> str:
        """掩盖用户名"""
        if len(username) > 4:
            return username[:2] + "*" * (len(username) - 4) + username[-2:]
        return "****"

    @staticmethod
    def random_sleep(min_sleep: int = 5, max_sleep: int = 20) -> None:
        """随机睡眠一段时间"""
        random_seconds = random.randint(min_sleep, max_sleep)
        logging.debug(f"Sleeping for {random_seconds} seconds")
        time.sleep(random_seconds)

    def send_request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.random_sleep()
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def get_captcha(self) -> str:
        """获取验证码"""
        captcha_url = "https://note.youdao.com/login/acc/urs/verify/get?app=client&product=YNOTE&ClientVer=61000010000&GUID=PCe3ea009f17ce4a46c&client_ver=61000010000&device_id=PCe3ea009f17ce4a46c&device_name=DESKTOP-0PK60BL&device_type=PC&keyfrom=pc&os=Windows&os_ver=Windows%2010&vendor=website&vendornew=website"

        # 创建验证码文件夹
        captcha_dir = "captchas"
        os.makedirs(captcha_dir, exist_ok=True)

        # 清理2天前的验证码图片
        self._cleanup_old_captchas(captcha_dir)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                captcha_res = self.send_request("GET", captcha_url)

                # 使用日期时间命名验证码文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                captcha_filename = os.path.join(captcha_dir, f"captcha_{timestamp}.png")

                with open(captcha_filename, "wb") as f:
                    f.write(captcha_res.content)

                ocr = ddddocr.DdddOcr(show_ad=False)
                result = ocr.classification(captcha_res.content)
                captcha_code = str(result) if result else ""

                # 将识别结果写入文件名
                result_filename = os.path.join(captcha_dir, f"captcha_{timestamp}_{captcha_code}.png")
                os.rename(captcha_filename, result_filename)

                # 检查验证码长度
                if self.captcha_length is None:
                    # 未配置长度要求，直接返回
                    logging.debug(f"成功获取验证码: {captcha_code} (未配置长度要求，保存为: {result_filename})")
                    return captcha_code
                elif len(captcha_code) == self.captcha_length:
                    logging.debug(f"成功获取{self.captcha_length}位验证码: {captcha_code} (保存为: {result_filename})")
                    return captcha_code
                else:
                    logging.warning(
                        f"获取到的验证码长度不符合要求: '{captcha_code}' (长度: {len(captcha_code)}，期望: {self.captcha_length})，第{attempt + 1}次重试"
                    )

            except requests.RequestException as e:
                logging.exception(f"获取验证码失败: {e}，第{attempt + 1}次重试")

        logging.error(f"获取验证码失败，重试{max_retries}次后仍未获取到符合要求的验证码")
        return ""

    def _cleanup_old_captchas(self, captcha_dir: str = "captchas") -> None:
        """清理2天前的验证码图片"""
        try:
            # 确保目录存在
            if not os.path.exists(captcha_dir):
                return

            # 查找所有captcha_*.png文件
            captcha_files = glob.glob(os.path.join(captcha_dir, "captcha_*.png"))
            cutoff_date = datetime.now() - timedelta(days=2)

            for file_path in captcha_files:
                try:
                    # 从文件名提取时间戳（文件名格式：captcha_YYYYMMDD_HHMMSS_验证码.png）
                    filename = os.path.basename(file_path)
                    if filename.startswith("captcha_") and filename.endswith(".png"):
                        name_parts = filename[8:-4].split("_")
                        if len(name_parts) >= 3:  # 文件名必须有3个部分：日期、时间、验证码
                            date_part = name_parts[0]
                            time_part = name_parts[1]
                            timestamp_str = f"{date_part}_{time_part}"
                            file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                            # 如果文件超过2天，删除它
                            if file_date < cutoff_date:
                                os.remove(file_path)
                                logging.debug(f"删除旧验证码图片: {file_path}")

                except (ValueError, OSError) as e:
                    logging.warning(f"处理验证码文件 {file_path} 时出错: {e}")

        except Exception as e:
            logging.warning(f"清理旧验证码图片时出错: {e}")

    def login(self) -> bool:
        """登录"""
        login_url = "https://note.youdao.com/login/acc/urs/verify/check?product=YNOTE&app=client&ClientVer=61000010000&GUID=PCe3ea009f17ce4a46c&client_ver=61000010000&device_id=PCe3ea009f17ce4a46c&device_name=DESKTOP-0PK60BL&device_type=PC&keyfrom=pc&os=Windows&os_ver=Windows%2010&vendor=website&vendornew=website&show=true&tp=urstoken&cf=6"
        data = {"username": self.username, "password": self.password}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        for i in range(self.retry_times + 1):
            captcha_code = self.get_captcha()
            try:
                res = self.send_request("POST", login_url, data=data, headers=headers, params={"vcode": captcha_code})
                if res.status_code == 200:
                    logging.info("登录成功")
                    return True
                logging.error(f"登录失败：{res.text}，验证码：{captcha_code}")
                if i < self.retry_times:
                    logging.info(f"登录失败，将进行第{i + 1}次重试")
                    self.session.cookies.clear()
            except requests.RequestException as e:
                logging.info(f"登录失败：{e}，将进行第{i + 1}次重试")
        logging.exception(f"登录失败，重试{self.retry_times}次未成功")
        return False

    def sign(self) -> str:
        """签到"""
        checkin_url = "https://note.youdao.com/yws/mapi/user?method=checkin"
        try:
            res = self.send_request("POST", checkin_url)
            if res.status_code != 200:
                msg = f"签到失败：{res.text}"
                logging.exception(msg)
                return msg

            info = res.json()
            if not isinstance(info, dict):
                return "签到失败：返回数据格式错误"

            total = float(info.get("total", 0)) / 1024 / 1024
            space = float(info.get("space", 0)) / 1024 / 1024
            timestamp = info.get("time", 0)
            if timestamp:
                time_string = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000))
            else:
                time_string = "未知时间"

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
            return f"签到失败:{e}"


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
        message = signer.sign()
    else:
        message = f"{signer.username_mask} 登录失败，重试{signer.retry_times}次未成功"

    # 推送消息
    pusher = DingtalkPusher(config["dingtalk"]["access_token"], config["dingtalk"]["secret"])
    pusher.send(message, "有道云笔记签到通知")


def main() -> None:
    """程序入口"""
    schedule.every().day.at(config["schedule"]["time"]).do(run_sign)

    next_run = schedule.next_run()
    if next_run:
        logging.info(f"Scheduling first run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logging.info("调度已设置，但尚未计算下次运行时间")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
