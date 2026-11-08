#!/usr/bin/env bash
# 在 Ubuntu 服务器上初始化并启动 Tallywise。
# 首次运行会安装 Docker；安装完成后需要重新登录，再运行一次本脚本。
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/8ight1een/-Tallywise.git}"
APP_DIR="${APP_DIR:-$HOME/tallywise}"

if ! command -v docker >/dev/null 2>&1; then
  echo "未检测到 Docker，开始安装..."
  curl -fsSL https://get.docker.com | sh
  echo "Docker 已安装，请重新登录（或执行 newgrp docker）后再次运行本脚本。"
  exit 0
fi

docker compose version >/dev/null

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  password="$(openssl rand -hex 16)"
  secret="$(openssl rand -hex 32)"
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$password|" .env
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$secret|" .env
  chmod 600 .env
  echo "已生成 .env（随机密码与密钥）"
fi

docker compose -f compose.yaml -f compose.prod.yaml up -d --build
docker compose ps
