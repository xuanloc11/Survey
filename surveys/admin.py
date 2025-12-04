from django.contrib import admin
from .models import Survey, Question, Choice, Response, Answer

admin.site.site_header = "Hệ thống Quản lý Khảo sát"
admin.site.site_title = "Survey Manager"
admin.site.index_title = "Trang quản trị"


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'created_at', 'is_active', 'response_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]

    def response_count(self, obj):
        return obj.responses.count()
    response_count.short_description = 'Số phản hồi'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'survey', 'question_type', 'order', 'is_required']
    list_filter = ['question_type', 'is_required']
    search_fields = ['text']
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'order']
    list_filter = ['question__survey']


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['survey', 'respondent', 'submitted_at']
    list_filter = ['submitted_at', 'survey']
    readonly_fields = ['submitted_at']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['response', 'question', 'get_answer']
    list_filter = ['question__survey']

    def get_answer(self, obj):
        if obj.text_answer:
            return obj.text_answer[:50]
        elif obj.choice:
            return obj.choice.text
        return "-"
    get_answer.short_description = 'Câu trả lời'
