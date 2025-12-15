from django import template
from django.contrib.auth.models import User
from django.db.models import Count, Q
from surveys.models import Survey, Question, Response

register = template.Library()


@register.simple_tag
def get_admin_stats():
    """Lấy thống kê cho admin dashboard"""
    surveys = Survey.objects.all()
    
    # Thống kê chi tiết cho từng khảo sát
    survey_stats = []
    for survey in surveys:
        # Tính tổng số câu trả lời từ response_data JSONField
        total_answers = 0
        for response in survey.responses.all():
            if response.response_data:
                total_answers += len(response.response_data)
        
        survey_stats.append({
            'survey': survey,
            'total_questions': survey.questions.count(),
            'total_responses': survey.responses.count(),
            'total_answers': total_answers,
            'is_active': survey.is_active,
            'created_at': survey.created_at,
            'creator': survey.creator,
        })
    
    return {
        'total_surveys': Survey.objects.count(),
        'total_responses': Response.objects.count(),
        'total_questions': Question.objects.count(),
        'total_users': User.objects.count(),
        'survey_stats': survey_stats,
        'recent_surveys': Survey.objects.select_related('creator').order_by('-created_at')[:10],
        'recent_responses': Response.objects.select_related('survey', 'respondent').order_by('-submitted_at')[:10],
    }

