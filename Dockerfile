# use Python 3.10
FROM  python:3.10-slim-bullseye

LABEL maintainer = Jerry

# define timezone
ENV TZ Asia/Shanghai

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["python", "main.py"]