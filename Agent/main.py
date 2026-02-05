from Agent_Core import SystemandLogic, CustomAgent, Agent_
from Sql_Tool.Calling_Able import MemoryType, UserManager
from Sql_Tool.MsSQL_Tool import Show_Tables, Query_SQL
from Rag_Tool.Retrieval import Retrieval_Tool_Text
from agents import OpenAIChatCompletionsModel, ModelSettings
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File, Form, HTTPException, Depends, Header
from pydantic import BaseModel
import asyncio
import fastapi
import uvicorn
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import os
from pathlib import Path

app = fastapi.FastAPI(title="Agent API", description="多對話 Agent 系統 API")

# ==================== 文件配置 ====================

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ==================== 用戶管理配置 ====================

user_manager = UserManager()
user_manager.initialize_user_tables()

# 創建默認管理員帳號（如果不存在）
try:
    user_manager.create_user("admin", "admin123", "admin", "admin@example.com")
    user_manager.create_user("user", "user123", "user", "user@example.com")
except:
    pass  # 用戶可能已存在

# ==================== CORS 配置 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5556",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5556",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 請求模型 ====================

class AskRequest(BaseModel):
    """提問請求"""
    user_prompt: str
    conversation_id: Optional[int] = None
    max_turns: Optional[int] = 10

class ConversationSwitchRequest(BaseModel):
    """切換對話請求"""
    conversation_id: int

class ClearMemoryRequest(BaseModel):
    """清除記憶請求"""
    conversation_id: int
    memory_type: Optional[str] = None

class SystemMemoryRequest(BaseModel):
    """系統記憶請求"""
    key: str
    content: str
    metadata: Optional[str] = None

class SelectModelRequest(BaseModel):
    """選擇模型請求"""
    model_name: str

class LoginRequest(BaseModel):
    """登入請求"""
    username: str
    password: str

class CreateUserRequest(BaseModel):
    """創建用戶請求"""
    username: str
    password: str
    role: str = "user"
    email: Optional[str] = None

# ==================== 認證輔助函數 ====================

def get_current_user(authorization: str = Header(None)) -> Optional[Dict[str, Any]]:
    """從請求頭中獲取當前用戶"""
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        user = user_manager.verify_session(token)
        return user
    
    return None

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """要求管理員權限"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登入")
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return current_user

def require_auth(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """要求登入"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登入")
    return current_user

# ==================== 根路由 ====================

@app.get("/")
def read_root():
    return {
        "service": "Agent Multi-Conversation System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health_check():
    """健康檢查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# ==================== 對話操作 API ====================

@app.post("/chat/ask")
async def ask_question(
    request: AskRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    提問 API
    - 如果提供 conversation_id，則切換到該對話
    - 否則使用當前對話編號
    - 支持可選的用戶認證
    """
    try:
        # 設置對話編號
        if request.conversation_id:
            SystemandLogic.set_conversation_id(request.conversation_id)
        
        # 執行 Agent
        response = await SystemandLogic.main(request.user_prompt, Agent_, max_turns=request.max_turns)
        
        # 如果用戶已登入，關聯消息到用戶
        if current_user:
            try:
                import pyodbc
                conn_obj = pyodbc.connect(user_manager.conn_str)
                cursor = conn_obj.cursor()
                
                # 更新當前對話的所有未關聯消息為當前用戶
                cursor.execute("""
                    UPDATE UnifiedMemory
                    SET UserId = ?
                    WHERE ConversationId = ? AND UserId IS NULL
                """, (current_user.get("user_id"), SystemandLogic.current_conversation_id))
                
                conn_obj.commit()
                conn_obj.close()
            except:
                pass  # 如果更新失敗，不影響主流程
        
        return {
            "status": "success",
            "conversation_id": SystemandLogic.current_conversation_id,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/chat/switch")
def switch_conversation(
    request: ConversationSwitchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    切換對話
    - 支持可選的用戶認證
    """
    try:
        SystemandLogic.switch_conversation(request.conversation_id)
        stats = SystemandLogic.get_conversation_summary()
        return {
            "status": "success",
            "conversation_id": request.conversation_id,
            "messages_count": stats['total_messages'],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/chat/new")
def create_new_conversation(start_id: int = 1):
    """
    建立新對話
    - 自動查找下一個未使用的編號
    """
    try:
        all_conversations = SystemandLogic.list_all_conversations()
        
        # 找下一個可用的編號
        if all_conversations:
            new_id = max(all_conversations) + 1
        else:
            new_id = start_id
        
        SystemandLogic.set_conversation_id(new_id)
        
        return {
            "status": "success",
            "conversation_id": new_id,
            "message": f"New conversation created with ID {new_id}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/chat/current")
def get_current_conversation():
    """獲取當前對話信息"""
    try:
        stats = SystemandLogic.get_conversation_summary()
        return {
            "status": "success",
            "conversation_id": SystemandLogic.current_conversation_id,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 記憶查詢 API ====================

@app.get("/memory/conversations")
def list_conversations():
    """列出所有對話"""
    try:
        conversations = SystemandLogic.list_all_conversations()
        return {
            "status": "success",
            "conversations": conversations,
            "total": len(conversations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/memory/messages/{conversation_id}")
def get_conversation_messages(
    conversation_id: int, 
    limit: int = 50, 
    memory_type: str = "chat",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    獲取對話記憶
    - conversation_id: 對話編號
    - limit: 返回數量限制
    - memory_type: 記憶類型 (chat/system/context/knowledge)
    - 支持用戶認證（可選）
    """
    try:
        # 映射記憶類型
        mem_type_map = {
            "chat": MemoryType.CHAT,
            "system": MemoryType.SYSTEM,
            "context": MemoryType.CONTEXT,
            "knowledge": MemoryType.KNOWLEDGE
        }
        mem_type = mem_type_map.get(memory_type.lower(), MemoryType.CHAT)
        
        # 如果用戶已登入，檢查權限
        if current_user:
            try:
                import pyodbc
                conn_obj = pyodbc.connect(user_manager.conn_str)
                cursor = conn_obj.cursor()
                
                # 檢查用戶是否有權訪問此對話
                if current_user.get("role") != "admin":
                    cursor.execute("""
                        SELECT COUNT(*) as cnt
                        FROM UnifiedMemory
                        WHERE ConversationId = ? AND UserId = ?
                    """, (conversation_id, current_user.get("user_id")))
                    
                    if cursor.fetchone().cnt == 0:
                        conn_obj.close()
                        raise HTTPException(status_code=403, detail="無權訪問此對話")
                
                conn_obj.close()
            except HTTPException:
                raise
            except:
                pass  # 如果檢查失敗，繼續
        
        messages = SystemandLogic.manager.get_messages(
            conversation_id, 
            limit=limit, 
            memory_type=mem_type
        )
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "memory_type": memory_type,
            "messages": messages,
            "total": len(messages),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/memory/statistics/{conversation_id}")
def get_conversation_stats(conversation_id: int):
    """獲取對話統計"""
    try:
        stats = SystemandLogic.manager.get_conversation_statistics(conversation_id)
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/memory/search/{conversation_id}")
def search_messages(conversation_id: int, keyword: str, memory_type: str = "chat"):
    """搜索對話消息"""
    try:
        mem_type_map = {
            "chat": MemoryType.CHAT,
            "system": MemoryType.SYSTEM,
            "context": MemoryType.CONTEXT,
            "knowledge": MemoryType.KNOWLEDGE
        }
        mem_type = mem_type_map.get(memory_type.lower(), MemoryType.CHAT)
        
        results = SystemandLogic.manager.search_messages(
            conversation_id, 
            keyword, 
            memory_type=mem_type
        )
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "keyword": keyword,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 清除記憶 API ====================

@app.delete("/memory/clear/{conversation_id}")
def clear_conversation_memory(conversation_id: int, memory_type: Optional[str] = None):
    """
    清除對話記憶
    - conversation_id: 對話編號
    - memory_type: 記憶類型 (可選，如果為空則清除所有)
    """
    try:
        mem_type = None
        if memory_type:
            mem_type_map = {
                "chat": MemoryType.CHAT,
                "system": MemoryType.SYSTEM,
                "context": MemoryType.CONTEXT,
                "knowledge": MemoryType.KNOWLEDGE
            }
            mem_type = mem_type_map.get(memory_type.lower())
        
        SystemandLogic.manager.clear_messages(conversation_id, memory_type=mem_type)
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "memory_type": memory_type or "all",
            "message": f"Cleared {'all' if not memory_type else memory_type} memories",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.delete("/memory/clear-all")
def clear_all_memory():
    """清除所有記憶"""
    try:
        SystemandLogic.manager.clear_messages()
        return {
            "status": "success",
            "message": "All memories cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 系統記憶 API ====================

@app.get("/system-memory/all")
def get_all_system_memories():
    """獲取所有系統記憶"""
    try:
        memories = SystemandLogic.manager.get_all_system_memories()
        return {
            "status": "success",
            "memories": memories,
            "total": len(memories),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/system-memory/{memory_key}")
def get_system_memory(memory_key: str):
    """獲取特定系統記憶"""
    try:
        memory = SystemandLogic.manager.get_system_memory(memory_key)
        if memory:
            return {
                "status": "success",
                "key": memory_key,
                "memory": memory,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "not_found",
                "key": memory_key,
                "message": "System memory not found",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/system-memory/save")
def save_system_memory(request: SystemMemoryRequest):
    """保存系統記憶"""
    try:
        result = SystemandLogic.manager.save_system_memory(
            request.key, 
            request.content, 
            request.metadata
        )
        return {
            "status": "success" if result else "failed",
            "key": request.key,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.put("/system-memory/update/{memory_key}")
def update_system_memory(memory_key: str, content: Optional[str] = None, metadata: Optional[str] = None):
    """更新系統記憶"""
    try:
        result = SystemandLogic.manager.update_system_memory(
            memory_key, 
            content=content, 
            metadata=metadata
        )
        return {
            "status": "success" if result else "failed",
            "key": memory_key,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.delete("/system-memory/{memory_key}")
def delete_system_memory(memory_key: str):
    """刪除系統記憶"""
    try:
        result = SystemandLogic.manager.delete_system_memory(memory_key)
        return {
            "status": "success" if result else "failed",
            "key": memory_key,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 模型選擇 API ====================

@app.get("/models/list")
async def list_available_models():
    """列出所有可用模型"""
    try:
        # 嘗試從客戶端獲取模型列表
        try:
            if hasattr(CustomAgent.external_client, 'models'):
                models = await CustomAgent.external_client.models.list()
                model_list = [m.id async for m in models]
            else:
                model_list = [CustomAgent.model_]  # 至少返回當前模型
        except Exception as e:
            SystemandLogic.Agent_CAlling_Log.warning(f"無法獲取模型列表: {e}，返回當前模型")
            model_list = [CustomAgent.model_]  # 失敗時至少返回當前模型
        
        return {
            "status": "success",
            "models": model_list if model_list else [CustomAgent.model_],
            "total": len(model_list) if model_list else 1,
            "current_model": CustomAgent.model_,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        SystemandLogic.Agent_CAlling_Log.error(f"list_available_models() 錯誤: {e}")
        return {
            "status": "success",
            "models": [CustomAgent.model_],
            "total": 1,
            "current_model": CustomAgent.model_,
            "timestamp": datetime.now().isoformat()
        }

@app.post("/models/select")
def select_model(request: SelectModelRequest):
    """選擇模型"""
    try:
        # 更新 CustomAgent 的模型
        CustomAgent.model_ = request.model_name
        
        # 重新創建 Agent
        from Sql_Tool.MsSQL_Tool import Show_Tables, Query_SQL
        from Rag_Tool.Retrieval import Retrieval_Tool_Text
        
        global Agent_
        Agent_ = CustomAgent.Create_Agent(Tool_List=[Show_Tables, Query_SQL, Retrieval_Tool_Text])
        
        SystemandLogic.Agent_CAlling_Log.info(f"Model switched to: {request.model_name}")
        
        return {
            "status": "success",
            "previous_model": CustomAgent.model_,
            "new_model": request.model_name,
            "message": f"Model switched to {request.model_name}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/models/current")
def get_current_model():
    """獲取當前模型信息"""
    return {
        "status": "success",
        "current_model": CustomAgent.model_,
        "base_url": CustomAgent.base_url,
        "model_settings": CustomAgent.Model_Set,
        "timestamp": datetime.now().isoformat()
    }

# ==================== 配置 API ====================

@app.get("/config/agent-settings")
def get_agent_settings():
    """獲取 Agent 設置"""
    return {
        "status": "success",
        "agent_name": CustomAgent.name,
        "model": CustomAgent.model_,
        "base_url": CustomAgent.base_url,
        "model_settings": CustomAgent.Model_Set,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/config/memory-types")
def get_memory_types():
    """獲取支持的記憶類型"""
    return {
        "status": "success",
        "memory_types": [
            {"name": "chat", "description": "對話記憶"},
            {"name": "system", "description": "系統記憶"},
            {"name": "context", "description": "上下文記憶"},
            {"name": "knowledge", "description": "知識記憶"}
        ],
        "timestamp": datetime.now().isoformat()
    }

# ==================== 文件管理 API ====================

@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...), conversation_id: int = Form(...)):
    """上傳檔案到特定對話"""
    try:
        # 創建對話資料夾
        conv_dir = UPLOAD_DIR / str(conversation_id)
        conv_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成時間戳前綴的檔名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.filename).suffix
        new_filename = f"{timestamp}_{file.filename}"
        file_path = conv_dir / new_filename
        
        # 保存檔案
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        return {
            "status": "success",
            "filename": new_filename,
            "original_name": file.filename,
            "size": len(contents),
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"檔案上傳失敗: {str(e)}")

@app.get("/files/conversation/{conversation_id}")
def get_conversation_files(conversation_id: int):
    """獲取特定對話的所有檔案"""
    try:
        conv_dir = UPLOAD_DIR / str(conversation_id)
        
        if not conv_dir.exists():
            return {
                "status": "success",
                "conversation_id": conversation_id,
                "files": []
            }
        
        files = []
        for file_path in sorted(conv_dir.iterdir()):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "upload_date": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "original_name": "_".join(file_path.name.split("_")[2:])  # 去掉時間戳
                })
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"獲取檔案列表失敗: {str(e)}")

@app.delete("/files/{conversation_id}/{filename}")
def delete_file(conversation_id: int, filename: str):
    """刪除特定檔案"""
    try:
        file_path = UPLOAD_DIR / str(conversation_id) / filename
        
        # 安全檢查 - 確保路徑在上傳目錄內
        try:
            file_path.resolve().relative_to(UPLOAD_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="不允許的檔案路徑")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="檔案不存在")
        
        file_path.unlink()
        
        return {
            "status": "success",
            "message": "檔案已刪除",
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"檔案刪除失敗: {str(e)}")

# ==================== 認證 API ====================

@app.post("/auth/login")
def login(request: LoginRequest):
    """用戶登入"""
    user = user_manager.verify_user(request.username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="用戶名或密碼錯誤")
    
    # 更新最後登入時間
    user_manager.update_last_login(user["user_id"])
    
    # 創建會話令牌
    token = user_manager.create_session(user["user_id"])
    
    if not token:
        raise HTTPException(status_code=500, detail="創建會話失敗")
    
    return {
        "status": "success",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "email": user["email"]
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/logout")
def logout(authorization: str = Header(None)):
    """用戶登出（客戶端刪除令牌即可）"""
    return {
        "status": "success",
        "message": "登出成功",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/auth/me")
def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """獲取當前用戶信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登入")
    
    return {
        "status": "success",
        "user": current_user,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/users")
def create_user(request: CreateUserRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """創建新用戶（僅管理員）"""
    success = user_manager.create_user(
        request.username,
        request.password,
        request.role,
        request.email
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="創建用戶失敗（用戶名可能已存在）")
    
    return {
        "status": "success",
        "message": f"用戶 '{request.username}' 創建成功",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/auth/users")
def get_all_users(current_user: Dict[str, Any] = Depends(require_admin)):
    """獲取所有用戶列表（僅管理員）"""
    users = user_manager.get_all_users()
    
    return {
        "status": "success",
        "users": users,
        "count": len(users),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/auth/conversations")
def get_user_conversations(
    current_user: Dict[str, Any] = Depends(require_auth),
    user_id: Optional[int] = None
):
    """
    獲取用戶的對話列表
    - 一般用戶：只能看到自己的對話
    - 管理員：可以看到所有對話，或指定用戶的對話
    """
    try:
        # 管理員可以查看指定用戶的對話
        if current_user.get("role") == "admin" and user_id is not None:
            target_user_id = user_id
        else:
            # 一般用戶只能看到自己的對話
            target_user_id = current_user.get("user_id")
        
        # 從 UnifiedMemory 表中獲取該用戶的對話
        conn = user_manager.conn_str
        import pyodbc
        conn_obj = pyodbc.connect(conn)
        cursor = conn_obj.cursor()
        
        cursor.execute("""
            SELECT DISTINCT ConversationId
            FROM UnifiedMemory
            WHERE UserId = ?
            ORDER BY ConversationId DESC
        """, (target_user_id,))
        
        conversations = [row.ConversationId for row in cursor.fetchall()]
        conn_obj.close()
        
        return {
            "status": "success",
            "conversations": conversations,
            "user_id": target_user_id,
            "count": len(conversations),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"獲取對話列表失敗: {str(e)}")

@app.get("/auth/messages/{conversation_id}")
def get_conversation_messages(
    conversation_id: int,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    獲取對話消息
    - 一般用戶：只能看到自己的對話
    - 管理員：可以看到所有對話
    """
    try:
        import pyodbc
        
        conn_obj = pyodbc.connect(user_manager.conn_str)
        cursor = conn_obj.cursor()
        
        # 檢查用戶權限
        if current_user.get("role") != "admin":
            # 一般用戶：檢查對話是否屬於自己
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM UnifiedMemory
                WHERE ConversationId = ? AND UserId = ?
            """, (conversation_id, current_user.get("user_id")))
            
            if cursor.fetchone().cnt == 0:
                conn_obj.close()
                raise HTTPException(status_code=403, detail="無權訪問此對話")
        
        # 獲取消息
        cursor.execute("""
            SELECT Role, Content, Timestamp
            FROM UnifiedMemory
            WHERE ConversationId = ?
            ORDER BY Timestamp ASC
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row.Role,
                "content": row.Content,
                "timestamp": row.Timestamp.isoformat() if row.Timestamp else None
            })
        
        conn_obj.close()
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"獲取消息失敗: {str(e)}")

if __name__ == "__main__":
    import os
    port = int(os.getenv("BACKEND_PORT", 5555))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
