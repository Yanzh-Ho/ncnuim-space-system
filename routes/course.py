# routes/course.py —— 模組 3：課程排課（負責人：何彥緻）
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from db import getDB
from auth import chkLogin

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# 星期幾的數字 → 中文（索引 0 不用）
WEEK = ["", "一", "二", "三", "四", "五", "六", "日"]


# 課程清單：老師只看自己的課，管理員看全部
@router.get("/")
async def courseList(request: Request, db=Depends(getDB), user=Depends(chkLogin("teacher", "admin"))):
	sql = """
		SELECT c.*, u.name AS teacher_name
		FROM courses c JOIN users u ON c.teacher = u.id
	"""
	if user["role"] == "admin":
		cur = await db.execute(sql + " ORDER BY c.weekday, c.start_time;")
	else:
		cur = await db.execute(sql + " WHERE c.teacher = %s ORDER BY c.weekday, c.start_time;", (user["id"],))
	courses = await cur.fetchall()
	return templates.TemplateResponse(name="course/list.html", request=request,
		context={"user": user, "courses": courses, "week": WEEK})
