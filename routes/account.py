from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from db import getDB
from auth import chkLogin

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


# 顯示註冊頁
@router.get("/register")
async def registerPage(request: Request):
	return templates.TemplateResponse(name="account/register.html", request=request,
		context={"user": None, "msg": None})


# 處理註冊：存進資料庫，approved = false，要等管理員審核
@router.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...),
                   name: str = Form(...), role: str = Form(...), db=Depends(getDB)):
	if role not in ("teacher", "student"):
		return templates.TemplateResponse(name="account/register.html", request=request,
			context={"user": None, "msg": "身分錯誤"}, status_code=400)
	cur = await db.execute("SELECT id FROM users WHERE id=%s;", (username,))
	if await cur.fetchone():
		return templates.TemplateResponse(name="account/register.html", request=request,
			context={"user": None, "msg": "帳號已被使用"}, status_code=400)
	await db.execute("INSERT INTO users (id, pwd, name, role, approved) VALUES (%s, %s, %s, %s, false);",
		(username, password, name, role))
	return templates.TemplateResponse(name="account/login.html", request=request,
		context={"user": None, "msg": "註冊成功，請等待管理員審核"})


# 管理員：帳號審核清單
@router.get("/admin")
async def userList(request: Request, db=Depends(getDB), user=Depends(chkLogin("admin"))):
	cur = await db.execute("SELECT * FROM users ORDER BY approved, role, id;")
	users = await cur.fetchall()
	return templates.TemplateResponse(name="account/admin.html", request=request,
		context={"user": user, "users": users})


# 管理員：通過
@router.post("/admin/approve/{uid}")
async def approve(uid: str, db=Depends(getDB), user=Depends(chkLogin("admin"))):
	await db.execute("UPDATE users SET approved=true WHERE id=%s;", (uid,))
	return RedirectResponse(url="/account/admin", status_code=303)


# 管理員：拒絕（刪除還沒通過的帳號）
@router.post("/admin/reject/{uid}")
async def reject(uid: str, db=Depends(getDB), user=Depends(chkLogin("admin"))):
	await db.execute("DELETE FROM users WHERE id=%s AND approved=false;", (uid,))
	return RedirectResponse(url="/account/admin", status_code=303)
