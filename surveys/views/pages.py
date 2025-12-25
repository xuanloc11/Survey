from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from ..models import Survey, Response


def home(request):
    context = {
        'total_surveys': Survey.objects.filter(is_active=True, is_deleted=False).count(),
        'total_responses': Response.objects.count(),
    }
    return render(request, 'surveys/pages/home.html', context)


@login_required
def dashboard(request):
    total_surveys = Survey.objects.filter(is_deleted=False).count()
    total_responses = Response.objects.count()

    user_surveys = Survey.objects.filter(creator=request.user, is_deleted=False).annotate(
        response_count=Count('responses')
    ).order_by('-created_at')
    user_surveys_count = user_surveys.count()
    user_responses_count = Response.objects.filter(survey__creator=request.user).count()

    context = {
        'total_surveys': total_surveys,
        'total_responses': total_responses,
        'user_surveys_count': user_surveys_count,
        'user_responses_count': user_responses_count,
        'recent_user_surveys': user_surveys[:5],
    }
    return render(request, 'surveys/dashboard/dashboard.html', context)


