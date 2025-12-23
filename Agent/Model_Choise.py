from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, ModelSettings, function_tool
import questionary
import asyncio

external_client = AsyncOpenAI(
    base_url="https://ollama.labelnine.app:5016/v1", 
    api_key="ollama-e28h8JE92-e19hd-dj2h8ak",
)

async def Models_List():
    resp = await external_client.models.list()
    return [m.id async for m in resp]

async def main():
    models = await Models_List()
    choice = await questionary.select(
        "請選擇模型：",
        choices=models,
    ).ask_async()

    print("當前選擇模型為：", choice)

if __name__ == "__main__":
    asyncio.run(main())
    # f = open('Prompt\Prompt.txt', 'r', encoding='utf-8').read()
    # print(f)