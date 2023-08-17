# 有道云笔记签到

该项目旨在实现有道云笔记的自动签到功能。

## 如何使用

在运行项目之前，请确保您已经创建了一个配置文件，并将其挂载到 Docker 容器中。请按照以下步骤进行操作：

1. 创建一个名为 config.ini 的配置文件。
2. 将以下示例配置复制到 config.ini 文件中：

```ini
[account]
username = your_username
password = your_password

[dingtalk]
access_token = your_access_token
secret = your_secret

[schedule]
time = 08:00
```

3. 将 config.ini 文件挂载到 Docker 容器中的 /app/config.ini 路径。

4. 运行该项目的命令如下：

```bash
docker run -d --name youdaonote-signin --restart=unless-stopped \
 -v /path/to/config.ini:/app/config.ini \
 jerryin/youdaonote-signin
```

或者使用 docker-compose：

```yaml
version: '3.8'

services:
  youdaonote-signin:
    image: jerryin/youdaonote-signin
    container_name: youdaonote-signin
    restart: unless-stopped
    volumes:
      - ./config.ini:/app/config.ini
```

请确保将 /path/to/config.ini 替换为您实际的配置文件路径。

## 如何获取钉钉自定义机器人 Webhook

您可以按照以下步骤获取钉钉自定义机器人的 Webhook：

1. 打开[自定义机器人官方说明](https://open.dingtalk.com/document/robots/custom-robot-access)
2. 建自定义机器人。
3. 获取生成的 Webhook URL，并将其用于配置文件中的 `access_token`和`secret`。

## 许可证

本项目基于 MIT 许可证发布，请查看 LICENSE 文件以获取更多信息。

## 联系信息

如果您有任何问题或反馈，请通过本项目的 GitHub 页面与我联系。