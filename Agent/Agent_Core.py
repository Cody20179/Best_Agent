from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, ModelSettings
from Sql_Tool.Calling_Able import ChatMemoryManager, MemoryType
from Sql_Tool.MsSQL_Tool import Show_Tables, Query_SQL
from Rag_Tool.Retrieval import Retrieval_Tool_Text
from dotenv import load_dotenv
import logging
import asyncio
import os
from datetime import datetime

class CustomAgent:
    def __init__(self, logger):
        load_dotenv()
        self.log = logger
        self.log.info("Environment variables loaded.")

        self.base_url = os.getenv("Ollama_Api_URL")
        self.api_key = os.getenv("Ollama_Api_Key")
        self.external_client = None
        self.Connect_Models()

        self.name = "Assistant"
        self.model_ = "gpt-oss:20b"
        self.Prompt_Path = r"Prompt\Prompt.txt"
        self.System_Prompt = None
        self.Load_System_Prompt()

        self.Model_Set = {
            "temperature": 0.2,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3
        }
        self.log.info("Agent settings initialized.")

    def Connect_Models(self):
        try:
            self.external_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
            self.log.info(f"Connected to external model {self.external_client.base_url}.")
        except Exception as e:
            self.log.error(f"Failed to connect to external model. Error: {e}")

    def Load_System_Prompt(self):
        try:
            self.System_Prompt = open(self.Prompt_Path, "r", encoding="utf-8").read()
            self.log.info(f"System prompt loaded from {self.Prompt_Path}, Lens = {len(self.System_Prompt)}.")
        except Exception as e:
            self.log.error(f"Failed to load system prompt from {self.Prompt_Path}. Error: {e}")

    def Create_Agent(self, Tool_List = []):
        """Create or Update Agent"""
        agent = Agent(
            name=self.name,
            instructions=self.System_Prompt,
            model=OpenAIChatCompletionsModel(
                model=self.model_,
                openai_client=self.external_client
            ),
            model_settings=ModelSettings(**self.Model_Set),
            tools=Tool_List,
        )
        self.log.info(f"Agent {self.name} created.")
        return agent

class SystemandLogic():
    def __init__(self):
        self.Create_Agent_Log = self.make_logger("Create_Agent_Log", "logs", "logs/Create_Agent_Log.log")
        self.Agent_CAlling_Log = self.make_logger("Agent_CAlling_Log", "logs", "logs/Agent_CAlling_Log.log")
        self.Agent_CAlling_Log.info("Log initialized.")

        self.manager = ChatMemoryManager()
        self.manager.initialize()
        self.Agent_CAlling_Log.info("Memory initialized.")
        
        # 當前對話編號（可動態設置）
        self.current_conversation_id = 1
        self.Agent_CAlling_Log.info(f"Conversation ID set to: {self.current_conversation_id}")

        # print("[INFO]: SystemandLogic initialized.")
        pass

    def make_logger(self, name, file_folder, filepath):
        os.makedirs(file_folder, exist_ok=True)
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()  # 避免重複掛 handler

        handler = logging.FileHandler(filepath, mode="w", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger
    
    def set_conversation_id(self, conversation_id: int):
        """設置當前對話編號"""
        self.current_conversation_id = conversation_id
        self.Agent_CAlling_Log.info(f"Conversation ID changed to: {conversation_id}")
    
    def load_system_memory(self):
        """加載系統記憶到 Agent 提示詞"""
        try:
            system_memory = self.manager.get_system_memory("system_prompt")
            if system_memory:
                return system_memory['content']
            return None
        except Exception as e:
            self.Agent_CAlling_Log.error(f"Error loading system memory: {e}")
            return None
    
    def save_system_memory(self, key: str, content: str, metadata: str = None):
        """保存系統記憶"""
        try:
            return self.manager.save_system_memory(key, content, metadata)
        except Exception as e:
            self.Agent_CAlling_Log.error(f"Error saving system memory: {e}")
            return False
    
    async def main(self, input, Agent, max_turns=3):
        """
        執行Agent - 帶對話記憶 + 系統記憶
        Args:
            input: 用戶輸入文本
            Agent: Agent實例
            max_turns: 最大轉數
        """
        try:
            # 1. 獲取對話歷史消息（Agent格式）
            history_messages = self.manager.get_messages_for_agent(
                self.current_conversation_id, 
                limit=20,
                memory_type=MemoryType.CHAT
            )
            
            # 2. 組合歷史消息 + 當前用戶輸入
            full_input = history_messages + [{"role": "user", "content": input}]
            self.Agent_CAlling_Log.info(f"Conversation {self.current_conversation_id}: Running Agent with {len(history_messages)} history messages.")
            
            # 3. 執行Agent
            result = await Runner.run(
                starting_agent=Agent,
                input=full_input,
                max_turns=max_turns
            )
            
            self.Agent_CAlling_Log.info(f"Conversation {self.current_conversation_id}: Run completed.")
            self.Agent_CAlling_Log.info(f"Final output: {result.final_output[:100]}...")
            
            # 4. 保存當前對話到數據庫
            messages = [
                {"role": "user", "content": input},
                {"role": "assistant", "content": result.final_output}
            ]
            self.manager.save_messages_batch(
                self.current_conversation_id,
                messages, 
                memory_type=MemoryType.CHAT
            )
            self.Agent_CAlling_Log.info(f"Messages saved to conversation {self.current_conversation_id}.")
            
            return result.final_output
        
        except Exception as e:
            self.Agent_CAlling_Log.error(f"Error in main(): {e}")
            raise
    
    def get_conversation_summary(self) -> dict:
        """獲取當前對話摘要"""
        return self.manager.get_conversation_statistics(self.current_conversation_id)
    
    def switch_conversation(self, conversation_id: int):
        """切換對話"""
        self.set_conversation_id(conversation_id)
        stats = self.get_conversation_summary()
        self.Agent_CAlling_Log.info(f"Switched to conversation {conversation_id}: {stats['total_messages']} messages")
    
    def clear_current_conversation(self):
        """清除當前對話所有記憶"""
        self.manager.clear_messages(self.current_conversation_id)
        self.Agent_CAlling_Log.info(f"Cleared all memories for conversation {self.current_conversation_id}")
    
    def list_all_conversations(self):
        """列出所有對話"""
        conversations = self.manager.get_all_conversations()
        return conversations


SystemandLogic = SystemandLogic()
CustomAgent = CustomAgent(SystemandLogic.Create_Agent_Log)
# 創建Agent實例
Agent_ = CustomAgent.Create_Agent(Tool_List=[Show_Tables, Query_SQL, Retrieval_Tool_Text])

if __name__ == "__main__":
    print("="*70)
    print("Agent 多對話系統")
    print("="*70)
    print("\n命令:")
    print("  /list - 列出所有對話")
    print("  /new <id> - 開始新對話（編號 id）")
    print("  /stats - 當前對話統計")
    print("  /clear - 清除當前對話")
    print("  /quit - 退出")
    print("  其他輸入 - 提交給 Agent")
    print("="*70)
    
    while True:
        try:
            user_input = input(f"\n[Conv-{SystemandLogic.current_conversation_id}] User: ").strip()
            
            if not user_input:
                continue
            
            # 命令處理
            if user_input.lower() == "/quit":
                print("Goodbye!")
                break
            
            elif user_input.lower() == "/list":
                conversations = SystemandLogic.list_all_conversations()
                print(f"All conversations: {conversations}")
                continue
            
            elif user_input.lower().startswith("/new"):
                try:
                    conv_id = int(user_input.split()[1])
                    SystemandLogic.switch_conversation(conv_id)
                    print(f"✓ Switched to conversation {conv_id}")
                except (ValueError, IndexError):
                    print("Usage: /new <conversation_id>")
                continue
            
            elif user_input.lower() == "/stats":
                stats = SystemandLogic.get_conversation_summary()
                print(f"\nConversation {SystemandLogic.current_conversation_id} Statistics:")
                print(f"  Total messages: {stats['total_messages']}")
                print(f"  User messages: {stats['user_messages']}")
                print(f"  Assistant messages: {stats['assistant_messages']}")
                print(f"  First message: {stats['first_message_time']}")
                print(f"  Last message: {stats['last_message_time']}")
                continue
            
            elif user_input.lower() == "/clear":
                SystemandLogic.clear_current_conversation()
                print(f"✓ Cleared conversation {SystemandLogic.current_conversation_id}")
                continue
            
            # 提交給 Agent
            print("\n[Agent is thinking...]")
            result = asyncio.run(SystemandLogic.main(user_input, Agent_, max_turns=10))
            print(f"\n[Agent] {result}")
        
        except KeyboardInterrupt:
            print("\n\nKeyboard interrupt. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue

