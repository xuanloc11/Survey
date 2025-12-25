from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.urls import reverse
from django.core import signing

from ..models import Survey
from ..forms import SurveyForm


@login_required
def survey_list(request):
    surveys = Survey.objects.filter(creator=request.user, is_deleted=False).annotate(
        response_count=Count('responses')
    ).order_by('-created_at')

    context = {
        'surveys': surveys,
    }
    return render(request, 'surveys/survey_management/survey_list.html', context)


@login_required
def survey_create(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST, request.FILES)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.creator = request.user
            survey.is_quiz = False
            raw_password = form.cleaned_data.get('password')
            if raw_password:
                survey.password = make_password(raw_password)
            survey.is_active = False
            survey.save()
            messages.success(request, 'Đã tạo khảo sát ở trạng thái nháp. Hãy xuất bản khi sẵn sàng!')
            return redirect('surveys:survey_detail', pk=survey.pk)
    else:
        form = SurveyForm(initial={'is_active': False})

    return render(request, 'surveys/survey_management/survey_form.html', {
        'form': form,
        'title': 'Tạo khảo sát mới'
    })


@login_required
def survey_edit(request, pk):
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)

    if request.method == 'POST':
        form = SurveyForm(request.POST, request.FILES, instance=survey)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.is_quiz = False
            raw_password = form.cleaned_data.get('password')
            if raw_password:
                survey.password = make_password(raw_password)
            survey.save()
            messages.success(request, 'Đã cập nhật khảo sát thành công!')
            return redirect('surveys:survey_detail', pk=survey.pk)
    else:
        form = SurveyForm(instance=survey)

    return render(request, 'surveys/survey_management/survey_form.html', {
        'form': form,
        'survey': survey,
        'title': 'Chỉnh sửa khảo sát'
    })


def survey_detail(request, pk):
    """Chi tiết khảo sát"""
    survey = get_object_or_404(Survey, pk=pk)
    questions = survey.questions.all().order_by('order')

    is_expired = survey.expires_at and survey.expires_at < timezone.now()
    responses_count = survey.responses.count()
    max_responses = survey.max_responses
    is_limit_reached = bool(max_responses) and responses_count >= max_responses
    remaining_slots = max_responses - responses_count if max_responses else None

    can_edit = request.user.is_authenticated and request.user == survey.creator
    template_name = 'surveys/survey_management/survey_builder.html' if can_edit else 'surveys/survey_management/survey_detail.html'

    context = {
        'survey': survey,
        'questions': questions,
        'is_expired': is_expired,
        'is_limit_reached': is_limit_reached,
        'remaining_slots': remaining_slots,
        'can_edit': can_edit,
        'builder_mode': can_edit,
        'share_link': request.build_absolute_uri(
            reverse('surveys:survey_take_token', args=[signing.dumps(survey.pk, salt="survey-share")])
        ),
    }

    if can_edit:
        responses = survey.responses.all()
        total_responses_count = responses.count()

        stats = []
        for question in questions:
            question_id_str = str(question.id)

            if question.question_type not in ['text', 'single', 'multiple']:
                continue

            if question.question_type == 'text':
                text_answers = []
                for response in responses:
                    if response.response_data and question_id_str in response.response_data:
                        answer_value = response.response_data[question_id_str]
                        if isinstance(answer_value, str) and answer_value.strip():
                            text_answers.append(answer_value)

                stats.append({
                    'question': question,
                    'type': 'text',
                    'answers': text_answers[:10],
                    'total': len(text_answers)
                })
            else:
                choice_stats = []
                if question.options:
                    for idx, option_text in enumerate(question.options):
                        count = 0
                        for response in responses:
                            if response.response_data and question_id_str in response.response_data:
                                answer_value = response.response_data[question_id_str]
                                if question.question_type == 'single':
                                    if answer_value == option_text:
                                        count += 1
                                elif question.question_type == 'multiple':
                                    if isinstance(answer_value, list) and option_text in answer_value:
                                        count += 1

                        percentage = (count / total_responses_count * 100) if total_responses_count > 0 else 0
                        choice_stats.append({
                            'option': option_text,
                            'index': idx,
                            'count': count,
                            'percentage': round(percentage, 1)
                        })

                stats.append({
                    'question': question,
                    'type': question.question_type,
                    'choices': choice_stats,
                    'total': total_responses_count
                })

        context['stats'] = stats
        context['total_responses'] = total_responses_count
        context['responses'] = responses

    return render(request, template_name, context)


@login_required
def survey_delete(request, pk):
    survey = get_object_or_404(Survey, pk=pk, creator=request.user, is_deleted=False)

    if request.method == 'POST':
        survey.is_deleted = True
        survey.is_active = False
        survey.deleted_at = timezone.now()
        survey.save(update_fields=['is_deleted', 'is_active', 'deleted_at'])
        messages.success(request, 'Đã xóa khảo sát. Khảo sát sẽ ngừng nhận phản hồi.')
        return redirect('surveys:survey_list')

    return render(request, 'surveys/survey_management/survey_confirm_delete.html', {
        'survey': survey
    })


