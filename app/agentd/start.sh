#!/bin/bash
# AI Agent 服务启动脚本 (Python 直接运行方式)

set -e

cd "$(dirname "$0")"

echo "=== Starting AI Agent Service ==="

# 加载环境变量
export $(grep -v '^#' .env | xargs)

# 启动服务
echo "Host: $APP_HOST"
echo "Port: $APP_PORT"
echo "TLS Cert: $TLS_CERT_FILE"
echo "TLS Key: $TLS_KEY_FILE"

exec python app.py
