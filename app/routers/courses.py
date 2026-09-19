"""课程管理：页面路由 + /api/courses CRUD。

课程列表 LEFT JOIN teachers 显示授课教师姓名；教师被删除后 teacher_id 被
外键 SET NULL 置空，模板对空值显示"未分配"。
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app import db, schemas
from app.deps import require_user_api, require_user_page
from app.templating import templates

router = APIRouter()


def _handle_db_error(exc: Exception) -> JSONResponse:
    code, detail = db.db_error_to_detail(exc)
    return JSONResponse({"detail": detail}, status_code=code)


@router.get("/courses")
def courses_page(request: Request, search: str = "", page: int = 1,
                 user=Depends(require_user_page)):
    return templates.TemplateResponse(request, "courses.html", {
        "user": user, "search": search, **db.list_courses(search, page, size=8),
        "teacher_options": db.teacher_options(),
    })


@router.get("/api/courses")
def api_list_courses(search: str = "", page: int = 1, size: int = 10,
                     user=Depends(require_user_api)):
    return db.list_courses(search, page, size)


@router.get("/api/courses/options")
def api_course_options(user=Depends(require_user_api)):
    return db.course_options()


@router.post("/api/courses", status_code=201)
def api_create_course(payload: schemas.CourseIn, user=Depends(require_user_api)):
    try:
        new_id = db.create_course(payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    return {"course_id": new_id}


@router.put("/api/courses/{course_id}")
def api_update_course(course_id: int, payload: schemas.CourseIn,
                      user=Depends(require_user_api)):
    if db.get_course(course_id) is None:
        return JSONResponse({"detail": "课程不存在"}, status_code=404)
    try:
        db.update_course(course_id, payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    return {"ok": True}


@router.delete("/api/courses/{course_id}")
def api_delete_course(course_id: int, user=Depends(require_user_api)):
    if not db.delete_course(course_id):
        return JSONResponse({"detail": "课程不存在"}, status_code=404)
    return {"ok": True}
