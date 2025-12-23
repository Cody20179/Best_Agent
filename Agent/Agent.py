from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, ModelSettings
from Rag_Tool.Retrieval import Retrieval_Tool_Text
from Sql_Tool.MsSQL_Tool import Show_Tables, Query_SQL
from VisionTool.Base64Tool import image_to_base64
import asyncio

from memory_json import JsonMemoryStore  

external_client = AsyncOpenAI(
    base_url="https://ollama.labelnine.app:5016/v1", 
    api_key="ollama-e28h8JE92-e19hd-dj2h8ak",
)

System_Prompt = open(r'Prompt\Prompt.txt', 'r', encoding='utf-8').read()

agent = Agent(
    name="Assistant",
    instructions=System_Prompt,
    model=OpenAIChatCompletionsModel(
        model="gpt-oss:20b",
        openai_client=external_client
    ),
    model_settings=ModelSettings(
        temperature=0.2,
        top_p=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.3
    ),
    tools=[Show_Tables, Query_SQL, Retrieval_Tool_Text, 
           image_to_base64],
)

memory = JsonMemoryStore(path="agent_memory.json", keep_last=40)

async def main(user_prompt):
    print(user_prompt)
    background_prompt = """
    You are a LLM Assister, 
    You Must help user to finish work when they ask,
    """ 

    past_items = memory.load()

    run_input = []
    run_input.extend(past_items)

    run_input.append({
        "role": "user",
        "content": background_prompt + "\n\n" + user_prompt
    })


    result = await Runner.run(
        starting_agent=agent,
        input=run_input,
        max_turns=3
    )

    print(f"使用者問題：{user_prompt}")
    print(f"系統回覆：{result.final_output}")


    try:
        new_memory_items = result.to_input_list()
        memory.append(new_memory_items)
    except Exception as e:
        print(f"[Memory] Save failed: {e}")


    return result.final_output

if __name__ == "__main__":
    # user_prompt = """ 幫我檢索並整理 設備使用費 以及 熱處理 內容

    # """
    # asyncio.run(main(user_prompt))


    for i in range(10):
        user_prompt = input("請輸入您的問題：")
        asyncio.run(main(user_prompt))