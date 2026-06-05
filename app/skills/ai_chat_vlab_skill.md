# Skill: Add AI Chat for VLab

## 功能描述
给 vlab 前端页面添加 AI Chat 按钮，以对话方式完成设备查询、借用、归还操作。

## 文件位置
- 后端 API: `/opt/vlab/flasky/app/api/views.py`
- 前端 UI: `/opt/vlab/flasky/app/templates/bootstrap/topnav.html`
- AI 服务: `/opt/vlab/flasky/app/lib/ai_search.py`

---

## 后端代码

### 1. 添加到 `app/api/views.py`

```python
# Local AI Agent Configuration
LOCAL_AI_BASE_URL = "https://10.8.66.253:10443"
LOCAL_AI_TIMEOUT = 30


def get_current_username():
    """获取当前登录用户名"""
    if current_user.is_authenticated:
        return current_user.svname
    return "anonymous"


def get_local_ai_headers():
    """构造Local AI Agent请求头"""
    return {
        "X-User-Id": get_current_username(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


# ========== Local AI Agent Proxy APIs ==========

@api.route('/local-ai/conversations', methods=['POST'])
def create_local_ai_conversation():
    """创建Local AI Agent会话"""
    try:
        url = f"{LOCAL_AI_BASE_URL}/conversations"
        headers = get_local_ai_headers()
        payload = {"message": "开始新会话"}
        
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=LOCAL_AI_TIMEOUT,
            verify=False
        )
        
        if response.status_code == 201:
            return jsonify(response.json()), 201
        else:
            return jsonify({'error': 'Failed to create conversation'}), response.status_code
            
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Local AI Agent unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/local-ai/conversations/<conversation_id>/messages', methods=['POST'])
def send_local_ai_message(conversation_id):
    """发送消息并流式返回响应 (SSE)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        url = f"{LOCAL_AI_BASE_URL}/conversations/{conversation_id}/messages/stream"
        headers = {
            "X-User-Id": get_current_username(),
            "Accept": "text/event-stream",
            "Content-Type": "application/json"
        }
        payload = {"message": user_message}
        
        def generate():
            try:
                with requests.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    stream=True,
                    timeout=300,
                    verify=False
                ) as resp:
                    # 直接转发原始字节，保持SSE格式完整
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            yield chunk
                            
            except Exception as e:
                yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'.encode('utf-8')
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/local-ai/conversations/<conversation_id>', methods=['DELETE'])
def delete_local_ai_conversation(conversation_id):
    """删除会话"""
    try:
        url = f"{LOCAL_AI_BASE_URL}/conversations/{conversation_id}"
        headers = {"X-User-Id": get_current_username()}
        
        response = requests.delete(
            url,
            headers=headers,
            timeout=LOCAL_AI_TIMEOUT,
            verify=False
        )
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({'error': 'Failed to delete conversation'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 前端代码

### 2. 添加到 `app/templates/bootstrap/topnav.html`

**导航按钮** (在现有 AI Chat 按钮后添加):

```html
<li role="presentation" class="dropdown">
  <a href="javascript:;" class="dropdown-toggle info-number" 
     data-toggle="modal" data-target="#LocalAISearchModal" 
     aria-expanded="false" title="Local AI Chat">
    <i class="fa fa-comments-o"></i> Local AI Chat
  </a>
</li>
```

**Modal 对话框** (添加在文件末尾 `</script>` 前):

```html
<!-- Local AI Search Modal - WeChat Style -->
<div class="modal fade" id="LocalAISearchModal" tabindex="-1" role="dialog" 
     aria-labelledby="LocalAISearchModalLabel">
  <div class="modal-dialog modal-lg" role="document" style="max-width: 800px;">
    <div class="modal-content" style="border-radius: 10px; overflow: hidden;">
      
      <!-- Header -->
      <div class="modal-header" style="background-color: #337ab7; padding: 15px 20px;">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
        <h4 class="modal-title" style="margin: 0; font-size: 18px; font-weight: 500; color: #fff;">
          <i class="fa fa-server" style="color: #fff; margin-right: 8px;"></i> 
          Local AI Assistant
        </h4>
      </div>
      
      <!-- Body -->
      <div class="modal-body" style="padding: 0; background-color: #f5f5f5; height: 500px; 
                                      display: flex; flex-direction: column;">
        
        <!-- Messages Area -->
        <div id="localAiSearchMessages" style="flex: 1; overflow-y: auto; padding: 20px;">
          <div class="chat-message ai-message">
            <div class="chat-avatar" style="background-color: #337ab7;">
              <i class="fa fa-server"></i>
            </div>
            <div class="chat-bubble">
              <div class="chat-content">
                你好！我是本地AI助手，支持以下功能：<br>
                1. <strong>查找空闲设备</strong> - 输入如"查找空闲设备，型号TZ570"<br>
                2. <strong>借用设备</strong> - 在设备列表中点击"借用"按钮或直接输入设备ID<br>
                3. <strong>归还设备</strong> - 在设备列表中点击"归还"按钮或直接输入设备ID
              </div>
              <div class="chat-time">刚刚</div>
            </div>
          </div>
        </div>
        
        <!-- Quick Actions Area -->
        <div style="padding: 10px 20px; background-color: #fff; border-top: 1px solid #e5e5e5;">
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;">
            <button class="btn btn-sm btn-info" onclick="setLocalInput('查找空闲设备，型号TZ470')">
              <i class="fa fa-search"></i> 查找TZ470
            </button>
            <button class="btn btn-sm btn-info" onclick="setLocalInput('查找空闲设备，型号TZ570')">
              <i class="fa fa-search"></i> 查找TZ570
            </button>
            <button class="btn btn-sm btn-info" onclick="setLocalInput('查找空闲设备，型号TZ670')">
              <i class="fa fa-search"></i> 查找TZ670
            </button>
          </div>
          <div style="display: flex; gap: 8px; margin-bottom: 10px;">
            <div style="flex: 1; display: flex; gap: 8px;">
              <input type="text" id="quickDeviceId" placeholder="输入设备ID" 
                     style="flex: 1; border-radius: 15px; border: 1px solid #ddd; 
                            padding: 6px 12px; font-size: 13px;">
              <button class="btn btn-sm btn-success" onclick="quickBorrowDevice()">
                <i class="fa fa-hand-grab-o"></i> 借用
              </button>
              <button class="btn btn-sm btn-warning" onclick="quickReturnDevice()">
                <i class="fa fa-undo"></i> 归还
              </button>
            </div>
          </div>
        </div>
        
        <!-- Input Area -->
        <div style="padding: 15px 20px; background-color: #fff; border-top: 1px solid #e5e5e5;">
          <div class="input-group" style="display: flex; gap: 10px;">
            <input type="text" class="form-control" id="localAiSearchInput" 
                   placeholder="输入问题，如：查找空闲设备..." 
                   style="border-radius: 20px; border: 1px solid #e5e5e5; padding: 10px 20px;">
            <button class="btn btn-primary" type="button" onclick="performLocalAISearch()" 
                    style="border-radius: 20px; padding: 10px 25px; background-color: #337ab7;">
              <i class="fa fa-paper-plane"></i> 发送
            </button>
          </div>
        </div>
      </div>
      
    </div>
  </div>
</div>

<script>
// ========== Local AI Chat JavaScript ==========
let localConversationId = null;

// Local AI Agent 配置 - 使用 Flask 后端代理
const LOCAL_AI_BASE_URL = '/api/local-ai';
const localAIUsername = '{{ current_user.svname }}';

// 辅助函数：添加消息到聊天区
function addLocalMessage(message, isUser = false) {
  const container = document.getElementById('localAiSearchMessages');
  const div = document.createElement('div');
  div.className = 'chat-message ' + (isUser ? 'user' : '');
  
  div.innerHTML = `
    <div class="chat-avatar" style="background-color: ${isUser ? '#07c160' : '#337ab7'};">
      <i class="fa fa-${isUser ? 'user' : 'server'}"></i>
    </div>
    <div class="chat-bubble">
      <div class="chat-content">${message}</div>
      <div class="chat-time">${new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'})}</div>
    </div>
  `;
  
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// 创建会话
async function createLocalConversation() {
  try {
    const response = await fetch(LOCAL_AI_BASE_URL + '/conversations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrf_token'),
        'X-User-Id': localAIUsername
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      localConversationId = data.conversation_id;
      console.log('[LOCAL_AI] Conversation created:', localConversationId);
    }
  } catch (error) {
    console.error('[LOCAL_AI] Create conversation error:', error);
  }
}

// 发送消息 (SSE 流式响应)
async function performLocalAISearch() {
  const input = document.getElementById('localAiSearchInput');
  const query = input.value.trim();
  if (!query) return;
  
  addLocalMessage(query, true);
  input.value = '';
  setLocalLoading(true);
  
  try {
    if (!localConversationId) {
      await createLocalConversation();
    }
    
    const response = await fetch(
      `${LOCAL_AI_BASE_URL}/conversations/${localConversationId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrf_token'),
        'X-User-Id': localAIUsername
      },
      body: JSON.stringify({ message: query })
    });
    
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    
    // 解析 SSE 流
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullResponse = null;
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:')) {
          try {
            const jsonData = trimmed.substring(5).trim();
            if (jsonData && jsonData !== '[DONE]') {
              fullResponse = JSON.parse(jsonData);
            }
          } catch (e) {}
        }
      }
    }
    
    if (fullResponse) {
      displayLocalAIResponse(fullResponse);
    } else {
      addLocalMessage('抱歉，未能获取到有效响应。');
    }
    
  } catch (error) {
    console.error('[LOCAL_AI] Error:', error);
    addLocalMessage('❌ 请求失败: ' + error.message);
  } finally {
    setLocalLoading(false);
  }
}

// 显示 AI 响应 (带结构化数据处理)
function displayLocalAIResponse(response) {
  let html = response.message ? response.message.replace(/\n/g, '<br>') : '暂无回复';
  
  if (response.structured_data && response.structured_data.length > 0) {
    const data = response.structured_data[0];
    
    if (data.type === 'idle_dut_device_list' && data.items) {
      // 显示空闲设备列表，带借用/归还按钮
      html += `<br><br><strong>找到 ${data.count} 台设备：</strong>`;
      html += '<table class="table table-bordered table-striped" style="margin-top: 10px;">';
      html += '<tr><th>ID</th><th>型号</th><th>序列号</th><th>类型</th><th>所有者</th><th>操作</th></tr>';
      
      data.items.forEach(item => {
        html += `<tr>
          <td>${item.id}</td>
          <td>${item.product}</td>
          <td>${item.sn}</td>
          <td>${item.product_type}</td>
          <td>${item.owner_label || item.owner_display_name}</td>
          <td>
            <button class="btn btn-xs btn-success" onclick="borrowDeviceLocal('${item.id}')">借用</button>
            <button class="btn btn-xs btn-warning" onclick="returnDeviceLocal('${item.id}')">归还</button>
          </td>
        </tr>`;
      });
      html += '</table>';
    }
  }
  
  addLocalMessage(html);
}

// 直接借用设备 (调用 Flask API，不经过 AI Agent)
async function borrowDeviceLocal(deviceId) {
  addLocalMessage(`借用设备${deviceId}`, true);
  setLocalLoading(true);
  
  try {
    const response = await fetch(`/api/borrow-device/${deviceId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrf_token'),
        'X-User-Id': localAIUsername
      },
      body: JSON.stringify({ requester_name: localAIUsername })
    });
    
    const result = await response.json();
    
    let html = '';
    if (response.ok && result.status === 'success') {
      html = `<div class="alert alert-success">
        <i class="fa fa-check-circle"></i> <strong>借用成功</strong><br>
        设备ID: ${result.device_id}<br>消息: ${result.message}
      </div>`;
    } else {
      html = `<div class="alert alert-danger">
        <i class="fa fa-times-circle"></i> <strong>借用失败</strong><br>
        消息: ${result.error || result.message}
      </div>`;
    }
    addLocalMessage(html);
    
  } catch (error) {
    addLocalMessage('❌ 借用设备失败: ' + error.message);
  } finally {
    setLocalLoading(false);
  }
}

// 直接归还设备 (调用 Flask API)
async function returnDeviceLocal(deviceId) {
  addLocalMessage(`归还设备${deviceId}`, true);
  setLocalLoading(true);
  
  try {
    const response = await fetch(`/api/return-device/${deviceId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrf_token'),
        'X-User-Id': localAIUsername
      },
      body: JSON.stringify({ requester_name: localAIUsername })
    });
    
    const result = await response.json();
    
    let html = '';
    if (response.ok && result.status === 'success') {
      html = `<div class="alert alert-success">
        <i class="fa fa-check-circle"></i> <strong>归还成功</strong><br>
        设备ID: ${result.device_id}<br>消息: ${result.message}
      </div>`;
    } else {
      html = `<div class="alert alert-danger">
        <i class="fa fa-times-circle"></i> <strong>归还失败</strong><br>
        消息: ${result.error || result.message}
      </div>`;
    }
    addLocalMessage(html);
    
  } catch (error) {
    addLocalMessage('❌ 归还设备失败: ' + error.message);
  } finally {
    setLocalLoading(false);
  }
}

// 快速操作辅助函数
function setLocalInput(text) {
  document.getElementById('localAiSearchInput').value = text;
  performLocalAISearch();
}

function quickBorrowDevice() {
  const id = document.getElementById('quickDeviceId').value.trim();
  if (!id) { addLocalMessage('❌ 请输入设备ID', false); return; }
  borrowDeviceLocal(id);
  document.getElementById('quickDeviceId').value = '';
}

function quickReturnDevice() {
  const id = document.getElementById('quickDeviceId').value.trim();
  if (!id) { addLocalMessage('❌ 请输入设备ID', false); return; }
  returnDeviceLocal(id);
  document.getElementById('quickDeviceId').value = '';
}

// 设置加载状态
function setLocalLoading(loading) {
  const btn = document.querySelector('#LocalAISearchModal .btn-primary');
  const input = document.getElementById('localAiSearchInput');
  
  if (loading) {
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> 发送中...';
    btn.disabled = true;
    input.disabled = true;
  } else {
    btn.innerHTML = '<i class="fa fa-paper-plane"></i> 发送';
    btn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

// 获取 Cookie
function getCookie(name) {
  let value = null;
  if (document.cookie) {
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
      c = c.trim();
      if (c.substring(0, name.length + 1) === (name + '=')) {
        value = decodeURIComponent(c.substring(name.length + 1));
        break;
      }
    }
  }
  return value;
}

// Modal 事件
$('#LocalAISearchModal').on('shown.bs.modal', function() {
  $('#localAiSearchInput').focus();
});

$('#LocalAISearchModal').on('hidden.bs.modal', function() {
  localConversationId = null;
});

// 回车键支持
document.getElementById('localAiSearchInput').addEventListener('keypress', function(e) {
  if (e.key === 'Enter') performLocalAISearch();
});
document.getElementById('quickDeviceId').addEventListener('keypress', function(e) {
  if (e.key === 'Enter') quickBorrowDevice();
});
</script>
```

---

## 使用说明

### 查询设备
1. 点击 "Local AI Chat" 按钮打开对话框
2. 输入 "查找空闲设备，型号TZ570" 或点击快捷按钮
3. AI 返回设备列表，点击 "借用" 或 "归还" 按钮

### 直接借还
1. 在 "输入设备ID" 框中输入设备编号
2. 点击 "借用" 或 "归还" 按钮
3. 或直接按回车借用

### 对话方式
- 支持自然语言查询，如：
  - "帮我找一个空闲的 TZ570"
  - "借用设备 123"
  - "归还设备 456"

---

## 架构说明

```
┌─────────┐     ┌─────────────┐     ┌─────────────────┐
│ Browser │────▶│ Flask Proxy │────▶│ Local AI Agent  │
│ (前端)   │     │ /api/local-ai│     │ 10.8.66.253:10443│
└─────────┘     └─────────────┘     └─────────────────┘
     │                  │
     │                  │
     └──────────────────┘
     直接借用/归还: /api/borrow-device/{id}
                   /api/return-device/{id}
```

- **查找设备**: 通过 AI Agent 处理自然语言，返回结构化数据
- **借用/归还**: 前端直接调用 Flask API，更快速可靠

---

## 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| LOCAL_AI_BASE_URL | `https://10.8.66.253:10443` | AI Agent 地址 |
| LOCAL_AI_TIMEOUT | 30 | 超时时间(秒) |
| verify | False | 跳过 SSL 验证 |
| X-User-Id | `current_user.svname` | 当前用户名 |
