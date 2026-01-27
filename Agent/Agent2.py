from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, ModelSettings
from dotenv import load_dotenv
import logging
import asyncio
import os

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

    def Create_Agent(self):
        agent = Agent(
            name=self.name,
            instructions=self.System_Prompt,
            model=OpenAIChatCompletionsModel(
                model=self.model_,
                openai_client=self.external_client
            ),
            model_settings=ModelSettings(**self.Model_Set),
            tools=[],
        )
        self.log.info(f"Agent {self.name} created.")
        return agent

class SystemandLogic():
    def __init__(self):
        self.Create_Agent_Log = self.make_logger("Create_Agent_Log", "logs", "logs/Create_Agent_Log.log")
        self.Agent_CAlling_Log = self.make_logger("Agent_CAlling_Log", "logs", "logs/Agent_CAlling_Log.log")
        self.Agent_CAlling_Log.info("SystemandLogic initialized.")
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
    
    async def main(self, input, Agent, max_turns=3):
        result = await Runner.run(
            starting_agent = Agent,
            input = input,
            max_turns = max_turns
        )
        self.Agent_CAlling_Log.info(f"Run completed with final output: {result.final_output}")
        # print(f"[INFO]: {result.final_output}")
        return result.final_output
    
SystemandLogic = SystemandLogic()
CustomAgent = CustomAgent(SystemandLogic.Create_Agent_Log)
AgentA = CustomAgent.Create_Agent()

if __name__ == "__main__":
    result = asyncio.run(SystemandLogic.main("Hi", AgentA, max_turns=3))
    print(result)