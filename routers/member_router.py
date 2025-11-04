from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from tortoise.transactions import in_transaction
from datetime import datetime
from models import Member, Course, Enrollment, User
from typing import Optional

router = APIRouter(prefix="/member", tags=["member"])

# 模拟登录用户依赖
async def get_current_member() -> Member:
    """模拟获取当前登录的会员"""
    # 实际应用中应该从请求中获取用户信息并验证
    user = await User.get_or_none(username="test_member")
    if not user:
        user = await User.create(
            username="test_member",
            email="member@example.com",
            password_hash="hashed_password",
            full_name="测试会员",
            role="member"
        )
        await Member.create(user=user)
    
    member = await Member.get(user=user)
    return member

# 会员仪表盘
@router.get("/dashboard", response_model=dict)
async def member_dashboard(request: Request, member: Member = Depends(get_current_member)):
    """会员仪表盘"""
    # 获取已报名课程
    enrollments = await Enrollment.filter(member=member).prefetch_related("course", "course__coach")
    
    # 获取可报名课程（已审核通过且未开始的课程）
    available_courses = await Course.filter(
        is_approved=True,
        start_date__gt=datetime.now(),
        enrolled_count__lt=Course.capacity
    ).prefetch_related("coach").order_by("start_date")
    
    # 格式化报名状态
    status_map = {
        "pending_payment": "待支付",
        "enrolled": "已报名",
        "attending": "上课中",
        "completed": "已完成",
        "reviewed": "已评价"
    }
    
    return {
        "request": request,
        "member": member,
        "enrollments": enrollments,
        "available_courses": available_courses,
        "status_map": status_map
    }

# 报名课程
@router.post("/enroll/{course_id}")
async def enroll_course(course_id: int, member: Member = Depends(get_current_member)):
    """报名课程"""
    course = await Course.get_or_none(id=course_id, is_approved=True)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在或未审核通过")
    
    if course.enrolled_count >= course.capacity:
        raise HTTPException(status_code=400, detail="课程已满")
    
    # 检查是否已报名
    existing_enrollment = await Enrollment.get_or_none(member=member, course=course)
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="您已报名该课程")
    
    # 创建报名记录
    async with in_transaction():
        enrollment = await Enrollment.create(
            member=member,
            course=course,
            status="pending_payment"
        )
        course.enrolled_count += 1
        await course.save()
    
    return RedirectResponse(url="/member/dashboard", status_code=303)

# 支付课程
@router.post("/pay/{enrollment_id}")
async def pay_course(enrollment_id: int, member: Member = Depends(get_current_member)):
    """支付课程"""
    enrollment = await Enrollment.get_or_none(id=enrollment_id, member=member)
    if not enrollment:
        raise HTTPException(status_code=404, detail="报名记录不存在")
    
    if enrollment.status != "pending_payment":
        raise HTTPException(status_code=400, detail="该订单状态不允许支付")
    
    enrollment.status = "enrolled"
    enrollment.payment_date = datetime.now()
    await enrollment.save()
    
    return RedirectResponse(url="/member/dashboard", status_code=303)

# 评价课程
@router.post("/review/{enrollment_id}")
async def review_course(
    enrollment_id: int,
    rating: int,
    review: Optional[str] = None,
    member: Member = Depends(get_current_member)
):
    """评价课程"""
    enrollment = await Enrollment.get_or_none(id=enrollment_id, member=member)
    if not enrollment:
        raise HTTPException(status_code=404, detail="报名记录不存在")
    
    if enrollment.status != "completed":
        raise HTTPException(status_code=400, detail="课程未完成，无法评价")
    
    enrollment.status = "reviewed"
    enrollment.rating = rating
    enrollment.review = review
    await enrollment.save()
    
    # 更新会员完成课程数和等级
    member.completed_courses += 1
    member.total_courses += 1
    member.update_level()
    await member.save()
    
    return RedirectResponse(url="/member/dashboard", status_code=303)