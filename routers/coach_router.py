from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from tortoise.transactions import in_transaction
from datetime import datetime
from models import Coach, Course, Enrollment, Member, User
from typing import Optional

router = APIRouter(prefix="/coach", tags=["coach"])

# 模拟登录用户依赖
async def get_current_coach() -> Coach:
    """模拟获取当前登录的教练"""
    # 实际应用中应该从请求中获取用户信息并验证
    user = await User.get_or_none(username="test_coach")
    if not user:
        user = await User.create(
            username="test_coach",
            email="coach@example.com",
            password_hash="hashed_password",
            full_name="测试教练",
            role="coach"
        )
        await Coach.create(user=user, specialization="健身", experience_years=5)
    
    coach = await Coach.get(user=user)
    return coach

# 教练仪表盘
@router.get("/dashboard", response_model=dict)
async def coach_dashboard(request: Request, coach: Coach = Depends(get_current_coach)):
    """教练仪表盘"""
    # 获取教练的课程
    courses = await Course.filter(coach=coach).prefetch_related("enrollments", "enrollments__member").order_by("start_date")
    
    # 统计信息
    total_courses = len(courses)
    total_students = sum(len(course.enrollments) for course in courses)
    
    # 计算平均评分
    all_ratings = []
    for course in courses:
        for enrollment in course.enrollments:
            if enrollment.rating is not None:
                all_ratings.append(enrollment.rating)
    average_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0.0
    
    return {
        "request": request,
        "coach": coach,
        "courses": courses,
        "total_courses": total_courses,
        "total_students": total_students,
        "average_rating": round(average_rating, 1) if average_rating else 0.0
    }

# 创建课程
@router.get("/create-course")
async def create_course_form(request: Request, coach: Coach = Depends(get_current_coach)):
    """创建课程表单"""
    return {
        "request": request,
        "coach": coach
    }

@router.post("/create-course")
async def create_course(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    capacity: int = Form(...),
    price: float = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    coach: Coach = Depends(get_current_coach)
):
    """创建课程"""
    try:
        # 解析日期时间
        start_datetime = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期时间格式不正确")
    
    if start_datetime >= end_datetime:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    
    course = await Course.create(
        title=title,
        description=description,
        coach=coach,
        capacity=capacity,
        price=price,
        start_date=start_datetime,
        end_date=end_datetime,
        is_approved=False  # 默认需要管理员审核
    )
    
    return RedirectResponse(url="/coach/dashboard", status_code=303)

# 查看课程详情
@router.get("/course/{course_id}")
async def view_course(course_id: int, coach: Coach = Depends(get_current_coach)):
    """查看课程详情"""
    course = await Course.get_or_none(id=course_id, coach=coach)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或您无权访问")
    
    enrollments = await Enrollment.filter(course=course).prefetch_related("member", "member__user").order_by("enrollment_date")
    
    return {
        "course": course,
        "enrollments": enrollments
    }

# 更新课程
@router.get("/update-course/{course_id}")
async def update_course_form(course_id: int, coach: Coach = Depends(get_current_coach)):
    """更新课程表单"""
    course = await Course.get_or_none(id=course_id, coach=coach)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或您无权访问")
    
    # 格式化日期时间为ISO格式
    start_date_iso = course.start_date.strftime("%Y-%m-%dT%H:%M")
    end_date_iso = course.end_date.strftime("%Y-%m-%dT%H:%M")
    
    return {
        "course": course,
        "start_date_iso": start_date_iso,
        "end_date_iso": end_date_iso
    }

@router.post("/update-course/{course_id}")
async def update_course(
    course_id: int,
    title: str = Form(...),
    description: str = Form(...),
    capacity: int = Form(...),
    price: float = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    coach: Coach = Depends(get_current_coach)
):
    """更新课程"""
    course = await Course.get_or_none(id=course_id, coach=coach)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或您无权访问")
    
    try:
        # 解析日期时间
        start_datetime = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期时间格式不正确")
    
    if start_datetime >= end_datetime:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    
    # 更新课程信息
    course.title = title
    course.description = description
    course.capacity = capacity
    course.price = price
    course.start_date = start_datetime
    course.end_date = end_datetime
    await course.save()
    
    return RedirectResponse(url="/coach/dashboard", status_code=303)

# 删除课程
@router.post("/delete-course/{course_id}")
async def delete_course(course_id: int, coach: Coach = Depends(get_current_coach)):
    """删除课程"""
    course = await Course.get_or_none(id=course_id, coach=coach)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或您无权访问")
    
    await course.delete()
    
    return RedirectResponse(url="/coach/dashboard", status_code=303)

# 标记课程完成
@router.post("/complete-course/{course_id}")
async def complete_course(course_id: int, coach: Coach = Depends(get_current_coach)):
    """标记课程完成"""
    course = await Course.get_or_none(id=course_id, coach=coach)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或您无权访问")
    
    # 更新所有未完成的报名记录
    enrollments = await Enrollment.filter(course=course, status__in=["enrolled", "attending"])
    for enrollment in enrollments:
        enrollment.status = "completed"
        enrollment.completion_date = datetime.now()
        await enrollment.save()
    
    return RedirectResponse(url="/coach/course/{}".format(course_id), status_code=303)

# 查看学员列表
@router.get("/students/{course_id}")
async def view_students(course_id: int, coach: Coach = Depends(get_current_coach)):
    """查看学员列表"""
    course = await Course.get_or_none(id=course_id, coach=coach)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或您无权访问")
    
    enrollments = await Enrollment.filter(course=course).prefetch_related("member", "member__user").order_by("member__user__full_name")
    
    return {
        "course": course,
        "enrollments": enrollments
    }

# 获取教练统计数据
@router.get("/stats")
async def coach_stats(coach: Coach = Depends(get_current_coach)):
    """获取教练统计数据"""
    # 获取教练的所有课程
    courses = await Course.filter(coach=coach)
    
    if not courses:
        return {
            "total_courses": 0,
            "total_students": 0,
            "average_rating": 0.0,
            "revenue": 0.0
        }
    
    # 统计数据
    total_courses = len(courses)
    total_students = sum(len(await Enrollment.filter(course=course)) for course in courses)
    
    # 计算平均评分
    all_ratings = []
    for course in courses:
        enrollments = await Enrollment.filter(course=course)
        for enrollment in enrollments:
            if enrollment.rating is not None:
                all_ratings.append(enrollment.rating)
    average_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0.0
    
    # 计算总收入
    revenue = 0.0
    for course in courses:
        enrollments = await Enrollment.filter(course=course, status__in=["enrolled", "attending", "completed", "reviewed"])
        revenue += float(course.price) * len(enrollments)
    
    return {
        "total_courses": total_courses,
        "total_students": total_students,
        "average_rating": round(average_rating, 1) if average_rating else 0.0,
        "revenue": round(revenue, 2)
    }