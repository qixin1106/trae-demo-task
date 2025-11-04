from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from tortoise.transactions import in_transaction
from datetime import datetime
from models import User, Member, Coach, Course, Enrollment
from typing import Optional, List

router = APIRouter(prefix="/admin", tags=["admin"])

# 模拟登录用户依赖
async def get_current_admin() -> User:
    """模拟获取当前登录的管理员"""
    # 实际应用中应该从请求中获取用户信息并验证
    user = await User.get_or_none(username="admin")
    if not user:
        user = await User.create(
            username="admin",
            email="admin@example.com",
            password_hash="admin_password",
            full_name="管理员",
            role="admin"
        )
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="您没有管理员权限")
    
    return user

# 管理员仪表盘
@router.get("/dashboard", response_model=dict)
async def admin_dashboard(request: Request, admin: User = Depends(get_current_admin)):
    """管理员仪表盘"""
    # 获取系统统计数据
    total_users = await User.all().count()
    total_members = await Member.all().count()
    total_coaches = await Coach.all().count()
    total_courses = await Course.all().count()
    total_enrollments = await Enrollment.all().count()
    
    # 获取待审核课程数量
    pending_courses = await Course.filter(is_approved=False).count()
    
    # 获取最近注册的用户
    recent_users = await User.all().order_by("-created_at").limit(10).prefetch_related("member", "coach")
    
    # 获取最近创建的课程
    recent_courses = await Course.all().order_by("-created_at").limit(10).prefetch_related("coach")
    
    return {
        "request": request,
        "admin": admin,
        "total_users": total_users,
        "total_members": total_members,
        "total_coaches": total_coaches,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "pending_courses": pending_courses,
        "recent_users": recent_users,
        "recent_courses": recent_courses
    }

# 用户管理
@router.get("/users", response_model=dict)
async def list_users(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    role: Optional[str] = None,
    admin: User = Depends(get_current_admin)
):
    """列出所有用户"""
    offset = (page - 1) * per_page
    query = User.all().order_by("-created_at").prefetch_related("member", "coach")
    
    if role:
        query = query.filter(role=role)
    
    users = await query.offset(offset).limit(per_page)
    total_users = await query.count()
    total_pages = (total_users + per_page - 1) // per_page
    
    return {
        "request": request,
        "users": users,
        "page": page,
        "per_page": per_page,
        "total_users": total_users,
        "total_pages": total_pages,
        "role_filter": role
    }

# 查看用户详情
@router.get("/users/{user_id}", response_model=dict)
async def view_user(user_id: int, admin: User = Depends(get_current_admin)):
    """查看用户详情"""
    user = await User.get_or_none(id=user_id).prefetch_related("member", "coach")
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户相关数据
    if user.role == "member" and user.member:
        enrollments = await Enrollment.filter(member=user.member).prefetch_related("course").order_by("-enrollment_date")
        return {
            "user": user,
            "member": user.member,
            "enrollments": enrollments
        }
    elif user.role == "coach" and user.coach:
        courses = await Course.filter(coach=user.coach).prefetch_related("enrollments").order_by("-created_at")
        return {
            "user": user,
            "coach": user.coach,
            "courses": courses
        }
    else:
        return {"user": user}

# 禁用/启用用户
@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: int, admin: User = Depends(get_current_admin)):
    """禁用/启用用户"""
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 实际应用中应该添加is_active字段
    # user.is_active = not user.is_active
    # await user.save()
    
    return RedirectResponse(url="/admin/users", status_code=303)

# 课程管理
@router.get("/courses", response_model=dict)
async def list_courses(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    is_approved: Optional[bool] = None,
    admin: User = Depends(get_current_admin)
):
    """列出所有课程"""
    offset = (page - 1) * per_page
    query = Course.all().order_by("-created_at").prefetch_related("coach")
    
    if is_approved is not None:
        query = query.filter(is_approved=is_approved)
    
    courses = await query.offset(offset).limit(per_page)
    total_courses = await query.count()
    total_pages = (total_courses + per_page - 1) // per_page
    
    return {
        "request": request,
        "courses": courses,
        "page": page,
        "per_page": per_page,
        "total_courses": total_courses,
        "total_pages": total_pages,
        "is_approved_filter": is_approved
    }

# 查看课程详情
@router.get("/courses/{course_id}", response_model=dict)
async def view_course(course_id: int, admin: User = Depends(get_current_admin)):
    """查看课程详情"""
    course = await Course.get_or_none(id=course_id).prefetch_related("coach", "enrollments", "enrollments__member")
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    return {
        "course": course,
        "enrollments": course.enrollments
    }

# 审核课程
@router.post("/courses/{course_id}/approve")
async def approve_course(course_id: int, admin: User = Depends(get_current_admin)):
    """审核通过课程"""
    course = await Course.get_or_none(id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    course.is_approved = True
    await course.save()
    
    return RedirectResponse(url="/admin/courses", status_code=303)

# 拒绝课程
@router.post("/courses/{course_id}/reject")
async def reject_course(course_id: int, admin: User = Depends(get_current_admin)):
    """拒绝课程"""
    course = await Course.get_or_none(id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    course.is_approved = False
    await course.save()
    
    return RedirectResponse(url="/admin/courses", status_code=303)

# 删除课程
@router.post("/courses/{course_id}/delete")
async def delete_course(course_id: int, admin: User = Depends(get_current_admin)):
    """删除课程"""
    course = await Course.get_or_none(id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    await course.delete()
    
    return RedirectResponse(url="/admin/courses", status_code=303)

# 会员管理
@router.get("/members", response_model=dict)
async def list_members(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    level: Optional[str] = None,
    admin: User = Depends(get_current_admin)
):
    """列出所有会员"""
    offset = (page - 1) * per_page
    query = Member.all().order_by("-user__created_at").prefetch_related("user")
    
    if level:
        query = query.filter(level=level)
    
    members = await query.offset(offset).limit(per_page)
    total_members = await query.count()
    total_pages = (total_members + per_page - 1) // per_page
    
    return {
        "request": request,
        "members": members,
        "page": page,
        "per_page": per_page,
        "total_members": total_members,
        "total_pages": total_pages,
        "level_filter": level
    }

# 更新会员等级
@router.post("/members/{member_id}/update-level")
async def update_member_level(
    member_id: int,
    level: str = Form(...),
    admin: User = Depends(get_current_admin)
):
    """更新会员等级"""
    member = await Member.get_or_none(id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    
    valid_levels = ["Bronze", "Silver", "Gold"]
    if level not in valid_levels:
        raise HTTPException(status_code=400, detail="无效的会员等级")
    
    member.level = level
    await member.save()
    
    return RedirectResponse(url="/admin/members", status_code=303)

# 系统统计
@router.get("/system-stats", response_model=dict)
async def system_stats(admin: User = Depends(get_current_admin)):
    """获取系统统计数据"""
    # 用户统计
    total_users = await User.all().count()
    total_members = await Member.all().count()
    total_coaches = await Coach.all().count()
    
    # 课程统计
    total_courses = await Course.all().count()
    approved_courses = await Course.filter(is_approved=True).count()
    pending_courses = await Course.filter(is_approved=False).count()
    
    # 报名统计
    total_enrollments = await Enrollment.all().count()
    pending_payments = await Enrollment.filter(status="pending_payment").count()
    enrolled = await Enrollment.filter(status="enrolled").count()
    completed = await Enrollment.filter(status="completed").count()
    reviewed = await Enrollment.filter(status="reviewed").count()
    
    # 收入统计
    revenue = 0.0
    paid_enrollments = await Enrollment.filter(status__in=["enrolled", "completed", "reviewed"]).prefetch_related("course")
    for enrollment in paid_enrollments:
        revenue += float(enrollment.course.price)
    
    # 会员等级统计
    bronze_members = await Member.filter(level="Bronze").count()
    silver_members = await Member.filter(level="Silver").count()
    gold_members = await Member.filter(level="Gold").count()
    
    return {
        "total_users": total_users,
        "total_members": total_members,
        "total_coaches": total_coaches,
        "total_courses": total_courses,
        "approved_courses": approved_courses,
        "pending_courses": pending_courses,
        "total_enrollments": total_enrollments,
        "pending_payments": pending_payments,
        "enrolled": enrolled,
        "completed": completed,
        "reviewed": reviewed,
        "revenue": round(revenue, 2),
        "member_levels": {
            "Bronze": bronze_members,
            "Silver": silver_members,
            "Gold": gold_members
        }
    }

# 查看系统日志
@router.get("/logs", response_model=dict)
async def view_logs(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    admin: User = Depends(get_current_admin)
):
    """查看系统日志"""
    # 实际应用中应该实现日志系统
    logs = []
    total_logs = 0
    total_pages = 0
    
    return {
        "request": request,
        "logs": logs,
        "page": page,
        "per_page": per_page,
        "total_logs": total_logs,
        "total_pages": total_pages
    }