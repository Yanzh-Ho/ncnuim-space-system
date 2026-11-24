
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from datetime import date, datetime, time, timedelta

from db import getDB
from auth import chkLogin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# 空間列表
@router.get("/spaces")
async def space_list(
    request: Request,
    user=Depends(chkLogin()),
    db=Depends(getDB)
):
    async with db.cursor() as cursor:
        await cursor.execute("""
            SELECT id, name, location, capacity, description
            FROM spaces
            ORDER BY id
        """)

        spaces = await cursor.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="space.html",
        context={
            "spaces": spaces,
            "user": user
        }
    )


# 教室週行事曆
@router.get("/{space_id}/calendar")
async def space_calendar(
    space_id: int,
    request: Request,
    user=Depends(chkLogin()),
    db=Depends(getDB)
):

    # 查詢教室資料
    async with db.cursor() as cursor:
        await cursor.execute("""
            SELECT id, name, location, capacity, description
            FROM spaces
            WHERE id = %s
        """, (space_id,))

        space = await cursor.fetchone()

    if space is None:
        raise HTTPException(
            status_code=404,
            detail="找不到此空間"
        )

    # 取得目前選擇的週數
    try:
        week_offset = int(
            request.query_params.get("week_offset", 0)
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="週數參數錯誤"
        )

    # 計算該週星期一
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    monday += timedelta(weeks=week_offset)

    # 產生當週七天日期
    week_dates = [
        monday + timedelta(days=i)
        for i in range(7)
    ]

    # 計算本週開始與結束時間
    week_start = datetime.combine(monday, time.min)
    week_end = datetime.combine(
        monday + timedelta(days=7),
        time.min
    )

    # 查詢該教室當週預約紀錄
    async with db.cursor() as cursor:
        await cursor.execute("""
            SELECT
                b.id,
                b.space_id,
                b.user_id,
                u.name AS applicant,
                b.start_time,
                b.end_time,
                b.purpose,
                b.status
            FROM space_bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.space_id = %s
              AND b.start_time < %s
              AND b.end_time > %s
            ORDER BY b.start_time
        """, (
            space_id,
            week_end,
            week_start
        ))

        bookings = await cursor.fetchall()

    # 建立每小時行事曆
    calendar_rows = []

    for hour in range(8, 22):

        row = {
            "time": f"{hour:02d}:00",
            "cells": []
        }

        for day in week_dates:

            slot_start = datetime.combine(
                day,
                time(hour, 0)
            )

            slot_end = datetime.combine(
                day,
                time(hour + 1, 0)
            )

            slot_bookings = []

            for booking in bookings:

                # 只有有效申請會占用時段
                if booking["status"] not in (
                    "approved",
                    "pending"
                ):
                    continue

                if (
                    booking["start_time"] < slot_end
                    and booking["end_time"] > slot_start
                ):
                    slot_bookings.append(booking)

            row["cells"].append({
                "bookings": slot_bookings,
                "date": day.strftime("%Y-%m-%d"),
                "start_time": f"{hour:02d}:00"
            })

        calendar_rows.append(row)

    return templates.TemplateResponse(
        request=request,
        name="space_calendar.html",
        context={
            "space": space,
            "week_dates": week_dates,
            "week_offset": week_offset,
            "bookings": bookings,
            "calendar_rows": calendar_rows,
            "user": user
        }
    )
