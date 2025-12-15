from django.contrib import admin
from django.utils.html import format_html
import json

# Chỉ import những model còn tồn tại
from .models import Survey, Question, Response

# Inline để thêm câu hỏi ngay trong trang chi tiết Khảo sát
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'creator', 'created_at', 'is_active')
    search_fields = ('title',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'survey', 'question_type', 'is_required')
    list_filter = ('survey', 'question_type')

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'survey', 'respondent', 'submitted_at')
    readonly_fields = ('response_data_pretty',) # Chỉ đọc field này

    # Hàm giúp hiển thị JSON đẹp trong admin
    def response_data_pretty(self, instance):
        if not instance.response_data:
            return "{}"
        # Format JSON thành chuỗi có thụt đầu dòng, hiển thị tiếng Việt đúng
        response_formatted = json.dumps(instance.response_data, ensure_ascii=False, indent=4)
        return format_html('<pre>{}</pre>', response_formatted)

    response_data_pretty.short_description = "Dữ liệu trả lời (Chi tiết)"