from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from typing import Optional

class User(Model):
    id = fields.IntField(pk=True, index=True)
    username = fields.CharField(max_length=50, unique=True, index=True, description="用户名")
    email = fields.CharField(max_length=100, unique=True, index=True, description="邮箱")
    password_hash = fields.CharField(max_length=255, description="密码哈希")
    full_name = fields.CharField(max_length=100, null=True, blank=True, description="全名")
    phone = fields.CharField(max_length=20, null=True, blank=True, description="电话")
    role = fields.CharField(max_length=20, description="角色: member, coach, admin")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "users"
        ordering = ["-created_at"]

# 会员模型
class Member(Model):
    user = fields.OneToOneField("models.User", on_delete=fields.CASCADE, pk=True, description="关联用户")
    level = fields.CharField(max_length=20, default="Bronze", description="会员等级")
    completed_courses = fields.IntField(default=0, description="完成课程数")
    total_courses = fields.IntField(default=0, description="总课程数")
    last_active = fields.DatetimeField(null=True, blank=True, description="最后活跃时间")

    class Meta:
        table = "members"

    def update_level(self):
        """根据完成课程数更新会员等级"""
        if self.completed_courses < 5:
            self.level = "Bronze"
        elif 5 <= self.completed_courses < 15:
            self.level = "Silver"
        else:
            self.level = "Gold"

# 教练模型
class Coach(Model):
    user = fields.OneToOneField("models.User", on_delete=fields.CASCADE, pk=True, description="关联用户")
    specialization = fields.CharField(max_length=100, null=True, blank=True, description="专业领域")
    experience_years = fields.IntField(default=0, description="从业年限")
    rating = fields.FloatField(default=0.0, description="评分")

    class Meta:
        table = "coaches"

# 课程模型
class Course(Model):
    id = fields.IntField(pk=True, index=True)
    title = fields.CharField(max_length=200, description="课程标题")
    description = fields.TextField(null=True, blank=True, description="课程描述")
    coach = fields.ForeignKeyField("models.Coach", on_delete=fields.SET_NULL, null=True, description="教练")
    capacity = fields.IntField(default=20, description="课程容量")
    enrolled_count = fields.IntField(default=0, description="已报名人数")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="课程价格")
    start_date = fields.DatetimeField(description="课程开始时间")
    end_date = fields.DatetimeField(description="课程结束时间")
    is_approved = fields.BooleanField(default=False, description="是否审核通过")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "courses"
        ordering = ["-created_at"]

# 报名记录模型
class Enrollment(Model):
    id = fields.IntField(pk=True, index=True)
    member = fields.ForeignKeyField("models.Member", on_delete=fields.CASCADE, description="会员")
    course = fields.ForeignKeyField("models.Course", on_delete=fields.CASCADE, description="课程")
    status = fields.CharField(max_length=50, default="pending_payment", description="报名状态")
    enrollment_date = fields.DatetimeField(auto_now_add=True, description="报名日期")
    payment_date = fields.DatetimeField(null=True, blank=True, description="支付日期")
    completion_date = fields.DatetimeField(null=True, blank=True, description="完成日期")
    rating = fields.IntField(null=True, blank=True, description="课程评分")
    review = fields.TextField(null=True, blank=True, description="课程评价")

    class Meta:
        table = "enrollments"
        unique_together = ("member", "course")
        ordering = ["-enrollment_date"]

# Pydantic 模型用于数据验证和序列化
UserSchema = pydantic_model_creator(User, name="UserSchema")
MemberSchema = pydantic_model_creator(Member, name="MemberSchema", exclude_readonly=True)
CoachSchema = pydantic_model_creator(Coach, name="CoachSchema", exclude_readonly=True)
CourseSchema = pydantic_model_creator(Course, name="CourseSchema", exclude_readonly=True)
EnrollmentSchema = pydantic_model_creator(Enrollment, name="EnrollmentSchema", exclude_readonly=True)