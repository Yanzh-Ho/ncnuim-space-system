
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from db import getDB
from auth import chkLogin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ==========================================
# 管理員查看預約（待審核＋已核准）
# ==========================================

@router.get("/bookings")
async def admin_booking_list(
    request: Request,
    user=Depends(chkLogin("admin")),
    db=Depends(getDB)
):
    async with db.cursor() as cursor:

        await cursor.execute("""
            SELECT
                b.id,
                b.space_id,
                s.name AS space_name,
                u.name AS applicant,
                b.start_time,
                b.end_time,
                b.purpose,
                b.status,
                b.created_at
            FROM space_bookings b
            JOIN spaces s ON b.space_id = s.id
            JOIN users u ON b.user_id = u.id
            WHERE b.status IN ('pending', 'approved')
            ORDER BY
                CASE
                    WHEN b.status = 'pending' THEN 1
                    WHEN b.status = 'approved' THEN 2
                END,
                b.created_at DESC
        """)

        bookings = await cursor.fetchall()

        # 查詢每筆預約的物品及借出歸還紀錄
        for booking in bookings:

            await cursor.execute("""
                SELECT
                    bi.id AS booking_item_id,
                    bi.item_id,
                    i.name AS item_name,
                    bi.quantity,
                    bi.borrowed_at,
                    bi.borrowed_by,
                    bu.name AS borrowed_admin,
                    bi.returned_at,
                    bi.returned_by,
                    ru.name AS returned_admin
                FROM booking_items bi
                JOIN items i ON bi.item_id = i.id
                LEFT JOIN users bu ON bi.borrowed_by = bu.id
                LEFT JOIN users ru ON bi.returned_by = ru.id
                WHERE bi.booking_id = %s
                ORDER BY i.id
            """, (booking["id"],))

            booking["items"] = await cursor.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="admin_booking.html",
        context={
            "bookings": bookings,
            "user": user
        }
    )


# ==========================================
# 管理員核准預約
# ==========================================

@router.post("/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: int,
    user=Depends(chkLogin("admin")),
    db=Depends(getDB)
):
    async with db.cursor() as cursor:

        await cursor.execute("""
            UPDATE space_bookings
            SET status = 'approved',
                reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP,
                review_comment = NULL
            WHERE id = %s
              AND status = 'pending'
        """, (user["id"], booking_id))

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="找不到待審核的預約"
            )

    return RedirectResponse(
        url="/admin/bookings",
        status_code=303
    )


# ==========================================
# 管理員退件預約
# ==========================================

@router.post("/bookings/{booking_id}/reject")
async def reject_booking(
    booking_id: int,
    review_comment: str = Form(...),
    user=Depends(chkLogin("admin")),
    db=Depends(getDB)
):
    if not review_comment.strip():
        raise HTTPException(
            status_code=400,
            detail="請填寫退件原因"
        )

    async with db.cursor() as cursor:

        await cursor.execute("""
            UPDATE space_bookings
            SET status = 'rejected',
                review_comment = %s,
                reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'pending'
        """, (
            review_comment.strip(),
            user["id"],
            booking_id
        ))

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="找不到待審核的預約"
            )

    return RedirectResponse(
        url="/admin/bookings",
        status_code=303
    )


# ==========================================
# 管理員確認借出
# ==========================================

@router.post("/bookings/items/{booking_item_id}/borrow")
async def borrow_item(
    booking_item_id: int,
    user=Depends(chkLogin("admin")),
    db=Depends(getDB)
):
    async with db.cursor() as cursor:

        # 確認物品所屬預約是否已核准
        await cursor.execute("""
            SELECT
                bi.id,
                bi.borrowed_at,
                bi.returned_at,
                b.status
            FROM booking_items bi
            JOIN space_bookings b
                ON bi.booking_id = b.id
            WHERE bi.id = %s
            FOR UPDATE OF bi
        """, (booking_item_id,))

        item = await cursor.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="找不到這筆借用物品"
            )

        if item["status"] != "approved":
            raise HTTPException(
                status_code=400,
                detail="只有已核准的預約才能領用物品"
            )

        if item["borrowed_at"] is not None:
            raise HTTPException(
                status_code=400,
                detail="此物品已經借出"
            )

        # 記錄借出時間及管理員
        await cursor.execute("""
            UPDATE booking_items
            SET borrowed_at = CURRENT_TIMESTAMP,
                borrowed_by = %s
            WHERE id = %s
              AND borrowed_at IS NULL
        """, (user["id"], booking_item_id))

    await db.commit()

    return RedirectResponse(
        url="/admin/bookings",
        status_code=303
    )


# ==========================================
# 管理員確認歸還
# ==========================================

@router.post("/bookings/items/{booking_item_id}/return")
async def return_item(
    booking_item_id: int,
    user=Depends(chkLogin("admin")),
    db=Depends(getDB)
):
    async with db.cursor() as cursor:

        # 確認物品目前的借用狀態
        await cursor.execute("""
            SELECT
                bi.id,
                bi.borrowed_at,
                bi.returned_at,
                b.status
            FROM booking_items bi
            JOIN space_bookings b
                ON bi.booking_id = b.id
            WHERE bi.id = %s
            FOR UPDATE OF bi
        """, (booking_item_id,))

        item = await cursor.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="找不到這筆借用物品"
            )

        if item["status"] != "approved":
            raise HTTPException(
                status_code=400,
                detail="此預約目前不能歸還"
            )

        if item["borrowed_at"] is None:
            raise HTTPException(
                status_code=400,
                detail="此物品尚未借出，不能歸還"
            )

        if item["returned_at"] is not None:
            raise HTTPException(
                status_code=400,
                detail="此物品已經歸還"
            )

        # 記錄歸還時間及管理員
        await cursor.execute("""
            UPDATE booking_items
            SET returned_at = CURRENT_TIMESTAMP,
                returned_by = %s
            WHERE id = %s
              AND borrowed_at IS NOT NULL
              AND returned_at IS NULL
        """, (user["id"], booking_item_id))

    await db.commit()

    return RedirectResponse(
        url="/admin/bookings",
        status_code=303
    )
