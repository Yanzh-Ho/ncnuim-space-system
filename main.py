from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from db import lifespan

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="ncnuim-space-secret")
templates = Jinja2Templates(directory="templates")

# ===== 各模組的 router =====
from routes.account import router as accountRoute
app.include_router(accountRoute, prefix="/account")


@app.get("/")
async def home(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse(name="home.html", request=request, context={"user": user})


app.mount("/static", StaticFiles(directory="static"), name="static")
