from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db import lifespan

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def home():
    return HTMLResponse("暨大管院空間系統")