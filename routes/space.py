import os
import shutil
from fastapi import APIRouter, Depends, Request, Form, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from db import getDB
from auth import currentUser, chkLogin

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# 確保存放 360 全景照片的資料夾存在
PANO_DIR = "static/pano"
os.makedirs(PANO_DIR, exist_ok=True)


# 1. 空間查詢首頁（公開：不須登入即可瀏覽列表與平面圖標記）
@router.get("/")
async def spaceList(request: Request, floor: str = "", db=Depends(getDB), user=Depends(currentUser)):
	if floor:
		cur = await db.execute("SELECT * FROM rooms WHERE floor=%s ORDER BY room_code;", (floor,))
	else:
		cur = await db.execute("SELECT * FROM rooms ORDER BY floor, room_code;")
	rooms = await cur.fetchall()
	return templates.TemplateResponse(name="space/list.html", request=request,
		context={"user": user, "rooms": rooms, "current_floor": floor})


# 2. 管理員：新增教室頁面
@router.get("/create")
async def createRoomPage(request: Request, user=Depends(chkLogin("admin"))):
	return templates.TemplateResponse(name="space/form.html", request=request,
		context={"user": user, "room": None, "msg": None})


# 3. 管理員：處理新增教室（含上傳 360 全景圖）
@router.post("/create")
async def createRoom(
	request: Request,
	room_code: str = Form(...),
	room_name: str = Form(...),
	floor: str = Form(...),
	capacity: int = Form(0),
	equipment: str = Form(""),
	description: str = Form(""),
	pano_url: str = Form(""),
	map_x: float = Form(50.0),
	map_y: float = Form(50.0),
	pano_file: UploadFile = File(None),
	db=Depends(getDB),
	user=Depends(chkLogin("admin"))
):
	# 檢查教室編號是否重複
	cur = await db.execute("SELECT id FROM rooms WHERE room_code=%s;", (room_code,))
	if await cur.fetchone():
		return templates.TemplateResponse(name="space/form.html", request=request,
			context={"user": user, "room": None, "msg": f"教室編號 {room_code} 已存在"}, status_code=400)

	# 若有上傳本地 360 照片，儲存至 static/pano/
	final_pano = pano_url
	if pano_file and pano_file.filename:
		ext = os.path.splitext(pano_file.filename)[1]
		filename = f"{room_code}{ext}"
		filepath = os.path.join(PANO_DIR, filename)
		with open(filepath, "wb") as buffer:
			shutil.copyfileobj(pano_file.file, buffer)
		final_pano = f"/static/pano/{filename}"

	await db.execute(
		"""INSERT INTO rooms (room_code, room_name, floor, capacity, equipment, description, pano_url, map_x, map_y)
		   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
		(room_code, room_name, floor, capacity, equipment, description, final_pano, map_x, map_y)
	)
	return RedirectResponse(url="/space/", status_code=303)


# 4. 單一教室詳細資訊與 360 全景瀏覽（公開）
@router.get("/{room_id}")
async def roomDetail(request: Request, room_id: int, db=Depends(getDB), user=Depends(currentUser)):
	cur = await db.execute("SELECT * FROM rooms WHERE id=%s;", (room_id,))
	room = await cur.fetchone()
	if room is None:
		return RedirectResponse(url="/space/", status_code=302)
	return templates.TemplateResponse(name="space/detail.html", request=request,
		context={"user": user, "room": room})


# 5. 管理員：編輯教室頁面
@router.get("/{room_id}/edit")
async def editRoomPage(request: Request, room_id: int, db=Depends(getDB), user=Depends(chkLogin("admin"))):
	cur = await db.execute("SELECT * FROM rooms WHERE id=%s;", (room_id,))
	room = await cur.fetchone()
	if room is None:
		return RedirectResponse(url="/space/", status_code=302)
	return templates.TemplateResponse(name="space/form.html", request=request,
		context={"user": user, "room": room, "msg": None})


# 6. 管理員：處理編輯教室
@router.post("/{room_id}/edit")
async def editRoom(
	request: Request,
	room_id: int,
	room_code: str = Form(...),
	room_name: str = Form(...),
	floor: str = Form(...),
	capacity: int = Form(0),
	equipment: str = Form(""),
	description: str = Form(""),
	pano_url: str = Form(""),
	map_x: float = Form(50.0),
	map_y: float = Form(50.0),
	pano_file: UploadFile = File(None),
	db=Depends(getDB),
	user=Depends(chkLogin("admin"))
):
	final_pano = pano_url
	if pano_file and pano_file.filename:
		ext = os.path.splitext(pano_file.filename)[1]
		filename = f"{room_code}{ext}"
		filepath = os.path.join(PANO_DIR, filename)
		with open(filepath, "wb") as buffer:
			shutil.copyfileobj(pano_file.file, buffer)
		final_pano = f"/static/pano/{filename}"

	await db.execute(
		"""UPDATE rooms SET room_code=%s, room_name=%s, floor=%s, capacity=%s,
		   equipment=%s, description=%s, pano_url=%s, map_x=%s, map_y=%s
		   WHERE id=%s;""",
		(room_code, room_name, floor, capacity, equipment, description, final_pano, map_x, map_y, room_id)
	)
	return RedirectResponse(url=f"/space/{room_id}", status_code=303)


# 7. 管理員：刪除教室
@router.post("/{room_id}/delete")
async def deleteRoom(room_id: int, db=Depends(getDB), user=Depends(chkLogin("admin"))):
	await db.execute("DELETE FROM rooms WHERE id=%s;", (room_id,))
	return RedirectResponse(url="/space/", status_code=303)