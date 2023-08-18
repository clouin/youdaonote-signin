import configparser
import re
from pathlib import Path

CONFIG_PATH = Path('config.ini')

DEFAULT_CONFIG = {
    'account': {
        'username': '',
        'password': '',
        'retry_times': 3
    },
    'dingtalk': {
        'access_token': '',
        'secret': ''
    },
    'schedule': {
        'time': '08:00'
    },
    'log': {
        'loglevel': 'INFO'
    }
}


class ConfigManager:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read_dict(DEFAULT_CONFIG)

        if CONFIG_PATH.exists():
            self.config.read(CONFIG_PATH)

        self.save()
        self.validate()

    def save(self):
        with CONFIG_PATH.open('w') as f:
            self.config.write(f)

    def validate(self):
        self._validate_loglevel()
        self._validate_retry_times()
        self._validate_schedule_time()

    def _validate_loglevel(self):
        level = self.get('log', 'loglevel')
        options = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if level not in options:
            raise ValueError(f'日志级别配置不合法:{level},可选项:{options}')

    def _validate_retry_times(self):
        times = self.getint('account', 'retry_times')
        if times < 0:
            raise ValueError('重试次数不合法')

    def _validate_schedule_time(self):
        time_pattern = r'^([01]\d|2[0-3]):[0-5]\d$'
        time = self.get('schedule', 'time')
        if not re.match(time_pattern, time):
            raise ValueError(f'定时时间格式不正确:{time}')

    def get(self, section, option, fallback=None):
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def getint(self, section, option, fallback=None):
        try:
            return self.config.getint(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback


if __name__ == '__main__':
    config = ConfigManager()

    for section in config.config.sections():
        print(f'[{section}]')
        for option, value in config.config.items(section):
            print(f'{option} = {value}')
