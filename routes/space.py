from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from db import getDB
from auth import chkLogin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/spaces")
def space_list(
    request: Request,
    db=Depends(getDB)
):
    chkLogin(request)

    cursor = db.cursor()
    cursor.execute("""
        SELECT id, name, location, capacity, description
        FROM spaces
        ORDER BY id
    """)

    spaces = cursor.fetchall()
    cursor.close()

    return templates.TemplateResponse(
        "space.html",
        {
            "request": request,
            "spaces": spaces
        }
    )