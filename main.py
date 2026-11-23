from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware.sessions import SessionMiddleware
from db import lifespan
from auth import currentUser
from routes.space import router as space_router

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="ncnuim-space-secret")
templates = Jinja2Templates(directory="templates")

# ===== 各模組的 router =====
from routes.account import router as accountRoute
app.include_router(accountRoute, prefix="/account")

# 空間預約模組
from routes.space import router as spaceRoute
app.include_router(spaceRoute, prefix="/space")

# 各模組負責人在這裡加上自己的 router，例如：
# from routes.space import router as spaceRoute
# app.include_router(spaceRoute, prefix="/space")


@app.get("/")
async def home(request: Request, user=Depends(currentUser)):
    return templates.TemplateResponse(name="home.html", request=request, context={"user": user})


# 沒登入（401）→ 自動跳到登入頁；其他錯誤照常顯示
@app.exception_handler(HTTPException)
async def authRedirect(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/account/login", status_code=302)
    return await http_exception_handler(request, exc)


app.mount("/static", StaticFiles(directory="static"), name="static")
