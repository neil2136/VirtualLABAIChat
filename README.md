# VLab Device Management System

## 项目简介

VLab 设备管理系统是一个基于 Flask 的 Web 应用，提供设备管理、用户认证和 AI 对话功能。系统集成了 AI Agent 服务，支持通过自然语言查询、借用和归还设备。
<img width="1865" height="1032" alt="image" src="https://github.com/user-attachments/assets/421132d3-d08f-4644-a0a2-114ba631a40f" />
https://github.com/neil2136/VirtualLABAIChat/issues/1#issue-4610913248

## 主要功能

- **设备管理**: 查询 DUT 设备信息，包括设备状态、拥有者、使用者等
- **设备借用/归还**: 支持设备借用和归还操作
- **AI 对话**: 通过自然语言与 AI Agent 交互，完成设备查询和管理
- **用户认证**: 基于 Flask-Login 的用户登录和权限管理
- **邮件通知**: 设备借用/归还邮件通知功能

## 技术栈

### 后端
- **Flask**: Web 框架
- **Flask-Login**: 用户认证
- **Flask-Bootstrap**: UI 框架
- **Flask-Mail**: 邮件发送
- **MongoDB**: 数据存储
- **pymongo**: MongoDB Python 驱动

### AI Agent (agentd)
- **FastAPI**: AI Agent Web 框架
- **pydantic-ai**: AI Agent 框架
- **Uvicorn**: ASGI 服务器
- **OpenAI API**: LLM 接口

### 前端
- **Bootstrap**: UI 组件库
- **jQuery**: JavaScript 框架
- **SSE**: Server-Sent Events 流式响应

## 项目结构

```
/github/VirtualLABAIChat/app/
├── __init__.py              # Flask 应用工厂
├── agentd/                 # AI Agent 服务
│   ├── agentd/             # AI Agent 核心代码
│   │   ├── agents/         # Agent 定义和工具
│   │   ├── api/            # FastAPI 路由
│   │   ├── infrastructure/ # 基础设施（MongoDB 连接等）
│   │   └── domain/         # 领域模型
│   ├── app.py              # Agentd 入口文件
│   ├── .env                # 环境变量配置
│   ├── requirements.txt    # Python 依赖
│   ├── restart_agentd.py   # 服务管理脚本
│   └── docker/             # Docker 配置
│       ├── Dockerfile
│       └── docker-compose.yml
├── api/                    # Flask API 路由
│   └── views.py            # API 端点实现
├── auth/                   # 用户认证
│   ├── __init__.py
│   ├── forms.py            # 认证表单
│   └── views.py            # 认证视图
├── main/                   # 主应用视图
│   ├── views.py            # 主页面视图
│   ├── forms.py            # 表单定义
│   └── tasks.py            # 后台任务
├── templates/              # HTML 模板
│   └── bootstrap/          # Bootstrap 模板
│       └── topnav.html     # 导航栏和 AI Chat 模态框
├── static/                 # 静态文件
├── skills/                 # 技能文档
│   ├── add_ai_agent_to_local_skill.md
│   └── ai_chat_vlab_skill.md
├── models.py               # 数据模型
├── decorators.py           # 装饰器
├── email.py                # 邮件功能
└── lib/                    # 工具库
```

## 快速开始

### 前置条件

- Python 3.8+
- MongoDB 4.0+
- Docker (可选，用于部署 agentd)
- Flask 应用依赖

### 安装步骤

#### 1. 安装 Flask 应用依赖

```bash
cd /github/VirtualLABAIChat/app
source .venv/bin/activate  # 激活虚拟环境
pip install -r requirements.txt
```

#### 2. 配置环境变量

编辑 Flask 配置文件 `config.py` 或环境变量：

```python
# 数据库配置
MONGODB_URI = "mongodb://10.103.2.40:27017"
MONGODB_DATABASE = "VL"

# 邮件配置
MAIL_SERVER = "smtp.example.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = "your-email@example.com"
MAIL_PASSWORD = "your-password"
```

#### 3. 启动 Flask 应用

```bash
cd /github/VirtualLABAIChat/app
python run.py
```

应用默认运行在 `http://localhost:5000`

### 部署 AI Agent (agentd)

#### 方式 1: Docker 部署（推荐）

```bash
cd /github/VirtualLABAIChat/app/agentd

# 生成 TLS 证书
mkdir -p certs
openssl req -x509 -newkey rsa:4096 \
    -keyout certs/server.key \
    -out certs/server.crt \
    -days 3650 -nodes \
    -subj "/CN=10.103.2.128" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:10.103.2.128"

# 配置 .env 文件（参考 agentd/.env.example）

# 构建 Docker 镜像
docker build -f docker/Dockerfile -t agentd:v0.1 .

# 启动容器
docker run -d \
    --name agentd \
    -p 10443:10443 \
    -v /github/VirtualLABAIChat/app/agentd/.env:/app/.env \
    -v /github/VirtualLABAIChat/app/agentd/certs:/app/certs \
    --restart unless-stopped \
    agentd:v0.1
```

#### 方式 2: 直接 Python 运行

```bash
cd /github/VirtualLABAIChat/app/agentd
source /github/VirtualLABAIChat/app/.venv/bin/activate
pip install -r requirements.txt
python app.py
```

或使用管理脚本：

```bash
python restart_agentd.py --force
```

### 验证服务

```bash
# Flask 应用
curl https://localhost

# AI Agent 健康检查
curl -k https://10.103.2.128:10443/health
# 预期输出: {"status":"ok","service":"agentd","version":"0.1.0"}
```

## AI Chat 功能

### 使用说明

1. 登录 VLab 系统
2. 点击顶部导航栏的 "Local AI Chat" 按钮
3. 在对话框中输入自然语言查询，例如：
   - "list my device" - 查看我的设备
   - "search tz570p" - 搜索 tz570p 设备
   - "borrow device 82" - 借用设备 82
   - "return device 82" - 归还设备 82

### AI Agent 配置

编辑 `/github/VirtualLABAIChat/app/agentd/.env`：

```bash
# LLM 配置
MODEL_NAME="glm-4-flash"
MODEL_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
MODEL_API_KEY="your-api-key"

# MongoDB 配置
MONGODB_URI=mongodb://10.103.2.40:27017
MONGODB_DATABASE=VL

# REST API 配置（指向 Flask 应用）
REST_API_SERVICES_JSON={"device_action_api":{"base_url":"https://10.103.2.128",...}}
```

## 设备查询功能

### 支持的查询方式

1. **自然语言查询**: 通过 AI Chat 对话查询
2. **精确查询**: 按设备 ID、序列号、型号等字段查询
3. **模糊查询**: 支持关键词匹配
4. **我的设备**: 查询拥有或正在使用的设备

### 查询字段

- `Owner`: 设备拥有者
- `User`: 当前使用者
- `Product`: 产品型号
- `SN`: 序列号
- `Group`: 设备分组
- `Description`: 设备描述
- `Rack`: 机架位置

## 管理命令

### AI Agent 管理

```bash
# 查看状态
docker ps | grep agentd

# 查看日志
docker logs -f agentd

# 重启服务
docker restart agentd

# 停止服务
docker stop agentd

# 删除容器
docker rm -f agentd

# 使用管理脚本（Python 运行方式）
python restart_agentd.py --status
python restart_agentd.py --force
```

### Flask 应用管理

```bash
# HTTP 模式启动（端口 80）
cd /github/VirtualLABAIChat/
python manage.py runserver -h 0.0.0.0 -p 80

# HTTPS 模式启动（端口 443）
cd /github/VirtualLABAIChat/
python manage.py runserver -h 0.0.0.0 -p 443 --threaded --ssl-crt /opt/vlab/ca/vlabself.pem --ssl-key /opt/vlab/ca/vlab.key

# 启动 Celery Worker（后台任务）
cd /github/VirtualLABAIChat/
celery -A app.main.tasks.celery worker --loglevel=info

# 查看日志
tail -f logs/system.log
```

## API 端点

### Flask API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ai-search` | POST | AI 搜索接口 |
| `/api/borrow-device/<device_id>` | POST | 借用设备 |
| `/api/return-device/<device_id>` | POST | 归还设备 |
| `/local-ai/conversations` | POST | 创建 AI 会话 |
| `/local-ai/conversations/<id>/messages/stream` | POST | 流式 AI 对话 |

### AI Agent API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/conversations` | POST | 创建会话 |
| `/conversations/<id>/messages/stream` | POST | 流式消息 |

## 配置说明

### Flask 配置

主要配置文件：`config.py`

```python
class Config:
    # 数据库
    MONGODB_URI = "mongodb://localhost:27017"
    MONGODB_DATABASE = "vlab"
    
    # 邮件
    MAIL_SERVER = "smtp.example.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    
    # 日志
    LOG_LEVEL = logging.INFO
    LOG_SYSTEM_DIR = "logs/system.log"
```

### AI Agent 配置

配置文件：`agentd/.env`

```bash
# 服务配置
APP_HOST=0.0.0.0
APP_PORT=10443

# TLS 证书
TLS_CERT_FILE=certs/server.crt
TLS_KEY_FILE=certs/server.key

# LLM 配置
MODEL_NAME="glm-4-flash"
MODEL_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
MODEL_API_KEY="your-api-key"

# MongoDB 配置
MONGODB_URI=mongodb://10.103.2.40:27017
MONGODB_DATABASE=VL
```

## 故障排查

### AI Agent 连接失败

```bash
# 检查服务状态
docker ps | grep agentd

# 检查端口占用
lsof -i :10443

# 查看日志
docker logs agentd

# 强制重启
python restart_agentd.py --force
```

### 设备查询无结果

1. 检查 MongoDB 连接
2. 确认数据库中有设备数据
3. 检查查询字段是否正确
4. 查看 AI Agent 日志

### 邮件发送失败

1. 检查 SMTP 配置
2. 确认邮箱密码正确
3. 检查防火墙是否阻止 SMTP 端口

## 开发指南

### 添加新的 AI 工具

1. 在 `agentd/agentd/agents/tools/` 中创建新工具
2. 在 `agentd/agentd/agents/chat_agent.py` 中注册工具
3. 更新工具文档字符串
4. 重启 AI Agent 服务

### 添加新的 API 端点

1. 在 `api/views.py` 中添加路由
2. 实现业务逻辑
3. 更新前端调用
4. 测试 API

## 相关文档

- [AI Agent 部署文档](skills/add_ai_agent_to_local_skill.md)
- [AI Chat 集成文档](skills/ai_chat_vlab_skill.md)

## 许可证

内部使用

## 维护者

VLab Team

## 更新日志

### v1.0.0 (2026-04-29)
- 初始版本发布
- 集成 AI Agent 服务
- 支持设备查询、借用、归还
- 支持 AI 对话功能
- 支持个性化问候语
- 支持 "我的设备" 查询（同时匹配 Owner 和 User）



# VLab 设备管理系统 前端模块功能说明书
## 目录
1. [全局顶部操作栏](#一全局顶部操作栏)
2. [左侧主导航菜单](#二左侧主导航菜单)
3. [右上角辅助功能区](#三右上角辅助功能区)
4. [主数据概览仪表盘](#四主数据概览仪表盘)
5. [文档说明](#文档说明)

## 一、全局顶部操作栏
**功能说明**：系统核心业务模块的全局快速入口，固定在页面顶部，所有页面均可访问，支持跨模块一键跳转。

| 模块名称 | 功能描述 | 适用用户角色 | 典型使用场景 |
|:---------|:---------|:-------------|:-------------|
| Refresh | 一键刷新当前页面所有数据，同步最新的设备状态、统计指标和日志信息 | 所有用户 | 测试前刷新确认设备可用状态；管理员实时查看系统负载 |
| VM Mgmt. | 虚拟机全生命周期管理，支持创建、删除、启停、快照、资源配置和权限分配 | 普通用户<br>团队管理员<br>系统管理员 | 测试工程师创建专属测试虚拟机；管理员回收闲置虚拟机资源 |
| DUT Mgmt. | 被测设备(Device Under Test)管理，负责设备注册、状态监控、领用/归还和报废流程 | 普通用户<br>团队管理员<br>系统管理员 | 工程师领用网络设备进行功能测试；管理员跟踪设备生命周期 |
| PC Mgmt. | 测试终端(台式机/笔记本)管理，统一管理硬件配置、系统镜像和远程访问权限 | 普通用户<br>团队管理员<br>系统管理员 | 远程连接测试PC执行自动化脚本；管理员批量部署测试环境 |
| Devices Search | 全局设备搜索引擎，支持按类型、型号、SN号、状态、归属人多维度检索 | 所有用户 | 快速查找特定型号的空闲设备；定位故障设备的位置和状态 |
| VLAN Search | 虚拟局域网查询工具，可查看VLAN配置、端口关联、IP段分配和使用状态 | 所有用户 | 测试前确认目标VLAN的可用IP；排查网络连通性问题 |
| Public Testbed | 公共测试床入口，提供团队共享的标准化测试环境预约和使用功能 | 所有用户 | 预约大型组网测试环境；使用共享的高性能测试设备 |
| Enhancement | 系统扩展功能模块，包含高级配置、插件管理、定制化工具和第三方集成 | 系统管理员 | 安装自动化测试插件；配置与CI/CD系统的对接 |

## 二、左侧主导航菜单
**功能说明**：系统功能的完整分类导航，按用户权限动态显示可访问模块，清晰区分个人资源和全局管理能力。

| 模块名称 | 功能描述 | 适用用户角色 | 典型使用场景 |
|:---------|:---------|:-------------|:-------------|
| My Devices | 个人设备中心，查看和管理当前用户名下已分配的所有设备资源 | 普通用户<br>团队管理员 | 查看自己领用的设备列表；归还不再使用的设备 |
| My VMs | 个人虚拟机管理，展示用户创建或授权使用的虚拟机，支持一键启停和控制台访问 | 普通用户<br>团队管理员 | 启动测试虚拟机；创建系统快照用于测试回滚 |
| My VLANs | 个人VLAN配置，管理用户专属的虚拟局域网和网络访问策略 | 普通用户<br>团队管理员 | 配置测试环境的网络隔离；添加端口转发规则 |
| Devices Summary | 全局设备总览，展示系统所有设备的分类统计、在线率和资源利用率 | 团队管理员<br>系统管理员 | 查看团队设备使用情况；统计整体设备闲置率 |
| Auto Tools | 自动化工具集，提供设备批量配置、测试脚本执行、定时任务和结果报告 | 普通用户<br>团队管理员 | 批量配置多台设备的基础参数；定时执行回归测试 |
| Public Testbed | 公共测试环境入口，与顶部按钮功能一致，支持共享资源的预约和使用 | 所有用户 | 查看公共测试床的预约日历；提交环境使用申请 |
| Switch config | 交换机配置管理，可视化配置网络交换机的端口、VLAN、路由和ACL策略 | 网络管理员<br>系统管理员 | 划分测试网段；配置端口镜像用于流量分析 |
| VLAB MDMT | 多设备批量管理工具，支持对指定设备组执行统一的升级、巡检和配置推送 | 团队管理员<br>系统管理员 | 批量升级设备固件；执行全系统设备健康检查 |
| VLAB LOG | 系统日志中心，汇总设备操作日志、系统运行日志、错误告警和安全事件 | 系统管理员<br>安全管理员 | 排查设备配置失败原因；审计用户的敏感操作 |

## 三、右上角辅助功能区
**功能说明**：提供系统辅助功能和用户相关入口，固定在页面右上角，全局可访问。

| 模块名称 | 功能描述 | 适用用户角色 | 典型使用场景 |
|:---------|:---------|:-------------|:-------------|
| 用户信息 | 显示当前登录用户名，提供个人资料修改、密码重置和安全退出功能 | 所有用户 | 修改个人联系信息；定期更换登录密码 |
| Local AI Chat | 集成的本地AI对话助手，可辅助解决设备配置问题、故障排查和操作指导 | 所有用户 | 咨询特定设备的配置命令；获取故障排查步骤 |
| 消息通知 | 系统通知中心，展示设备告警、任务完成提醒、审批通知和系统公告 | 所有用户 | 接收设备离线告警；查看自动化测试完成通知 |
| 系统更新 | 提示系统版本更新状态，支持一键升级到最新稳定版本 | 系统管理员 | 升级系统修复已知漏洞；获取新功能特性 |

## 四、主数据概览仪表盘
**功能说明**：系统首页默认展示的核心数据面板，直观呈现系统运行状态、资源使用情况和用户行为统计。

| 模块名称 | 功能描述 | 适用用户角色 | 典型使用场景 |
|:---------|:---------|:-------------|:-------------|
| 核心KPI统计卡片 | 展示系统关键运行指标：DUT/SP使用量、VM总数、交换机总数、有效/无效配置数、登录总次数 | 所有用户 | 快速了解系统整体负载；确认当前可用资源数量 |
| 用户配置频率分析 | 柱状图展示指定团队上周各成员的配置操作总次数，对比工作活跃度 | 团队管理员<br>系统管理员 | 评估团队成员工作量；识别需要技术支持的成员 |
| Top Devices usage | 展示上周使用次数最多的设备排行榜，按使用频次降序排列 | 团队管理员<br>系统管理员 | 识别热门设备资源；提前规划设备采购和负载均衡 |
| Top Users usage | 展示上周系统操作最活跃的用户排行榜，反映系统使用强度 | 团队管理员<br>系统管理员 | 了解核心用户群体；优化技术支持优先级 |
| Users Failure rate | 环形图展示不同项目模块的配置失败率占比，标注具体百分比 | 开发人员<br>系统管理员 | 快速定位问题高发模块；针对性进行代码优化 |
| Users Log | 表格形式展示所有用户的登录审计信息，包含用户名、登录IP、结果和时间戳 | 系统管理员<br>安全管理员 | 排查用户登录失败问题；审计异常登录行为 |

## 文档说明
1. 本文档基于 VLab 系统主仪表盘页面整理，适用于 v1.0 及以上版本
2. 用户角色定义：
   - **普通用户**：测试工程师，主要使用系统资源执行测试任务
   - **团队管理员**：负责团队内部资源分配、使用统计和成员管理
   - **系统管理员**：负责系统全局配置、维护、安全审计和版本升级
3. 后续系统功能更新需同步维护本文档，新增模块请按上述表格格式补充
{"$mid":24,"mimeType":"cache_control","data":"ZXBoZW1lcmFs"}
