
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
        # 查詢教室
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

        # 查詢可借用物品
        await cursor.execute("""
            SELECT id, name, total_quantity
            FROM items
            WHERE available = TRUE
              AND total_quantity > 0
            ORDER BY id
        """)

        items = await cursor.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="booking_form.html",
        context={
            "space": space,
            "user": user,
            "booking_date": booking_date,
            "start_time": start_time,
            "items": items
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
    # 取得使用者勾選的物品
    form_data = await request.form()
    selected_items = form_data.getlist("item_ids")

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

    # 整理物品及數量
    booking_items = []

    for item_id_text in selected_items:
        try:
            item_id = int(item_id_text)
            quantity = int(form_data.get(f"quantity_{item_id}", "1"))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="物品編號或數量格式錯誤"
            )

        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="借用數量必須大於 0"
            )

        booking_items.append((item_id, quantity))

    if len(set(item_id for item_id, quantity in booking_items)) != len(booking_items):
        raise HTTPException(
            status_code=400,
            detail="物品不能重複選擇"
        )

    # 使用交易，確保教室預約和物品明細一起儲存
    async with db.transaction():
        async with db.cursor() as cursor:

            # 確認教室存在
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

            # 檢查教室預約時間是否衝突
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

            # 檢查物品數量
            for item_id, quantity in booking_items:

                await cursor.execute("""
                    SELECT total_quantity
                    FROM items
                    WHERE id = %s
                      AND available = TRUE
                    FOR UPDATE
                """, (item_id,))

                item = await cursor.fetchone()

                if item is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"物品編號 {item_id} 不存在或未開放借用"
                    )

                # 計算相同時段已被預約的物品數量
                await cursor.execute("""
                    SELECT COALESCE(SUM(bi.quantity), 0) AS borrowed
                    FROM booking_items bi
                    JOIN space_bookings b
                      ON bi.booking_id = b.id
                    WHERE bi.item_id = %s
                      AND b.status IN ('approved', 'pending')
                      AND b.start_time < %s
                      AND b.end_time > %s
                """, (
                    item_id,
                    end_datetime,
                    start_datetime
                ))

                borrowed = await cursor.fetchone()

                remaining = item["total_quantity"] - borrowed["borrowed"]

                if quantity > remaining:
                    raise HTTPException(
                        status_code=409,
                        detail=f"物品編號 {item_id} 數量不足，目前可借 {remaining} 件"
                    )

            # 新增教室預約
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
                RETURNING id
            """, (
                space_id,
                user["id"],
                start_datetime,
                end_datetime,
                purpose.strip()
            ))

            booking = await cursor.fetchone()
            booking_id = booking["id"]

            # 新增物品借用明細
            for item_id, quantity in booking_items:
                await cursor.execute("""
                    INSERT INTO booking_items (
                        booking_id,
                        item_id,
                        quantity
                    )
                    VALUES (%s, %s, %s)
                """, (
                    booking_id,
                    item_id,
                    quantity
                ))

    # 送出成功，返回教室週行事曆
    return RedirectResponse(
        url=f"/space/{space_id}/calendar",
        status_code=303
    )
