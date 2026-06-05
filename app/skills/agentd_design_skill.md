# Skill: Agentd - Local AI Agent Service

## 功能描述

Agentd 是一个基于 FastAPI + Pydantic-AI 构建的本地 AI Agent 服务，为 VLab 前端提供智能设备管理能力。用户可以通过自然语言对话完成设备查询、借用、归还等操作。

## 项目位置

- 服务入口: `/opt/vlab/flasky/app/agentd/app.py`
- 核心代码: `/opt/vlab/flasky/app/agentd/agentd/`
- 配置文件: `/opt/vlab/flasky/app/agentd/.env`

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agentd Service                           │
│                    (FastAPI + Pydantic-AI)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  API Layer  │  │Application  │  │   Domain    │  │Infrastructure│
│  │   (Routes)  │──│  Layer      │──│   Layer     │──│  Layer    │ │
│  │             │  │(Services)   │  │(Entities/  │  │(Connectors)│ │
│  │ • /health   │  │             │  │  Types)     │  │           │ │
│  │ • /convers- │  │ • Chat      │  │             │  │ • MongoDB │ │
│  │   ations    │  │   Service   │  │ • Session   │  │ • REST    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                         AI Agent Core                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Agent     │  │   Tools     │  │  LLM Model  │              │
│  │  (Pydantic  │  │ • MongoDB   │  │ (OpenAI     │              │
│  │   -AI)      │  │   Search    │  │  Compatible)│              │
│  │             │  │ • REST API  │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   MongoDB       │  │   Device Action │  │   Flask VLab    │
│   (设备数据库)   │  │   API (借还)    │  │   (Frontend)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 核心组件

### 1. API 层 (`agentd/api/`)

#### 路由定义

```
api/
├── app_factory.py          # FastAPI 应用创建
├── router.py               # 路由聚合
├── routes/
│   ├── health.py           # 健康检查 GET /health
│   └── conversations.py     # 对话核心 API
│       ├── POST /conversations                    # 创建会话
│       ├── POST /conversations/{id}/messages/stream # 流式消息 (SSE)
│       └── DELETE /conversations/{id}             # 删除会话
├── dependencies/
│   ├── user.py            # get_current_user_id (从 Header 提取)
│   └── settings.py        # get_app_settings
└── schemas/
    ├── common.py          # HealthResponse, ErrorResponse
    └── conversations.py   # 请求/响应模型
```

#### 关键端点

**创建会话**
```python
POST /conversations
Response: {
    "conversation_id": "uuid",
    "created_at": "2026-01-20T10:00:00",
    "expires_at": "2026-01-20T10:30:00"
}
```

**流式对话** (SSE)
```python
POST /conversations/{id}/messages/stream
Body: {"message": "查找空闲设备，型号tz570p"}

# SSE 事件流:
event: message_start
data: {"conversation_id": "uuid"}

event: token
data: {"conversation_id": "uuid", "token": "找到"}

event: token
data: {"conversation_id": "uuid", "token": " 6 台"}
...

event: message_end
data: {
    "conversation_id": "uuid",
    "message": "找到6台空闲设备...",
    "structured_data": [{
        "type": "idle_dut_device_list",
        "tool_name": "search_idle_dut_devices_by_model",
        "items": [...]
    }]
}
```

### 2. 应用层 (`agentd/application/`)

```
application/
└── services/
    └── chat_service.py      # 核心业务逻辑
        ├── ChatStreamEvent (类型定义)
        │   ├── MessageStartStreamEvent
        │   ├── TokenStreamEvent
        │   ├── ToolCallStreamEvent
        │   ├── ToolResultStreamEvent
        │   ├── MessageEndStreamEvent
        │   └── ErrorStreamEvent
        ├── stream_chat_turn()      # 流式对话处理
        ├── run_chat_turn()         # 非流式对话
        ├── extract_message_end_structured_data()  # 提取结构化数据
        └── persist_chat_turn()     # 持久化对话记录
```

### 3. 领域层 (`agentd/domain/`)

```
domain/
├── entities/
│   ├── conversation_session.py    # 会话实体
│   │   ├── ConversationSession (dataclass)
│   │   ├── create_conversation_session()
│   │   ├── append_conversation_message()
│   │   └── is_conversation_session_expired()
│   └── conversation_message.py  # 消息实体
│       └── ConversationMessage (role, content, created_at)
├── types/
│   ├── chat_types.py             # 对话相关类型
│   │   ├── ChatAgentDeps         # Agent 依赖 (user_id, user_prompt)
│   │   ├── DutDeviceListPayload  # 设备列表载荷
│   │   ├── IdleDutDeviceListPayload
│   │   └── Borrow/Return Device Payload
│   ├── mongo_types.py            # MongoDB 类型
│   │   ├── MongoResourceConfig   # 资源配置
│   │   ├── MongoQuerySpec        # 查询规格
│   │   └── MongoQueryResult      # 查询结果
│   └── rest_types.py             # REST API 类型
│       ├── RestServiceConfig     # 服务配置
│       ├── RestResourceConfig    # 资源配置
│       └── RestRequest/Response Spec
└── errors/                       # 领域异常
    ├── conversation_errors.py    # 会话异常
    ├── mongo_errors.py           # MongoDB 异常
    ├── rest_errors.py            # REST 异常
    └── agent_errors.py           # Agent 配置异常
```

### 4. 基础设施层 (`agentd/infrastructure/`)

```
infrastructure/
├── config/
│   └── settings.py             # Pydantic Settings 配置
├── connectors/
│   ├── mongodb/                # MongoDB 连接器
│   │   ├── connector.py        # MongoConnector 类
│   │   ├── query_builder.py    # 查询构建器
│   │   └── resource_registry.py # 资源注册表
│   └── rest/                   # REST 连接器
│       ├── connector.py        # RestConnector 类
│       └── service_registry.py # 服务注册表
├── repositories/
│   ├── in_memory_conversation_repository.py
│   └── in_memory_message_history_repository.py
└── streaming/
    └── sse.py                  # SSE 格式工具
```

### 5. AI Agent 核心 (`agentd/agents/`)

```
agents/
├── chat_agent.py               # Agent 创建与配置
│   ├── create_chat_agent()     # 创建 Agent (带缓存)
│   └── get_chat_agent()        # 获取 Agent 实例
├── prompts/                    # 系统提示词 (可选)
└── tools/                      # 工具定义
    ├── __init__.py            # 工具注册入口
    ├── mongo_tools.py         # MongoDB 工具
    │   ├── register_mongo_tools()
    │   ├── search_dut_devices()           # 通用搜索
    │   └── search_idle_dut_devices_by_model()  # 空闲设备搜索
    └── rest_tools.py          # REST API 工具
        ├── register_rest_tools()
        ├── query_rest_resource()            # 通用 REST 查询
        ├── borrow_device()                  # 借用设备
        └── return_device()                  # 归还设备
```

## 工具系统详解

### MongoDB 工具

#### 1. search_dut_devices
```python
async def search_dut_devices(
    ctx: RunContext[ChatAgentDeps],
    keyword: str,              # 自然语言关键词
    filters: MongoQueryParams, # 结构化筛选条件
    limit: int                 # 返回数量限制
) -> dict[str, object]

# 返回: DutDeviceListPayload
{
    "type": "dut_device_list",
    "tool_name": "search_dut_devices",
    "query": {"keyword": "tz570", "limit": 10, "filters": {}},
    "count": 5,
    "items": [{
        "id": "37",
        "sn": "2CB8ED6DF470",
        "owner_raw": "lezhang (Neil Zhang)",
        "owner_account": "lezhang",
        "owner_display_name": "Neil Zhang",
        "owner_label": "owner: lezhang (Neil Zhang)"
    }]
}
```

#### 2. search_idle_dut_devices_by_model
```python
async def search_idle_dut_devices_by_model(
    ctx: RunContext[ChatAgentDeps],
    model: str,    # 设备型号
    limit: int     # 返回数量
) -> dict[str, object]

# 特殊逻辑:
# - 验证用户明确询问"空闲/可用"设备
# - MongoDB 聚合: Owner == User 且非空
# - 自动排除当前用户自己的设备

# 返回: IdleDutDeviceListPayload
{
    "type": "idle_dut_device_list",
    "tool_name": "search_idle_dut_devices_by_model",
    "items": [{
        "id": "37",
        "sn": "...",
        "product": "TZ570P",
        "product_type": "G7",
        "owner_raw": "...",
        "user": "lezhang",  # 与 owner 相同表示空闲
        ...
    }]
}
```

### REST API 工具

#### 1. borrow_device
```python
async def borrow_device(
    ctx: RunContext[ChatAgentDeps],
    device_id: str   # 设备ID
) -> dict[str, object]

# 自动从 ctx.deps.user_id 获取请求者身份
# 调用 REST API: POST /devices/{device_id}/borrow

# 返回: BorrowDevicePayload
{
    "type": "borrow_device_result",
    "tool_name": "borrow_device",
    "result": {
        "device_id": "37",
        "message": "Successfully borrowed device 37",
        "requester": "yzhang",
        "status": "success",
        "type": "borrow_result"
    }
}
```

#### 2. return_device
```python
async def return_device(
    ctx: RunContext[ChatAgentDeps],
    device_id: str
) -> dict[str, object]

# 调用 REST API: POST /devices/{device_id}/return

# 返回: ReturnDevicePayload
{
    "type": "return_device_result",
    "tool_name": "return_device",
    "result": {
        "device_id": "37",
        "message": "Successfully returned device 37 to lezhang",
        "owner": "lezhang (Neil Zhang)",
        "status": "success",
        "type": "return_result"
    }
}
```

## 配置说明

### 环境变量 (.env)

```bash
# === LLM 配置 ===
MODEL_NAME=llama3.2:latest           # 模型名称
MODEL_BASE_URL=https://localhost:11434/v1  # Ollama/vLLM 地址
MODEL_API_KEY=sk-no-key-required       # API Key (本地可随意)

# === MongoDB 配置 ===
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=vlab
MONGODB_RESOURCES_JSON={
    "dut_search": {
        "collection": "devices",
        "filter_fields": ["Product", "ProductType", "Classify"],
        "keyword_paths": ["SN", "Product", "Owner"],
        ...
    }
}

# === REST API 配置 ===
REST_API_SERVICES_JSON={
    "device_action_api": {
        "base_url": "https://vlab.sonicwall.com",
        "auth_type": "bearer_token",
        "resources": {
            "borrow_device": {"method": "POST", "path": "/devices/{device_id}/borrow"},
            "return_device": {"method": "POST", "path": "/devices/{device_id}/return"}
        }
    }
}

# === 应用配置 ===
APP_HOST=0.0.0.0
APP_PORT=10443
SESSION_TTL_SECONDS=1800             # 会话过期时间
MAX_CONVERSATION_MESSAGES=50         # 最大历史消息数
TRUSTED_USER_HEADER=X-User-Id        # 用户身份 Header
```

## 运行与部署

### 本地开发

```bash
cd /opt/vlab/flasky/app/agentd

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置模型和数据库连接

# 运行服务
uv run python app.py

# 服务启动: https://localhost:10443
```

### Docker 部署

```bash
# 构建镜像
docker build -t agentd:latest -f docker/Dockerfile .

# 运行容器
docker run -d \
    -p 10443:10443 \
    -v $(pwd)/.env:/app/.env \
    --name agentd \
    agentd:latest
```

## 扩展开发指南

### 添加新工具

#### 1. MongoDB 查询工具

```python
# agentd/agents/tools/custom_mongo_tools.py

from pydantic_ai import Agent, RunContext
from agentd.domain.types.chat_types import ChatAgentDeps

async def search_custom_resource(
    ctx: RunContext[ChatAgentDeps],
    keyword: str,
    limit: int = 10
) -> dict[str, object]:
    """
    搜索自定义资源
    
    Args:
        keyword: 搜索关键词
        limit: 返回数量限制
    """
    user_id = ctx.deps.user_id
    
    # 调用 MongoDB 连接器
    connector = get_mongo_connector()
    result = await connector.query_custom_collection(
        keyword=keyword,
        limit=limit
    )
    
    return {
        "type": "custom_resource_list",
        "tool_name": "search_custom_resource",
        "items": result.documents
    }

# 在 register_mongo_tools() 中注册
agent.tool(search_custom_resource)
```

#### 2. REST API 工具

```python
# agentd/agents/tools/custom_rest_tools.py

async def perform_custom_action(
    ctx: RunContext[ChatAgentDeps],
    resource_id: str,
    action: str
) -> dict[str, object]:
    """
    执行自定义操作
    
    Args:
        resource_id: 资源ID
        action: 操作类型 (start/stop/restart)
    """
    user_id = ctx.deps.user_id
    
    connector = RestConnector()
    response = await connector.request(
        service_name="custom_service",
        resource_name="custom_action",
        path_params={"id": resource_id},
        json_body={"action": action, "user": user_id}
    )
    
    return {
        "type": "custom_action_result",
        "tool_name": "perform_custom_action",
        "result": response.body
    }

# 在 register_rest_tools() 中注册
agent.tool(perform_custom_action)
```

### 修改系统提示词

```python
# agentd/agents/chat_agent.py

agent = Agent(
    model=model,
    deps_type=ChatAgentDeps,
    output_type=str,
    instructions="""
    你是 VLab 实验室的智能助手，帮助用户管理测试设备。
    
    可用工具：
    1. search_dut_devices - 搜索设备
    2. search_idle_dut_devices_by_model - 搜索空闲设备  
    3. borrow_device - 借用设备
    4. return_device - 归还设备
    
    规则：
    - 用户问"设备"、"盒子"、"防火墙"都指 DUT 设备
    - 默认使用 search_dut_devices，除非明确问"空闲"
    - 借用/归还时自动使用当前用户身份
    - [添加你的自定义规则...]
    """
)
```

## 调试与监控

### 日志系统

```python
# 所有关键操作都记录结构化日志
emit_debug_log(
    "event.name",
    key1=value1,
    key2=value2
)

# 日志级别: DEBUG/INFO/ERROR
# 输出格式: JSON Lines
```

### 典型日志流

```
chat_agent.create.start           # Agent 创建开始
chat_agent.create.completed       # Agent 创建完成 (含注册的工具列表)

api.conversation.stream.start     # 流式对话开始
api.conversation.stream.prepared  # 历史消息加载完成

chat_service.stream.start         # Agent 执行开始
dut_tools.search.start            # 工具调用开始
dut_tools.search.success          # 工具执行成功

chat_service.stream.token         # Token 输出 (逐字)
chat_service.stream.completed     # 流式输出完成
api.conversation.message_end      # 消息结束
```

### 健康检查

```bash
# 服务健康状态
curl https://localhost:10443/health

# 响应
{
    "status": "ok",
    "service": "agentd",
    "version": "0.1.0"
}
```

## 前端集成要点

### SSE 连接处理

```javascript
// 建立 SSE 连接
const eventSource = new EventSource(
    `/api/local-ai/conversations/${conversationId}/messages?message=${encodeURIComponent(query)}`
);

// 处理事件
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.event) {
        case 'message_start':
            showTypingIndicator();
            break;
        case 'token':
            appendToken(data.token);  // 流式追加文字
            break;
        case 'message_end':
            hideTypingIndicator();
            if (data.structured_data) {
                renderStructuredData(data.structured_data);
            }
            break;
        case 'error':
            showError(data.message);
            break;
    }
};
```

### 结构化数据渲染

```javascript
function renderStructuredData(data) {
    switch(data.type) {
        case 'idle_dut_device_list':
            renderDeviceTable(data.items);  // 渲染设备表格
            break;
        case 'borrow_device_result':
            showSuccessToast(data.result);    // 显示成功提示
            break;
        case 'return_device_result':
            showSuccessToast(data.result);
            break;
    }
}
```

## API 端点速查

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /conversations | 创建会话 |
| POST | /conversations/{id}/messages/stream | 流式对话 (SSE) |
| DELETE | /conversations/{id} | 删除会话 |

## 相关技能

- **ai_chat_vlab_skill.md** - VLab 前端 AI Chat 集成技能
- **fastapi_patterns.md** - FastAPI 开发模式
- **pydantic_ai_guide.md** - Pydantic-AI 使用指南

---

**维护者**: VLab Team  
**版本**: 0.1.0  
**更新日期**: 2026-01
