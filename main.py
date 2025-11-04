from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from tortoise.contrib.fastapi import register_tortoise
from routers import member_router, coach_router, admin_router
import os

# 创建FastAPI应用
app = FastAPI(title="会员课程管理系统", version="1.0.0")

# 配置模板引擎
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 配置静态文件目录
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# 注册路由
app.include_router(member_router.router)
app.include_router(coach_router.router)
app.include_router(admin_router.router)

# 配置Tortoise-ORM数据库连接
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",  # 使用SQLite数据库
    modules={"models": ["models"]},  # 模型所在模块
    generate_schemas=True,  # 自动生成数据库表
    add_exception_handlers=True,  # 添加异常处理
)

# 根路径路由
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 404错误处理
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
