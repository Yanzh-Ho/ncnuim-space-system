from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from db import getDB

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# 顯示登入頁
@router.get("/login")
async def loginPage(request: Request):
	return templates.TemplateResponse(name="account/login.html", request=request,
		context={"user": None, "msg": None})


# 處理登入
@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db=Depends(getDB)):
	cur = await db.execute("SELECT * FROM users WHERE id=%s AND pwd=%s;", (username, password))
	u = await cur.fetchone()
	if u is None:
		return templates.TemplateResponse(name="account/login.html", request=request,
			context={"user": None, "msg": "帳號或密碼錯誤"}, status_code=401)
	if not u["approved"]:
		return templates.TemplateResponse(name="account/login.html", request=request,
			context={"user": None, "msg": "帳號尚未通過管理員審核"}, status_code=403)
	request.session["user"] = {"id": u["id"], "name": u["name"], "role": u["role"]}
	return RedirectResponse(url="/", status_code=303)


# 登出
@router.get("/logout")
async def logout(request: Request):
	request.session.clear()
	return RedirectResponse(url="/", status_code=302)
