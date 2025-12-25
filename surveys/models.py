from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Survey(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    header_image = models.ImageField(upload_to='survey_headers/', blank=True, null=True, verbose_name="Ảnh tiêu đề")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người tạo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    is_deleted = models.BooleanField(default=False, verbose_name="Đã xóa (soft delete)")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian xóa")
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="Bắt đầu vào")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Hết hạn vào")
    is_quiz = models.BooleanField(default=False, verbose_name="Chế độ Quiz (có đáp án đúng / tính điểm)")
    max_responses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Giới hạn số phản hồi",
        help_text="Để trống nếu không giới hạn số lượt làm khảo sát"
    )
    password = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Mật khẩu khảo sát",
        help_text="Để trống nếu không yêu cầu mật khẩu"
    )
    whitelist_emails = models.TextField(
        blank=True,
        default="",
        verbose_name="Danh sách email được phép",
        help_text="Nhập danh sách email (mỗi dòng một email) được phép tham gia/export"
    )
    allow_review_response = models.BooleanField(
        default=True,
        verbose_name="Cho phép xem lại câu trả lời",
        help_text="Người trả lời có thể xem lại câu trả lời của mình sau khi gửi"
    )
    send_confirmation_email = models.BooleanField(
        default=False,
        verbose_name="Gửi email xác nhận",
        help_text="Gửi email cảm ơn sau khi hoàn thành khảo sát (chỉ dùng khi tắt xem lại câu trả lời)"
    )
    one_response_only = models.BooleanField(
        default=True,
        verbose_name="Chỉ cho phép trả lời 1 lần",
        help_text="Mỗi người chỉ được trả lời khảo sát 1 lần duy nhất"
    )

    class Meta:
        verbose_name = "Khảo sát"
        verbose_name_plural = "Khảo sát"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SurveyCollaborator(models.Model):
    ROLE_OWNER = "owner"
    ROLE_EDITOR = "editor"
    ROLE_VIEWER = "viewer"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_VIEWER, "Viewer"),
    ]

    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="collaborators",
        verbose_name="Khảo sát",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="survey_roles",
        verbose_name="Người dùng",
    )
    role = models.CharField(
        max_length=16,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
        verbose_name="Vai trò",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày thêm")

    class Meta:
        verbose_name = "Phân quyền khảo sát"
        verbose_name_plural = "Phân quyền khảo sát"
        constraints = [
            models.UniqueConstraint(fields=["survey", "user"], name="uniq_survey_user_role")
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.survey.title} ({self.role})"


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Câu hỏi tự luận'),
        ('single', 'Chọn một đáp án'),  # Radio
        ('multiple', 'Chọn nhiều đáp án'),  # Checkbox
        ('section', 'Tiêu đề'),
        ('description', 'Mô tả'),
        ('image', 'Hình ảnh'),
        ('video', 'Video'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions', verbose_name="Khảo sát")
    text = models.TextField(verbose_name="Nội dung câu hỏi")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='single',
                                     verbose_name="Loại câu hỏi")
    order = models.IntegerField(default=0, verbose_name="Thứ tự")
    is_required = models.BooleanField(default=True, verbose_name="Bắt buộc")
    subtitle = models.TextField(blank=True, default="", verbose_name="Mô tả/Phụ đề")
    media_url = models.TextField(blank=True, default="", verbose_name="Media URL (ảnh/video)")

    options = models.JSONField(default=list, blank=True, null=True, verbose_name="Các lựa chọn (JSON)")
    correct_answers = models.JSONField(default=list, blank=True, null=True, verbose_name="Các đáp án đúng (JSON)")
    score = models.IntegerField(default=1, verbose_name="Điểm cho câu hỏi")

    class Meta:
        verbose_name = "Câu hỏi"
        verbose_name_plural = "Câu hỏi"
        ordering = ['order']

    def __str__(self):
        return self.text[:50]

class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses', verbose_name="Khảo sát")
    respondent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người trả lời")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian gửi")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    response_data = models.JSONField(default=dict, verbose_name="Dữ liệu trả lời")

    class Meta:
        verbose_name = "Phản hồi"
        verbose_name_plural = "Phản hồi"
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Response #{self.id} for {self.survey.title}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
