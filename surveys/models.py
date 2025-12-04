from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Survey(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người tạo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Hết hạn vào")

    class Meta:
        verbose_name = "Khảo sát"
        verbose_name_plural = "Khảo sát"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Câu hỏi tự luận'),
        ('single', 'Chọn một đáp án'),
        ('multiple', 'Chọn nhiều đáp án'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions', verbose_name="Khảo sát")
    text = models.TextField(verbose_name="Nội dung câu hỏi")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='single', verbose_name="Loại câu hỏi")
    order = models.IntegerField(default=0, verbose_name="Thứ tự")
    is_required = models.BooleanField(default=True, verbose_name="Bắt buộc")

    class Meta:
        verbose_name = "Câu hỏi"
        verbose_name_plural = "Câu hỏi"
        ordering = ['order']

    def __str__(self):
        return self.text[:50]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name="Câu hỏi")
    text = models.CharField(max_length=200, verbose_name="Nội dung lựa chọn")
    order = models.IntegerField(default=0, verbose_name="Thứ tự")

    class Meta:
        verbose_name = "Lựa chọn"
        verbose_name_plural = "Lựa chọn"
        ordering = ['order']

    def __str__(self):
        return self.text


class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses', verbose_name="Khảo sát")
    respondent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người trả lời")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian gửi")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Phản hồi"
        verbose_name_plural = "Phản hồi"
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Response to {self.survey.title}"


class Answer(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='answers', verbose_name="Phản hồi")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Câu hỏi")
    text_answer = models.TextField(blank=True, null=True, verbose_name="Câu trả lời dạng text")
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Lựa chọn")

    class Meta:
        verbose_name = "Câu trả lời"
        verbose_name_plural = "Câu trả lời"

    def __str__(self):
        if self.text_answer:
            return self.text_answer[:50]
        elif self.choice:
            return self.choice.text
        return "No answer"
