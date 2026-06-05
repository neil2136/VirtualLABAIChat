import requests
import json
import re
import time
from .mongodb import mongo
from flask import current_app


class AISearchService:
    def __init__(self):
        self.api_key = "8ead5d49a47f49ac9dceaf07fd442380.J7M72z2zi9kAqKkn"
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.db = mongo()
    
    def call_ai_api(self, user_input):
        """ calling AI API to analyze user intent """
        print(f"[AI_SEARCH] Processing user input: '{user_input}'")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
                    You are a device management assistant. Analyze the user's input and determine their intent.

                    User input: "{user_input}"

                    Please respond with JSON format:
                    {{
                        "intent": "search_device|check_borrow|find_idle|borrow_device|return_device|get_device_info|other",
                        "device_id": "device number if mentioned, otherwise null",
                        "product_name": "product model if mentioned (e.g., TZ570P), otherwise null",
                        "username": "username if mentioned for borrowing, otherwise null",
                        "confidence": "confidence level 0-1"
                    }}

                    Rules:
                    - "search_device": User wants to find if a device exists (查找设备)
                    - "check_borrow": User wants to check device borrowing status (检查设备借用状态)
                    - "find_idle": User wants to find idle/available devices by product model (查找空闲设备)
                    - "borrow_device": User wants to borrow a device (借用设备)
                    - "return_device": User wants to return a device (归还设备)
                    - "get_device_info": User wants to get detailed information about a device (获取设备信息)
                    - "other": Other requests (其他请求)

                    Device ID format: Numbers like 123, 456
                    Product name format: Model names like TZ570P, TZ670, etc.
                    Borrowing status: When User string is NOT contained in Owner field (case-insensitive), the device is borrowed
                    Idle device: User string IS contained in Owner field (case-insensitive) AND Operator == 'NA'
                    Example: User="khuang", Owner="khuang (Jason Huang)" -> Device is idle (not borrowed)

                    Keywords for find_idle: "idle", "available", "free", "空闲", "可用", "未占用"
                    Keywords for borrow_device: "borrow", "借用", "借"
                """
        
        data = {
            "model": "glm-4-flash",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }
        
        try:
            print(f"[AI_SEARCH] Calling AI API with prompt length: {len(prompt)}")
            response = requests.post(self.api_url, headers=headers, json=data, timeout=10)
            print(f"[AI_SEARCH] AI API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                print(f"[AI_SEARCH] Raw AI response: {ai_response}")
                
                # Clean markdown code block markers if present
                if ai_response.startswith('```json'):
                    ai_response = ai_response.replace('```json', '').replace('```', '').strip()
                elif ai_response.startswith('```'):
                    ai_response = ai_response.replace('```', '').strip()
                
                print(f"[AI_SEARCH] Cleaned AI response: {ai_response}")
                # Parse JSON response
                ai_data = json.loads(ai_response)
                print(f"[AI_SEARCH] Parsed AI data: {ai_data}")
                return ai_data
            else:
                print(f"[AI_SEARCH] AI API call failed: {response.status_code}")
                return self._fallback_analysis(user_input)
        except Exception as e:
            print(f"[AI_SEARCH] AI API error: {str(e)}")
            return self._fallback_analysis(user_input)
    
    def _fallback_analysis(self, user_input):
        """ Simple fallback analysis when AI API fails """
        print(f"[AI_SEARCH] Using fallback analysis for: '{user_input}'")
        
        # Extract device ID using regex
        device_id_match = re.search(r'\b\d+\b', user_input)
        device_id = device_id_match.group() if device_id_match else None
        
        # Extract product name (e.g., TZ570P, TZ670)
        product_match = re.search(r'[A-Z]+\d+[A-Z]*', user_input, re.IGNORECASE)
        product_name = product_match.group() if product_match else None
        
        # Simple keyword matching
        input_lower = user_input.lower()
        if any(keyword in input_lower for keyword in ['idle', 'available', 'free', '空闲', '可用', '未占用']):
            intent = "find_idle"
        elif any(keyword in input_lower for keyword in ['borrow', '借用', '借']):
            intent = "borrow_device"
        elif any(keyword in input_lower for keyword in ['return', '归还', '还']):
            intent = "return_device"
        elif any(keyword in input_lower for keyword in ['get', '获取', '信息', 'info', 'information']):
            intent = "get_device_info"
        elif any(keyword in input_lower for keyword in ['find', 'search', 'look for', 'exist', '查找']):
            intent = "search_device"
        elif any(keyword in input_lower for keyword in ['borrowed', 'who', 'status', 'using', '状态']):
            intent = "check_borrow"
        else:
            intent = "other"
        
        result = {
            "intent": intent,
            "device_id": device_id,
            "product_name": product_name,
            "username": None,
            "confidence": 0.6
        }
        print(f"[AI_SEARCH] Fallback analysis result: {result}")
        return result
    
    def search_device(self, device_id):
        """ Search device by ID """
        print(f"[AI_SEARCH] Searching for device ID: {device_id}")
        try:
            # Keep device_id as string since MongoDB stores it as string
            # Search in DUT collection
            dut_info = self.db.find_one('DUT', 'id', device_id)
            if dut_info and dut_info is not None:
                print(f"[AI_SEARCH] Found DUT device: {device_id}")
                return {
                    "found": True,
                    "type": "DUT",
                    "info": dut_info
                }
            
            # Search in SonicPoint collection
            sp_info = self.db.find_one('SonicPoint', 'id', device_id)
            if sp_info and sp_info is not None:
                print(f"[AI_SEARCH] Found SonicPoint device: {device_id}")
                return {
                    "found": True,
                    "type": "SonicPoint",
                    "info": sp_info
                }
            
            print(f"[AI_SEARCH] Device {device_id} not found in any collection")
            return {"found": False, "message": f"Device {device_id} not found"}
        except Exception as e:
            print(f"[AI_SEARCH] Search error for device {device_id}: {str(e)}")
            return {"found": False, "message": f"Search error: {str(e)}"}
    
    def check_borrow_status(self, device_info):
        """ Check device borrowing status """
        if not device_info or not device_info.get("found"):
            return "Device not found"
        
        info = device_info["info"]
        device_id = info.get("id", "Unknown")
        device_type = device_info["type"]
        product = info.get("Product", "Unknown")
        
        user = info.get("User", "Unknown")
        owner = info.get("Owner", "Unknown")
        
        print(f"[AI_SEARCH] Device {device_id} - User: {user}, Owner: {owner}")
        
        if user != owner:
            status = f"Device {device_id} ({device_type} - {product}) is currently borrowed by {user}, original owner is {owner}"
            return status
        else:
            status = f"Device {device_id} ({device_type} - {product}) is not borrowed, current owner is {owner}"
            return status
    
    def find_idle_devices(self, product_name):
        """ 查找空闲设备（按产品型号） """
        print(f"[AI_SEARCH] 查找空闲设备，产品型号: {product_name}")
        try:
            # 查找所有匹配产品型号的设备
            all_devices = self.db.find_by_regex('DUT', 'Product', product_name)
            
            if not all_devices:
                all_devices = self.db.find_by_regex('SonicPoint', 'Product', product_name)
            
            if not all_devices:
                return {"found": False, "message": f"未找到产品型号为 {product_name} 的设备"}
            
            # 筛选空闲设备：User 字符包含在 Owner 中（不区分大小写）且 Operator == 'NA'
            idle_devices = []
            for device in all_devices:
                user = device.get('User', '')
                owner = device.get('Owner', '')
                operator = device.get('Operator', '')
                
                # 判断设备是否空闲：用户字符包含在所有者中（不区分大小写）且操作者为NA
                # 例如：User="khuang", Owner="khuang (Jason Huang)" -> 空闲
                if user.lower() in owner.lower() and operator == 'NA':
                    idle_devices.append({
                        'id': device.get('id'),
                        'product': device.get('Product'),
                        'user': user,
                        'owner': owner,
                        'type': 'DUT' if 'DUT' in str(type(device)) else 'SonicPoint'
                    })
            
            if idle_devices:
                print(f"[AI_SEARCH] 找到 {len(idle_devices)} 个空闲设备")
                return {
                    "found": True,
                    "count": len(idle_devices),
                    "devices": idle_devices,
                    "message": f"找到 {len(idle_devices)} 个空闲的 {product_name} 设备"
                }
            else:
                return {
                    "found": False,
                    "message": f"未找到空闲的 {product_name} 设备（所有设备都被占用或已借用）"
                }
                
        except Exception as e:
            print(f"[AI_SEARCH] 查找空闲设备错误: {str(e)}")
            return {"found": False, "message": f"查找错误: {str(e)}"}
    
    def borrow_device(self, device_id, username):
        """ 借用设备（参考 dutborrow 方法） """
        print(f"[AI_SEARCH] 尝试借用设备 {device_id}，用户: {username}")
        try:
            # 先查找设备信息
            dut_info = self.db.find_one('DUT', 'id', device_id)
            device_type = 'DUT'
            
            if not dut_info:
                sp_info = self.db.find_one('SonicPoint', 'id', device_id)
                if sp_info:
                    dut_info = sp_info
                    device_type = 'SonicPoint'
                else:
                    return {"success": False, "message": f"设备 {device_id} 不存在"}
            
            # 检查设备是否已被借用
            user = dut_info.get('User', '')
            owner = dut_info.get('Owner', '')
            
            # 判断设备是否已被借用：用户字符不包含在所有者中（不区分大小写）
            # 例如：User="khuang", Owner="khuang (Jason Huang)" -> 未被借用
            # 例如：User="testuser", Owner="khuang (Jason Huang)" -> 已被借用
            if user.lower() not in owner.lower():
                return {"success": False, "message": f"设备 {device_id} 已被 {user} 借用"}
            
            # 更新设备的 User 字段
            update_result = self.db.update_one(device_type, 'id', device_id, 'User', username)
            
            if update_result:
                print(f"[AI_SEARCH] 设备 {device_id} 借用成功")
                return {
                    "success": True,
                    "message": f"成功借用设备 {device_id} ({dut_info.get('Product')})",
                    "device_id": device_id,
                    "product": dut_info.get('Product'),
                    "device_type": device_type
                }
            else:
                return {"success": False, "message": "更新设备信息失败"}
                
        except Exception as e:
            print(f"[AI_SEARCH] 借用设备错误: {str(e)}")
            return {"success": False, "message": f"借用错误: {str(e)}"}
    
    def get_suggested_prompts(self):
        """ Get suggested prompts for users """
        return [
            "Find idle device TZ570P_Lock",
            "Borrow device 123",
            "Find device 101",
            "Check device 100 status",
            "Who is using device 108?",
            "Is device 318 idle?",
            "Search for device 200",
        ]
    
    def process_user_query(self, user_input, username=None):
        """ Process user query and return response """
        print(f"[AI_SEARCH] ===== Processing User Query =====")
        print(f"[AI_SEARCH] Input: '{user_input}'")
        print(f"[AI_SEARCH] Username: {username}")
        
        # Analyze user intent
        ai_result = self.call_ai_api(user_input)
        
        intent = ai_result.get("intent", "other")
        device_id = ai_result.get("device_id")
        product_name = ai_result.get("product_name")
        borrow_username = ai_result.get("username") or username
        confidence = ai_result.get("confidence", 0)
        
        # Fallback: extract device ID using regex if AI didn't find it
        if not device_id:
            device_id_match = re.search(r'\b\d+\b', user_input)
            if device_id_match:
                device_id = device_id_match.group()
                print(f"[AI_SEARCH] Fallback regex extracted device_id: {device_id}")
        
        print(f"[AI_SEARCH] AI Analysis - Intent: {intent}, Device ID: {device_id}, Product: {product_name}, Username: {borrow_username}, Confidence: {confidence}")
        
        if intent == "other" or confidence < 0.5:
            print(f"[AI_SEARCH] Providing suggestions")
            suggested_prompts = self.get_suggested_prompts()
            return {
                "type": "suggestion",
                "message": "I can help you search for devices, check their borrowing status, find idle devices, and borrow devices. Try these prompts:",
                "suggestions": suggested_prompts
            }
        
        if intent == "search_device":
            print(f"[AI_SEARCH] Executing device search for: {device_id}")
            device_result = self.search_device(device_id)
            if device_result["found"]:
                print(f"[AI_SEARCH] Device found, checking borrow status...")
                borrow_status = self.check_borrow_status(device_result)
                return {
                    "type": "device_info",
                    "message": borrow_status,
                    "device": device_result
                }
            else:
                return {
                    "type": "not_found",
                    "message": device_result.get("message", "Device not found")
                }
        
        elif intent == "check_borrow":
            print(f"[AI_SEARCH] Executing borrow status check for: {device_id}")
            device_result = self.search_device(device_id)
            if device_result["found"]:
                print(f"[AI_SEARCH] Device found, checking borrow status...")
                borrow_status = self.check_borrow_status(device_result)
                return {
                    "type": "borrow_status",
                    "message": borrow_status,
                    "device": device_result
                }
            else:
                return {
                    "type": "not_found",
                    "message": device_result.get("message", "Device not found")
                }
        
        elif intent == "find_idle":
            print(f"[AI_SEARCH] Executing find idle devices for: {product_name}")
            if not product_name:
                return {
                    "type": "error",
                    "message": "请指定产品型号（例如：TZ570P）"
                }
            idle_result = self.find_idle_devices(product_name)
            if idle_result["found"]:
                device_list = "\n".join([f"- 设备 {d['id']}: {d['product']} (所有者: {d['owner']})" for d in idle_result["devices"]])
                return {
                    "type": "idle_devices",
                    "message": idle_result["message"],
                    "devices": idle_result["devices"],
                    "formatted_list": device_list
                }
            else:
                return {
                    "type": "not_found",
                    "message": idle_result.get("message", "未找到空闲设备")
                }
        
        elif intent == "borrow_device":
            print(f"[AI_SEARCH] Executing borrow device: {device_id}, user: {borrow_username}")
            if not device_id:
                return {
                    "type": "error",
                    "message": "请指定设备ID（例如：123）"
                }
            if not borrow_username:
                return {
                    "type": "error",
                    "message": "请提供用户名以借用设备"
                }
            borrow_result = self.borrow_device(device_id, borrow_username)
            if borrow_result["success"]:
                return {
                    "type": "borrow_success",
                    "message": borrow_result["message"],
                    "device_id": borrow_result["device_id"],
                    "product": borrow_result["product"]
                }
            else:
                return {
                    "type": "borrow_failed",
                    "message": borrow_result["message"]
                }
        
        elif intent == "return_device":
            print(f"[AI_SEARCH] Executing return device: {device_id}, user: {borrow_username}")
            if not device_id:
                return {
                    "type": "error",
                    "message": "请指定设备ID（例如：123）"
                }
            if not borrow_username:
                return {
                    "type": "error",
                    "message": "请提供用户名以归还设备"
                }
            # Return device by calling API endpoint
            # For now, just return the information to let frontend handle it
            return {
                "type": "return_device",
                "message": f"准备归还设备 {device_id}",
                "device_id": device_id,
                "username": borrow_username
            }
        
        elif intent == "get_device_info":
            print(f"[AI_SEARCH] Executing get device info: {device_id}")
            if not device_id:
                return {
                    "type": "error",
                    "message": "请指定设备ID（例如：123）"
                }
            
            device_result = self.search_device(device_id)
            if device_result["found"]:
                # Format device information
                info = device_result["info"]
                device_info = {
                    "name": info.get("Product", "Unknown"),
                    "id": info.get("id", "Unknown"),
                    "sn": info.get("SN", "Unknown"),
                    "owner": info.get("Owner", "Unknown"),
                    "user": info.get("User", "Unknown"),
                    "type": device_result["type"]
                }
                
                return {
                    "type": "device_info",
                    "message": f"设备 {device_id} 的详细信息：",
                    "device_info": device_info
                }
            else:
                return {
                    "type": "not_found",
                    "message": device_result.get("message", "设备未找到")
                }
        
        return {
            "type": "error",
            "message": "Unable to process your request"
        }
