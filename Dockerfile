# Stage 1: Build stage
FROM python:3.10-slim-bullseye as builder

ENV TZ=Asia/Shanghai

# Prevent Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turn off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /build

COPY . .

# Install pip dependencies
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --upgrade -r requirements.txt \
    && python -m pip install pyarmor==7.*

# Obfuscate Python code
RUN pyarmor obfuscate --recursive main.py

# Stage 2: Runtime stage
FROM python:3.10-slim-bullseye

LABEL maintainer="Jerry"

ENV TZ=Asia/Shanghai

# Prevent Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turn off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install pip dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --upgrade -r requirements.txt

COPY --from=builder /build/dist .

CMD ["python", "main.py"]
