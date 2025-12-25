from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import json

# Chỉ import những model còn tồn tại
from .models import Survey, Question, Response, UserProfile, SurveyCollaborator

# Inline để thêm câu hỏi ngay trong trang chi tiết Khảo sát
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'creator', 'created_at', 'is_active')
    search_fields = ('title',)
    # Quiz mode is disabled in this project
    exclude = ('is_quiz',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'survey', 'question_type', 'is_required')
    list_filter = ('survey', 'question_type')
    # Quiz mode is disabled in this project
    exclude = ('correct_answers', 'score')

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

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar')
    search_fields = ('user__username', 'user__email')


@admin.register(SurveyCollaborator)
class SurveyCollaboratorAdmin(admin.ModelAdmin):
    list_display = ('survey', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('survey__title', 'user__username', 'user__email')

# Custom Admin Site
from django.contrib.admin import AdminSite
from django.urls import path
from django.shortcuts import render

class CustomAdminSite(AdminSite):
    site_header = "HCMUTE Survey Administration"
    site_title = "Survey Admin"
    index_title = "Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.custom_index), name='index'),
        ]
        return custom_urls + urls
    
    def custom_index(self, request):
        context = self.each_context(request)
        
        # Get statistics
        total_surveys = Survey.objects.count()
        total_responses = Response.objects.count()
        active_surveys = Survey.objects.filter(is_active=True).count()
        inactive_surveys = Survey.objects.filter(is_active=False).count()
        total_users = User.objects.count()
        
        # Surveys per month (last 6 months)
        today = timezone.now()
        survey_months = []
        survey_counts = []
        for i in range(5, -1, -1):
            month_start = today - timedelta(days=30 * i)
            month_name = month_start.strftime('%m/%Y')
            count = Survey.objects.filter(
                created_at__year=month_start.year,
                created_at__month=month_start.month
            ).count()
            survey_months.append(month_name)
            survey_counts.append(count)
        
        # Responses per day (last 7 days)
        response_days = []
        response_counts = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_name = day.strftime('%d/%m')
            count = Response.objects.filter(
                submitted_at__date=day.date()
            ).count()
            response_days.append(day_name)
            response_counts.append(count)
        
        context.update({
            'total_surveys': total_surveys,
            'total_responses': total_responses,
            'active_surveys': active_surveys,
            'inactive_surveys': inactive_surveys,
            'total_users': total_users,
            'survey_months': json.dumps(survey_months),
            'survey_counts': json.dumps(survey_counts),
            'response_days': json.dumps(response_days),
            'response_counts': json.dumps(response_counts),
        })
        
        return render(request, 'admin/index.html', context)

# Create custom admin site instance
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register models with custom admin site
custom_admin_site.register(Survey, SurveyAdmin)
custom_admin_site.register(Question, QuestionAdmin)
custom_admin_site.register(Response, ResponseAdmin)

# Register User and Group models
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group

# Custom UserAdmin to hide password hash details
class CustomUserAdmin(UserAdmin):
    pass  # CSS will handle hiding password details

custom_admin_site.register(User, CustomUserAdmin)
custom_admin_site.register(Group, GroupAdmin)
custom_admin_site.register(UserProfile, UserProfileAdmin)