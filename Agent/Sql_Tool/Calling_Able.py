from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import pyodbc
import dotenv
import os

dotenv.load_dotenv()

class MemoryType(Enum):
    """記憶類型列舉"""
    CHAT = "chat"           # 對話記憶
    SYSTEM = "system"       # 系統記憶
    CONTEXT = "context"     # 上下文記憶
    KNOWLEDGE = "knowledge" # 知識記憶

class ChatMemoryManager:
    """統一記憶管理器 - 支持多對話 + 系統記憶 + 按編號管理"""
    
    def __init__(self, server=None, database=None, 
                 uid=None, pwd=None):
        """
        初始化統一記憶管理器
        Args:
            server: SQL Server地址（優先使用環境變數）
            database: 數據庫名稱（優先使用環境變數）
            uid: 用戶名（優先使用環境變數）
            pwd: 密碼（優先使用環境變數）
        """
        # 優先使用環境變數，回退到傳入的參數
        self.server = server or os.getenv("MSSQL_HOST") or os.getenv("Server", "140.134.60.229,5677")
        self.database = database or os.getenv("MSSQL_DB") or os.getenv("Database", "Chat_Memory_DB")
        self.uid = uid or os.getenv("MSSQL_USER") or os.getenv("UID", "sa")
        self.pwd = pwd or os.getenv("MSSQL_PASSWORD") or os.getenv("PWD")
        
        # 判斷運行環境，選擇相應的驅動
        is_docker = os.path.exists("/.dockerenv")
        
        if is_docker:
            # Docker 環境使用 FreeTDS
            self.conn_str = (
                f"Driver={{FreeTDS}};"
                f"Server={self.server};"
                f"Port=1433;"
                f"Database={self.database};"
                f"UID={self.uid};"
                f"PWD={self.pwd};"
            )
        else:
            # 本地環境使用 ODBC Driver 18
            self.conn_str = (
                f"Driver={{ODBC Driver 18 for SQL Server}};"
                f"Server={self.server};"
                f"Database={self.database};"
                f"UID={self.uid};"
                f"PWD={self.pwd};"
                "Encrypt=yes;"
                "TrustServerCertificate=yes;"
                "Connection Timeout=5;"
            )
    
    def initialize(self):
        """初始化記憶數據庫和表格"""
        try:
            # 連接到 master 數據庫來創建新數據庫
            master_conn_str = (
                f"Driver={{ODBC Driver 18 for SQL Server}};"
                f"Server={self.server};"
                "Database=master;"
                f"UID={self.uid};"
                f"PWD={self.pwd};"
                "Encrypt=yes;"
                "TrustServerCertificate=yes;"
                "Connection Timeout=5;"
            )
            
            conn = pyodbc.connect(master_conn_str, timeout=5, autocommit=True)
            cur = conn.cursor()
            
            # 檢查數據庫是否存在
            cur.execute(f"SELECT name FROM sys.databases WHERE name = '{self.database}'")
            if not cur.fetchone():
                print(f"Creating database {self.database}...")
                cur.execute(f"CREATE DATABASE [{self.database}]")
                print(f"Database {self.database} created successfully.")
            else:
                print(f"Database {self.database} already exists.")
            
            cur.close()
            conn.close()
            
            # 連接到新數據庫並創建表格
            chat_conn = pyodbc.connect(self.conn_str, timeout=5)
            chat_cur = chat_conn.cursor()
            
            # 檢查統一記憶表是否存在
            chat_cur.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME = 'UnifiedMemory'
            """)
            
            if not chat_cur.fetchone():
                print("Creating UnifiedMemory table...")
                chat_cur.execute("""
                CREATE TABLE UnifiedMemory (
                    Id INT IDENTITY(1,1) PRIMARY KEY,
                    ConversationId INT NOT NULL,
                    MemoryType NVARCHAR(50) NOT NULL,
                    Role NVARCHAR(50),
                    Content NVARCHAR(MAX) NOT NULL,
                    Metadata NVARCHAR(MAX),
                    CreatedAt DATETIME DEFAULT GETDATE(),
                    UpdatedAt DATETIME DEFAULT GETDATE(),
                    INDEX idx_conversation (ConversationId),
                    INDEX idx_memory_type (MemoryType),
                    INDEX idx_conversation_type (ConversationId, MemoryType)
                )
                """)
                chat_conn.commit()
                print("UnifiedMemory table created successfully.")
            else:
                print("UnifiedMemory table already exists.")
            
            # 檢查系統記憶表是否存在
            chat_cur.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME = 'SystemMemory'
            """)
            
            if not chat_cur.fetchone():
                print("Creating SystemMemory table...")
                chat_cur.execute("""
                CREATE TABLE SystemMemory (
                    Id INT IDENTITY(1,1) PRIMARY KEY,
                    MemoryKey NVARCHAR(255) NOT NULL UNIQUE,
                    Content NVARCHAR(MAX) NOT NULL,
                    Metadata NVARCHAR(MAX),
                    CreatedAt DATETIME DEFAULT GETDATE(),
                    UpdatedAt DATETIME DEFAULT GETDATE()
                )
                """)
                chat_conn.commit()
                print("SystemMemory table created successfully.")
            else:
                print("SystemMemory table already exists.")
            
            chat_cur.close()
            chat_conn.close()
            
            return True
        
        except Exception as e:
            print(f"Error initializing memory database: {e}")
            return False
    
    # ==================== 對話記憶操作 ====================
    
    def save_message(self, conversation_id: int, role: str, content: str, 
                    memory_type: MemoryType = MemoryType.CHAT, metadata: str = None, user_id: int = None):
        """
        保存單條聊天消息
        Args:
            conversation_id: 對話編號
            role: "user" 或 "assistant"
            content: 消息內容
            memory_type: 記憶類型
            metadata: 額外元數據（JSON格式）
            user_id: 用戶ID（可選）
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            INSERT INTO UnifiedMemory (ConversationId, MemoryType, Role, Content, Metadata, UserId)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, memory_type.value, role, content, metadata, user_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✓ Saved: [Conv-{conversation_id}] [{role}] {content[:50]}...")
            return True
        
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False
    
    
    def save_messages_batch(self, conversation_id: int, messages: List[Dict[str, str]], 
                           memory_type: MemoryType = MemoryType.CHAT, user_id: int = None):
        """
        批量保存聊天消息（Agent格式）
        Args:
            conversation_id: 對話編號
            messages: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            memory_type: 記憶類型
            user_id: 用戶ID（可選）
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                cur.execute("""
                INSERT INTO UnifiedMemory (ConversationId, MemoryType, Role, Content, UserId)
                VALUES (?, ?, ?, ?, ?)
                """, (conversation_id, memory_type.value, role, content, user_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✓ Batch saved {len(messages)} messages to conversation: {conversation_id}")
            return True
        
        except Exception as e:
            print(f"Error saving batch chat messages: {e}")
            return False
    
    def get_messages(self, conversation_id: int, limit: int = 100, 
                    memory_type: MemoryType = MemoryType.CHAT) -> List[Dict[str, Any]]:
        """
        獲取對話記憶（含時間戳）
        Args:
            conversation_id: 對話編號
            limit: 返回消息數量限制
            memory_type: 記憶類型
        Returns:
            [{"role": "user", "content": "...", "timestamp": "..."}]
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            sql = f"""
            SELECT TOP {limit} Role, Content, CreatedAt, Metadata
            FROM UnifiedMemory 
            WHERE ConversationId = ? AND MemoryType = ?
            ORDER BY CreatedAt ASC
            """
            cur.execute(sql, (conversation_id, memory_type.value))
            
            messages = []
            for row in cur.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2].isoformat() if row[2] else None,
                    "metadata": row[3]
                })
            
            cur.close()
            conn.close()
            
            return messages
        
        except Exception as e:
            print(f"Error getting chat messages: {e}")
            return []
    
    
    def get_messages_for_agent(self, conversation_id: int, limit: int = 100, 
                               memory_type: MemoryType = MemoryType.CHAT) -> List[Dict[str, str]]:
        """
        獲取對話記憶（Agent格式 - 無時間戳）
        Args:
            conversation_id: 對話編號
            limit: 返回消息數量限制
            memory_type: 記憶類型
        Returns:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            sql = f"""
            SELECT TOP {limit} Role, Content 
            FROM UnifiedMemory 
            WHERE ConversationId = ? AND MemoryType = ?
            ORDER BY CreatedAt ASC
            """
            cur.execute(sql, (conversation_id, memory_type.value))
            
            messages = []
            for row in cur.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1]
                })
            
            cur.close()
            conn.close()
            
            return messages
        
        except Exception as e:
            print(f"Error getting chat messages for agent: {e}")
            return []
    
    def clear_messages(self, conversation_id: int = None, memory_type: MemoryType = None):
        """
        清空對話記憶
        Args:
            conversation_id: 對話編號（如果為 None，則清空所有記錄）
            memory_type: 記憶類型（如果為 None，則清空該對話的所有類型）
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            if conversation_id is not None:
                if memory_type is not None:
                    cur.execute("""
                    DELETE FROM UnifiedMemory 
                    WHERE ConversationId = ? AND MemoryType = ?
                    """, (conversation_id, memory_type.value))
                    print(f"✓ Cleared {memory_type.value} memory for conversation: {conversation_id}")
                else:
                    cur.execute("""
                    DELETE FROM UnifiedMemory 
                    WHERE ConversationId = ?
                    """, (conversation_id,))
                    print(f"✓ Cleared all memories for conversation: {conversation_id}")
            else:
                cur.execute("DELETE FROM UnifiedMemory")
                print("✓ Cleared all memories.")
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Error clearing memories: {e}")
            return False
    
    # ==================== 系統記憶操作 ====================
    
    def save_system_memory(self, memory_key: str, content: str, metadata: str = None) -> bool:
        """
        保存系統記憶
        Args:
            memory_key: 記憶鍵（唯一標識）
            content: 記憶內容
            metadata: 額外元數據
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            # 檢查是否已存在
            cur.execute("SELECT Id FROM SystemMemory WHERE MemoryKey = ?", (memory_key,))
            existing = cur.fetchone()
            
            if existing:
                # 更新
                cur.execute("""
                UPDATE SystemMemory 
                SET Content = ?, Metadata = ?, UpdatedAt = GETDATE()
                WHERE MemoryKey = ?
                """, (content, metadata, memory_key))
                print(f"✓ Updated system memory: {memory_key}")
            else:
                # 插入
                cur.execute("""
                INSERT INTO SystemMemory (MemoryKey, Content, Metadata)
                VALUES (?, ?, ?)
                """, (memory_key, content, metadata))
                print(f"✓ Saved system memory: {memory_key}")
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Error saving system memory: {e}")
            return False
    
    def get_system_memory(self, memory_key: str) -> Optional[Dict[str, Any]]:
        """
        獲取系統記憶
        Args:
            memory_key: 記憶鍵
        Returns:
            {"content": "...", "metadata": "...", "updated_at": "..."} 或 None
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT Content, Metadata, UpdatedAt 
            FROM SystemMemory 
            WHERE MemoryKey = ?
            """, (memory_key,))
            
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row:
                return {
                    "content": row[0],
                    "metadata": row[1],
                    "updated_at": row[2].isoformat() if row[2] else None
                }
            return None
        
        except Exception as e:
            print(f"Error getting system memory: {e}")
            return None
    
    def update_system_memory(self, memory_key: str, content: str = None, metadata: str = None) -> bool:
        """
        更新系統記憶
        Args:
            memory_key: 記憶鍵
            content: 新的記憶內容
            metadata: 新的元數據
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            # 檢查是否存在
            cur.execute("SELECT Id FROM SystemMemory WHERE MemoryKey = ?", (memory_key,))
            if not cur.fetchone():
                print(f"✗ System memory not found: {memory_key}")
                cur.close()
                conn.close()
                return False
            
            # 構建動態 UPDATE 語句
            update_fields = []
            params = []
            
            if content is not None:
                update_fields.append("Content = ?")
                params.append(content)
            
            if metadata is not None:
                update_fields.append("Metadata = ?")
                params.append(metadata)
            
            if update_fields:
                update_fields.append("UpdatedAt = GETDATE()")
                params.append(memory_key)
                
                sql = f"UPDATE SystemMemory SET {', '.join(update_fields)} WHERE MemoryKey = ?"
                cur.execute(sql, params)
                conn.commit()
                print(f"✓ Updated system memory: {memory_key}")
            
            cur.close()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Error updating system memory: {e}")
            return False
    
    def delete_system_memory(self, memory_key: str = None) -> bool:
        """
        刪除系統記憶
        Args:
            memory_key: 記憶鍵（如果為 None，則刪除所有系統記憶）
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            if memory_key:
                cur.execute("DELETE FROM SystemMemory WHERE MemoryKey = ?", (memory_key,))
                print(f"✓ Deleted system memory: {memory_key}")
            else:
                cur.execute("DELETE FROM SystemMemory")
                print("✓ Deleted all system memories")
            
            conn.commit()
            cur.close()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Error deleting system memory: {e}")
            return False
    
    def get_all_system_memories(self) -> List[Dict[str, Any]]:
        """獲取所有系統記憶"""
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT MemoryKey, Content, Metadata, UpdatedAt 
            FROM SystemMemory 
            ORDER BY UpdatedAt DESC
            """)
            
            memories = []
            for row in cur.fetchall():
                memories.append({
                    "key": row[0],
                    "content": row[1],
                    "metadata": row[2],
                    "updated_at": row[3].isoformat() if row[3] else None
                })
            
            cur.close()
            conn.close()
            
            return memories
        
        except Exception as e:
            print(f"Error getting all system memories: {e}")
            return []
    
    
    # ==================== 統計與查詢 ====================
    
    def get_all_conversations(self) -> List[int]:
        """獲取所有對話編號"""
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT DISTINCT ConversationId 
            FROM UnifiedMemory 
            ORDER BY ConversationId
            """)
            conversations = [row[0] for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            return conversations
        
        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []
    
    def get_conversation_statistics(self, conversation_id: int) -> Dict[str, Any]:
        """獲取對話統計信息"""
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT 
                COUNT(*) as TotalMessages,
                SUM(CASE WHEN Role = 'user' THEN 1 ELSE 0 END) as UserMessages,
                SUM(CASE WHEN Role = 'assistant' THEN 1 ELSE 0 END) as AssistantMessages,
                MIN(CreatedAt) as FirstMessage,
                MAX(CreatedAt) as LastMessage
            FROM UnifiedMemory 
            WHERE ConversationId = ?
            """, (conversation_id,))
            
            row = cur.fetchone()
            
            stats = {
                "conversation_id": conversation_id,
                "total_messages": row[0] if row[0] else 0,
                "user_messages": row[1] if row[1] else 0,
                "assistant_messages": row[2] if row[2] else 0,
                "first_message_time": row[3].isoformat() if row[3] else None,
                "last_message_time": row[4].isoformat() if row[4] else None
            }
            
            cur.close()
            conn.close()
            
            return stats
        
        except Exception as e:
            print(f"Error getting conversation statistics: {e}")
            return {}
    
    def get_memory_types_count(self) -> Dict[str, int]:
        """獲取各類型記憶的數量"""
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT MemoryType, COUNT(*) as Count
            FROM UnifiedMemory 
            GROUP BY MemoryType
            """)
            
            counts = {}
            for row in cur.fetchall():
                counts[row[0]] = row[1]
            
            cur.close()
            conn.close()
            
            return counts
        
        except Exception as e:
            print(f"Error getting memory types count: {e}")
            return {}
    
    def search_messages(self, conversation_id: int, keyword: str, 
                       memory_type: MemoryType = MemoryType.CHAT) -> List[Dict[str, Any]]:
        """
        搜索對話中的消息
        Args:
            conversation_id: 對話編號
            keyword: 搜索關鍵詞
            memory_type: 記憶類型
        """
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT Role, Content, CreatedAt, Metadata
            FROM UnifiedMemory 
            WHERE ConversationId = ? AND MemoryType = ? AND Content LIKE ?
            ORDER BY CreatedAt DESC
            """, (conversation_id, memory_type.value, f"%{keyword}%"))
            
            messages = []
            for row in cur.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2].isoformat() if row[2] else None,
                    "metadata": row[3]
                })
            
            cur.close()
            conn.close()
            
            return messages
        
        except Exception as e:
            print(f"Error searching messages: {e}")
            return []
    
    def get_system_memory_summary(self) -> Dict[str, Any]:
        """獲取系統記憶摘要"""
        try:
            conn = pyodbc.connect(self.conn_str, timeout=5)
            cur = conn.cursor()
            
            cur.execute("""
            SELECT 
                COUNT(*) as TotalMemories,
                MIN(CreatedAt) as FirstCreated,
                MAX(UpdatedAt) as LastUpdated
            FROM SystemMemory
            """)
            
            row = cur.fetchone()
            
            summary = {
                "total_memories": row[0] if row[0] else 0,
                "first_created": row[1].isoformat() if row[1] else None,
                "last_updated": row[2].isoformat() if row[2] else None
            }
            
            cur.close()
            conn.close()
            
            return summary
        
        except Exception as e:
            print(f"Error getting system memory summary: {e}")
            return {}

class UserRole(Enum):
    """用戶角色列舉"""
    USER = "user"       # 一般用戶
    ADMIN = "admin"     # 超級管理員

class UserManager:
    """用戶管理器 - 處理用戶認證、權限和用戶數據隔離"""
    
    def __init__(self, server=None, database=None, 
                 uid=None, pwd=None):
        """
        初始化用戶管理器
        Args:
            server: SQL Server地址（優先使用環境變數）
            database: 數據庫名稱（優先使用環境變數）
            uid: 用戶名（優先使用環境變數）
            pwd: 密碼（優先使用環境變數）
        """
        # 優先使用環境變數
        self.server = server or os.getenv("MSSQL_HOST", "140.134.60.229,5677")
        self.database = database or os.getenv("MSSQL_DB", "Chat_Memory_DB")
        self.uid = uid or os.getenv("MSSQL_USER", "sa")
        self.pwd = pwd or os.getenv("MSSQL_PASSWORD", "!ok*L9bicP")
        
        # 判斷運行環境，選擇相應的驅動
        is_docker = os.path.exists("/.dockerenv")
        
        if is_docker:
            # Docker 環境使用 FreeTDS
            self.conn_str = (
                f"Driver={{FreeTDS}};"
                f"Server={self.server};"
                f"Port=1433;"
                f"Database={self.database};"
                f"UID={self.uid};"
                f"PWD={self.pwd};"
            )
        else:
            # 本地環境使用 ODBC Driver 18
            self.conn_str = (
                f"Driver={{ODBC Driver 18 for SQL Server}};"
                f"Server={self.server};"
                f"Database={self.database};"
                f"UID={self.uid};"
                f"PWD={self.pwd};"
                "Encrypt=yes;"
                "TrustServerCertificate=yes;"
                "Connection Timeout=5;"
            )
    
    def initialize_user_tables(self):
        """初始化用戶相關數據表"""
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            # 創建用戶表
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
                CREATE TABLE Users (
                    UserId INT IDENTITY(1,1) PRIMARY KEY,
                    Username NVARCHAR(50) UNIQUE NOT NULL,
                    Password NVARCHAR(255) NOT NULL,
                    Role NVARCHAR(20) NOT NULL DEFAULT 'user',
                    Email NVARCHAR(100),
                    CreatedAt DATETIME DEFAULT GETDATE(),
                    LastLogin DATETIME,
                    IsActive BIT DEFAULT 1
                )
            """)
            
            # 創建用戶會話表（用於存儲登入令牌）
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'UserSessions')
                CREATE TABLE UserSessions (
                    SessionId INT IDENTITY(1,1) PRIMARY KEY,
                    UserId INT NOT NULL,
                    Token NVARCHAR(255) UNIQUE NOT NULL,
                    CreatedAt DATETIME DEFAULT GETDATE(),
                    ExpiresAt DATETIME NOT NULL,
                    FOREIGN KEY (UserId) REFERENCES Users(UserId)
                )
            """)
            
            # 為 UnifiedMemory 表添加 UserId 列（如果不存在）
            try:
                cursor.execute("""
                    ALTER TABLE UnifiedMemory 
                    ADD UserId INT NULL
                """)
            except:
                pass  # 列可能已存在
            
            # 創建索引以提升查詢性能
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Users_Username')
                CREATE UNIQUE INDEX IX_Users_Username ON Users(Username)
            """)
            
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_UserSessions_Token')
                CREATE UNIQUE INDEX IX_UserSessions_Token ON UserSessions(Token)
            """)
            
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_UnifiedMemory_UserId')
                CREATE INDEX IX_UnifiedMemory_UserId ON UnifiedMemory(UserId)
            """)
            
            conn.commit()
            conn.close()
            print("✓ 用戶數據表初始化成功")
            return True
            
        except Exception as e:
            print(f"✗ 用戶數據表初始化失敗: {e}")
            return False
    
    def create_user(self, username: str, password: str, role: str = "user", email: str = None) -> bool:
        """
        創建新用戶
        Args:
            username: 用戶名
            password: 密碼（明文，會被哈希）
            role: 角色（user 或 admin）
            email: 郵箱（可選）
        Returns:
            是否創建成功
        """
        try:
            import hashlib
            # 簡單的密碼哈希（生產環境應使用 bcrypt）
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO Users (Username, Password, Role, Email)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash, role, email))
            
            conn.commit()
            conn.close()
            return True
            
        except pyodbc.IntegrityError:
            print(f"✗ 用戶名 '{username}' 已存在")
            return False
        except Exception as e:
            print(f"✗ 創建用戶失敗: {e}")
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        驗證用戶登入
        Args:
            username: 用戶名
            password: 密碼
        Returns:
            用戶信息字典（如果驗證成功）或 None
        """
        try:
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT UserId, Username, Role, Email, IsActive
                FROM Users
                WHERE Username = ? AND Password = ?
            """, (username, password_hash))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row.IsActive:
                return {
                    "user_id": row.UserId,
                    "username": row.Username,
                    "role": row.Role,
                    "email": row.Email
                }
            return None
            
        except Exception as e:
            print(f"✗ 驗證用戶失敗: {e}")
            return None
    
    def create_session(self, user_id: int, hours_valid: int = 24) -> Optional[str]:
        """
        創建用戶會話令牌
        Args:
            user_id: 用戶ID
            hours_valid: 令牌有效時長（小時）
        Returns:
            會話令牌或 None
        """
        try:
            import uuid
            from datetime import timedelta
            
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=hours_valid)
            
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO UserSessions (UserId, Token, ExpiresAt)
                VALUES (?, ?, ?)
            """, (user_id, token, expires_at))
            
            conn.commit()
            conn.close()
            return token
            
        except Exception as e:
            print(f"✗ 創建會話失敗: {e}")
            return None
    
    def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        驗證會話令牌
        Args:
            token: 會話令牌
        Returns:
            用戶信息字典或 None
        """
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.UserId, u.Username, u.Role, u.Email, s.ExpiresAt
                FROM Users u
                INNER JOIN UserSessions s ON u.UserId = s.UserId
                WHERE s.Token = ? AND u.IsActive = 1 AND s.ExpiresAt > GETDATE()
            """, (token,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "user_id": row.UserId,
                    "username": row.Username,
                    "role": row.Role,
                    "email": row.Email
                }
            return None
            
        except Exception as e:
            print(f"✗ 驗證會話失敗: {e}")
            return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """獲取所有用戶列表（僅管理員）"""
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT UserId, Username, Role, Email, CreatedAt, LastLogin, IsActive
                FROM Users
                ORDER BY CreatedAt DESC
            """)
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "user_id": row.UserId,
                    "username": row.Username,
                    "role": row.Role,
                    "email": row.Email,
                    "created_at": row.CreatedAt.isoformat() if row.CreatedAt else None,
                    "last_login": row.LastLogin.isoformat() if row.LastLogin else None,
                    "is_active": row.IsActive
                })
            
            conn.close()
            return users
            
        except Exception as e:
            print(f"✗ 獲取用戶列表失敗: {e}")
            return []
    
    def update_last_login(self, user_id: int):
        """更新用戶最後登入時間"""
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE Users
                SET LastLogin = GETDATE()
                WHERE UserId = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"✗ 更新登入時間失敗: {e}")


if __name__ == "__main__":
    print("="*70)
    print("統一記憶系統測試 - 多對話 + 系統記憶")
    print("="*70)
    
    # 初始化管理器
    manager = ChatMemoryManager()
    
    # 1. 初始化數據庫
    print("\n[1] 初始化數據庫...")
    manager.initialize()
    
    # 2. 測試對話記憶保存 - 對話 1
    print("\n[2] 測試對話記憶 (對話編號: 1)...")
    messages_conv1 = [
        {"role": "user", "content": "你好，今天天氣如何？"},
        {"role": "assistant", "content": "今天是個晴天，非常舒適！"},
        {"role": "user", "content": "謝謝你的回答"}
    ]
    manager.save_messages_batch(1, messages_conv1, MemoryType.CHAT)
    
    # 3. 測試對話記憶保存 - 對話 2
    print("\n[3] 測試對話記憶 (對話編號: 2)...")
    messages_conv2 = [
        {"role": "user", "content": "幫我計算 2+2=?"},
        {"role": "assistant", "content": "2+2=4"},
        {"role": "user", "content": "那 3+3=?"},
        {"role": "assistant", "content": "3+3=6"}
    ]
    manager.save_messages_batch(2, messages_conv2, MemoryType.CHAT)
    
    # 4. 測試系統記憶
    print("\n[4] 測試系統記憶...")
    manager.save_system_memory("system_prompt", "你是一個友善的AI助手")
    manager.save_system_memory("user_profile", "用戶來自台灣，喜歡技術話題", '{"level": "advanced"}')
    manager.save_system_memory("conversation_rules", "保持禮貌，避免敏感話題")
    
    # 5. 讀取對話 1
    print("\n[5] 讀取對話 1...")
    chat_history_1 = manager.get_messages(1)
    print("對話記錄（含時間戳）:")
    for msg in chat_history_1:
        print(f"  {msg['role']:10s} | {msg['content'][:40]}")
    
    # 6. 讀取對話 2（Agent 格式）
    print("\n[6] 讀取對話 2 (Agent 格式)...")
    agent_messages = manager.get_messages_for_agent(2)
    for msg in agent_messages:
        print(f"  {msg}")
    
    # 7. 讀取系統記憶
    print("\n[7] 讀取系統記憶...")
    system_memory = manager.get_system_memory("system_prompt")
    print(f"  system_prompt: {system_memory['content'] if system_memory else 'Not found'}")
    
    user_profile = manager.get_system_memory("user_profile")
    print(f"  user_profile: {user_profile['content'] if user_profile else 'Not found'}")
    print(f"    metadata: {user_profile['metadata'] if user_profile else 'N/A'}")
    
    # 8. 查看所有系統記憶
    print("\n[8] 所有系統記憶...")
    all_sys_memories = manager.get_all_system_memories()
    for mem in all_sys_memories:
        print(f"  {mem['key']}: {mem['content'][:50]}...")
    
    # 9. 更新系統記憶
    print("\n[9] 更新系統記憶...")
    manager.update_system_memory("user_profile", content="用戶來自台灣，喜歡AI和機器學習")
    updated_profile = manager.get_system_memory("user_profile")
    print(f"  更新後: {updated_profile['content'] if updated_profile else 'Not found'}")
    
    # 10. 統計
    print("\n[10] 對話統計...")
    stats_1 = manager.get_conversation_statistics(1)
    print(f"  對話 1:")
    print(f"    總消息數: {stats_1['total_messages']}")
    print(f"    用戶消息: {stats_1['user_messages']}")
    print(f"    助手消息: {stats_1['assistant_messages']}")
    
    # 11. 查看所有對話
    print("\n[11] 所有對話編號...")
    conversations = manager.get_all_conversations()
    print(f"  對話列表: {conversations}")
    
    # 12. 記憶類型統計
    print("\n[12] 記憶類型統計...")
    memory_counts = manager.get_memory_types_count()
    for mem_type, count in memory_counts.items():
        print(f"  {mem_type}: {count}")
    
    # 13. 搜索功能
    print("\n[13] 搜索對話 2 中的 '3'...")
    search_results = manager.search_messages(2, "3", MemoryType.CHAT)
    for result in search_results:
        print(f"  {result['role']}: {result['content']}")
    
    # 14. 系統記憶摘要
    print("\n[14] 系統記憶摘要...")
    sys_summary = manager.get_system_memory_summary()
    print(f"  總記憶數: {sys_summary['total_memories']}")
    print(f"  最後更新: {sys_summary['last_updated']}")
    
    # 15. 清除特定記憶
    print("\n[15] 清除對話 1 的記憶...")
    manager.clear_messages(1)
    
    # 16. 驗證清除
    print("\n[16] 驗證清除...")
    remaining = manager.get_messages(1)
    print(f"  對話 1 剩餘消息數: {len(remaining)}")
    
    # 17. 刪除系統記憶
    print("\n[17] 刪除特定系統記憶...")
    manager.delete_system_memory("conversation_rules")
    all_memories_after = manager.get_all_system_memories()
    print(f"  剩餘系統記憶數: {len(all_memories_after)}")
    
    print("\n" + "="*70)
    print("✓ 統一記憶系統測試完成！")
    print("="*70)

