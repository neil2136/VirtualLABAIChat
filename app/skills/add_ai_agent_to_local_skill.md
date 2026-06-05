# Skill: Add AI Agent to Local

## 功能描述

将 AI Agent 服务（agentd）部署到本地 Flask 主机，提供设备查询、借用、归还等 AI 对话功能。

## 前置条件

- Docker 已安装并可运行
- 目标主机 IP: `10.103.2.128`
- Flask 应用运行在同一主机
- MongoDB 可访问（如 `10.103.2.40:27017`）

## 安装步骤

### 1. 生成 TLS 证书（10年期）

```bash
cd /opt/vlab/flasky/app/agentd
mkdir -p certs

openssl req -x509 -newkey rsa:4096 \
    -keyout certs/server.key \
    -out certs/server.crt \
    -days 3650 -nodes \
    -subj "/CN=10.103.2.128" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:10.103.2.128"
```

### 2. 创建 .env 配置文件

```bash
cat > /opt/vlab/flasky/app/agentd/.env << 'EOF'
# === 服务配置 ===
APP_HOST=0.0.0.0
APP_PORT=10443

# === TLS证书 ===
TLS_CERT_FILE=certs/server.crt
TLS_KEY_FILE=certs/server.key

# === CORS配置 ===
CORS_ALLOW_ORIGINS=["https://10.103.2.128","http://10.103.2.128","https://localhost","http://localhost"]

# === LLM 配置 ===
#MODEL_NAME="qwen3.5:0.8b"
#MODEL_BASE_URL="http://10.8.66.50:11434/v1"
#MODEL_API_KEY=ollama
MODEL_NAME="glm-4-flash"
MODEL_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
MODEL_API_KEY="your-api-key-here"

# === MongoDB 配置 ===
MONGODB_URI=mongodb://10.103.2.40:27017
MONGODB_DATABASE=vlab

# === MongoDB 资源配置 ===
MONGODB_RESOURCES_JSON={"dut_search":{"collection":"DUT","description":"Search DUT devices and return id, SN and Owner","filter_fields":{"User":{"document_path":"User","field_type":"string","string_match_mode":"contains"},"Owner":{"document_path":"Owner","field_type":"string","string_match_mode":"contains"},"Group":{"document_path":"Group","field_type":"string","string_match_mode":"contains"},"Description":{"document_path":"Description","field_type":"string","string_match_mode":"contains"},"Rack":{"document_path":"Rack","field_type":"string","string_match_mode":"contains"},"Product":{"document_path":"Product","field_type":"string","string_match_mode":"contains"},"classify":{"document_path":"classify","field_type":"string","string_match_mode":"contains"},"id":{"document_path":"id","field_type":"string","string_match_mode":"exact"},"Operator":{"document_path":"Operator","field_type":"string","string_match_mode":"contains"},"DeviceType":{"document_path":"DeviceType","field_type":"string","string_match_mode":"contains"},"ProductType":{"document_path":"ProductType","field_type":"string","string_match_mode":"contains"},"FWScripts":{"document_path":"FWScripts","field_type":"string","string_match_mode":"contains"},"SN":{"document_path":"SN","field_type":"string","string_match_mode":"contains"},"ConsoleManager":{"document_path":"ConsoleInfo.ConsoleManager","field_type":"string","string_match_mode":"contains"},"TelnetPort":{"document_path":"ConsoleInfo.TelnetPort","field_type":"string","string_match_mode":"contains"},"SSHPort":{"document_path":"ConsoleInfo.SSHPort","field_type":"string","string_match_mode":"contains"},"PowerController":{"document_path":"PowerInfo.PowerController","field_type":"string","string_match_mode":"contains"},"PowerChannel":{"document_path":"PowerInfo.PowerChannel","field_type":"string","string_match_mode":"contains"},"FWVersion":{"document_path":"FWStatus.version","field_type":"string","string_match_mode":"contains"},"FWUptime":{"document_path":"FWStatus.uptime","field_type":"string","string_match_mode":"contains"}},"projection_fields":["id","SN","Product","ProductType","Owner","User","Group","Rack","Description","classify","DeviceType","ConsoleInfo","PowerInfo","Firmware","FWStatus"],"keyword_paths":["SN","Product","Owner","id","User","Group","Rack","Description","ProductType","DeviceType","classify","ConsoleInfo.ConsoleManager"],"sort":[["id",1]],"limit":20,"retry_count":3}}

# === REST API 配置（指向 Flask 自身） ===
REST_API_SERVICES_JSON={"device_action_api":{"base_url":"https://10.103.2.128","auth_type":"none","auth_config":{},"timeout_seconds":10,"retry_count":2,"resources":{"borrow_device":{"method":"POST","path":"/api/borrow-device/{device_id}","description":"Borrow a device by id."},"return_device":{"method":"POST","path":"/api/return-device/{device_id}","description":"Return a device by id."}}}}

# === 应用配置 ===
SESSION_TTL_SECONDS=1800
MAX_CONVERSATION_MESSAGES=100
TRUSTED_USER_HEADER=X-User-Id
LOG_LEVEL=INFO
EOF
```

### 3. 更新 Flask 代理配置

编辑 `/opt/vlab/flasky/app/api/views.py`，更新 AI Agent 地址：

```python
# Local AI Agent Configuration
LOCAL_AI_BASE_URL = "https://10.103.2.128:10443"
LOCAL_AI_TIMEOUT = 30
```

### 4. 构建 Docker 镜像

```bash
cd /opt/vlab/flasky/app/agentd

docker build -f docker/Dockerfile -t agentd:v0.1 .
```

### 5. 启动 Docker 容器

```bash
docker run -d \
    --name agentd \
    -p 10443:10443 \
    -v /opt/vlab/flasky/app/agentd/.env:/app/.env \
    -v /opt/vlab/flasky/app/agentd/certs:/app/certs \
    --restart unless-stopped \
    agentd:v0.1
```

或使用 docker-compose:
```bash
cd /opt/vlab/flasky/app/agentd/docker
docker-compose up -d
```

### 6. 验证服务

```bash
# 健康检查
curl -k https://10.103.2.128:10443/health

# 预期输出: {"status":"ok","service":"agentd","version":"0.1.0"}
```

## 管理命令

```bash
# 查看日志
docker logs -f agentd

# 重启服务
docker restart agentd

# 停止服务
docker stop agentd

# 删除容器（保留镜像）
docker rm -f agentd

# 重新创建容器
docker run -d --name agentd -p 10443:10443 \
    -v /opt/vlab/flasky/app/agentd/.env:/app/.env \
    -v /opt/vlab/flasky/app/agentd/certs:/app/certs \
    --restart unless-stopped agentd:v0.1
```

## 目录结构（精简后）

```
/opt/vlab/flasky/app/agentd/
├── .env              # 环境变量配置
├── agentd/           # 核心代码
├── app.py            # 入口文件
├── certs/            # TLS证书
│   ├── server.crt
│   └── server.key
└── docker/           # Docker配置
    ├── Dockerfile
    └── docker-compose.yml
```

## 配置修改后重启

```bash
# 修改 .env 后，重启容器使配置生效
docker restart agentd
```

## 防火墙配置

确保防火墙允许 10443 端口：

```bash
# iptables
iptables -A INPUT -p tcp --dport 10443 -j ACCEPT

# 或 firewalld
firewall-cmd --permanent --add-port=10443/tcp
firewall-cmd --reload
```

## 相关技能

- `ai_chat_vlab_skill.md` - VLab 前端 AI Chat 集成
- `agentd_design_skill.md` - Agentd 架构设计文档

---

**维护者**: VLab Team  
**版本**: 1.0.0  
**更新日期**: 2026-04-27
