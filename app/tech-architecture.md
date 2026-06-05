# VLab Device Management System 技术架构文档

## 项目概述
VLab设备管理系统是一个基于Python的Web应用，采用Flask框架构建，支持设备管理、用户认证、API接口等功能。

## 技术栈

### 前端技术
- 项目主要采用Flask框架构建后端API
- 使用HTML、CSS、JavaScript构建用户界面
- 支持RESTful API接口

### 后端技术
- **主框架**: Flask 2.3.3
- **数据库**: MongoDB (通过Flask-SQLAlchemy和pymongo)
- **用户认证**: Flask-Login
- **表单处理**: Flask-WTF
- **邮件服务**: Flask-Mail
- **跨域支持**: Flask-CORS
- **API框架**: Flask-RESTful

### 数据库配置
- **数据库类型**: MongoDB
- **连接配置**:
  ```python
  MONGODB_CONFIG = {
      'host': '10.103.2.40',
      'port': 27017,
      'db_name': 'VL',
      'username': 'root',
      'password': 'sonicpassword'
  }
  ```

## API接口说明

### 用户认证
- `/api/tokens/` - 获取认证令牌
- `/api/users/` - 用户管理接口
- 认证使用HTTP Basic Auth和Token验证

### 设备管理
- `/api/posts/` - 帖子/设备管理
- 支持分页查询、创建、更新操作

## 项目结构

```
app/
├── __init__.py          # 应用初始化
├── api/                 # API接口
│   ├── authentication.py  # 用户认证
│   ├── posts.py          # 帖子/设备管理
│   └── errors.py         # 错误处理
├── auth/                # 用户认证相关
├── lib/                 # 库文件
│   ├── ai_search.py      # AI搜索服务
│   ├── esxi/             # VMware ESXi管理
│   └── mail/             # 邮件相关功能
├── models.py            # 数据模型定义
├── main/                # 主视图
└── README.md            # 项目说明
```

## 数据库模型

### User模型
```python
class User(db.Document):
    email = db.StringField(required=True, unique=True)
    password = db.StringField(required=True)
    confirmed = db.BooleanField(default=False)
    # 其他用户相关字段
```

### Post模型
```python
class Post(db.Document):
    author = db.ReferenceField(User, required=True)
    body = db.StringField(required=True)
    # 其他帖子相关字段
```

## 配置管理

- 通过config.py文件管理不同环境配置
- 支持开发、测试、生产环境配置
- DeepSeek AI模型集成配置

## 部署说明

- 使用Gunicorn作为应用服务器
- Procfile定义部署配置
- 通过Flask-Migrate管理数据库迁移

## 依赖包管理

项目依赖通过requirements.txt管理，主要依赖包括：
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-WTF
- Flask-Mail
- pymongo
- 以及其他库