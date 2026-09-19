"""Jinja2 模板环境（独立成模块，供 main.py 与各 router 共用，避免循环导入）"""
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["app_name"] = "学生成绩管理系统"
