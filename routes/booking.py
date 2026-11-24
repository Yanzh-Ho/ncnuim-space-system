
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime

from db import getDB
from auth import chkLogin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# 預約申請頁面
@router.get("/{space_id}/new")
async def booking_form(
    space_id: int,
    request: Request,
    user=Depends(chkLogin()),
    db=Depends(getDB)
):

    booking_date = request.query_params.get("date")
    start_time = request.query_params.get("start_time")

    async with db.cursor() as cursor:
        await cursor.execute("""
            SELECT id, name, location, capacity
            FROM spaces
            WHERE id = %s
        """, (space_id,))

        space = await cursor.fetchone()

    if space is None:
        raise HTTPException(
            status_code=404,
            detail="找不到此教室"
        )

    return templates.TemplateResponse(
        request=request,
        name="booking_form.html",
        context={
            "space": space,
            "user": user,
            "booking_date": booking_date,
            "start_time": start_time
        }
    )


# 送出預約申請
@router.post("/{space_id}/create")
async def create_booking(
    space_id: int,
    request: Request,
    booking_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    purpose: str = Form(...),
    user=Depends(chkLogin()),
    db=Depends(getDB)
):

    # 檢查日期與時間格式
    try:
        start_datetime = datetime.strptime(
            f"{booking_date} {start_time}",
            "%Y-%m-%d %H:%M"
        )

        end_datetime = datetime.strptime(
            f"{booking_date} {end_time}",
            "%Y-%m-%d %H:%M"
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="日期或時間格式錯誤"
        )

    if end_datetime <= start_datetime:
        raise HTTPException(
            status_code=400,
            detail="結束時間必須晚於開始時間"
        )

    if not purpose.strip():
        raise HTTPException(
            status_code=400,
            detail="請填寫預約用途"
        )

    if start_datetime.date() < datetime.today().date():
        raise HTTPException(
            status_code=400,
            detail="不能預約過去的日期"
        )

    # 確認教室存在
    async with db.cursor() as cursor:
        await cursor.execute("""
            SELECT id
            FROM spaces
            WHERE id = %s
        """, (space_id,))

        space = await cursor.fetchone()

        if space is None:
            raise HTTPException(
                status_code=404,
                detail="找不到此教室"
            )

        # 檢查時間是否與其他有效預約衝突
        await cursor.execute("""
            SELECT id
            FROM space_bookings
            WHERE space_id = %s
              AND status IN ('approved', 'pending')
              AND start_time < %s
              AND end_time > %s
            LIMIT 1
        """, (
            space_id,
            end_datetime,
            start_datetime
        ))

        conflict = await cursor.fetchone()

        if conflict:
            raise HTTPException(
                status_code=409,
                detail="此時段已有人預約，請選擇其他時間"
            )

        # 新增預約資料
        await cursor.execute("""
            INSERT INTO space_bookings (
                space_id,
                user_id,
                start_time,
                end_time,
                purpose,
                status
            )
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (
            space_id,
            user["id"],
            start_datetime,
            end_datetime,
            purpose.strip()
        ))

    # 送出成功，返回該教室週行事曆
    return RedirectResponse(
        url=f"/space/{space_id}/calendar",
        status_code=303
    )
