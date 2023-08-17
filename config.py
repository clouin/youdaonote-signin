import configparser
from pathlib import Path

CONFIG_PATH = Path('config.ini')


def get_default_config() -> configparser.ConfigParser:
    conf = configparser.ConfigParser()

    conf['account'] = {
        'username': '',
        'password': ''
    }

    conf['dingtalk'] = {
        'access_token': '',
        'secret': ''
    }

    conf['schedule'] = {
        'time': '08:00'
    }

    return conf


class ConfigManager:

    def __init__(self) -> None:
        if not CONFIG_PATH.exists():
            self.config = get_default_config()
            with CONFIG_PATH.open('w') as f:
                self.config.write(f)
        else:
            self.config = configparser.ConfigParser()
            self.config.read(CONFIG_PATH)


if __name__ == '__main__':
    config = ConfigManager().config
