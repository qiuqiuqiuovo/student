"""pydantic 请求模型：应用层校验（双重校验的第一层）。

前端表单已带 HTML/JS 前置校验，这里负责兜底——非法数据根本到不了 SQL 层，
FastAPI 自动返回 422 及字段级错误明细。
"""
from datetime import date

from pydantic import BaseModel, Field


class StudentIn(BaseModel):
    student_no: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    gender: str = Field(default="男", pattern="^(男|女)$")
    birth_date: date | None = None
    major: str | None = Field(default=None, max_length=50)
    class_name: str | None = Field(default=None, max_length=50)
    enrollment_date: date | None = None


class TeacherIn(BaseModel):
    teacher_no: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    gender: str = Field(default="男", pattern="^(男|女)$")
    title: str | None = Field(default=None, max_length=30)
    department: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class CourseIn(BaseModel):
    course_no: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=100)
    credits: float = Field(ge=0.5, le=99.9)
    teacher_id: int | None = None
    semester: str | None = Field(default=None, max_length=20)


class GradeIn(BaseModel):
    """成绩录入请求：score 的范围校验是第一层防线（第二层是 DB 触发器 + CHECK）"""

    student_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    score: float = Field(ge=0, le=100)
    exam_date: date


class GradeUpdateIn(BaseModel):
    score: float = Field(ge=0, le=100)
    exam_date: date


class GradeBatchRow(BaseModel):
    student_no: str
    course_no: str
    score: float = Field(ge=0, le=100)
    exam_date: date


class GradeBatchIn(BaseModel):
    """批量导入：每行调用存储过程 sp_insert_grade，单事务，一行失败全部回滚"""

    rows: list[GradeBatchRow] = Field(min_length=1, max_length=200)


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    nickname: str | None = Field(default=None, max_length=32)
