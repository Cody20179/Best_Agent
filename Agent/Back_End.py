from Agent import main
import fastapi

app = fastapi.FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/ask")
async def ask_question(user_prompt: str):
    response = await main(user_prompt)
    return {"response": response}

