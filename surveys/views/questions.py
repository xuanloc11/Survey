from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..models import Survey, Question
from ..forms import QuestionForm
from ..permissions import get_survey_access
from ..tokens import make_survey_token


@login_required
def question_add(request, survey_pk):
    survey = get_object_or_404(Survey, pk=survey_pk, is_deleted=False)
    access = get_survey_access(request.user, survey)
    if not access.can_edit:
        messages.error(request, 'Bạn không có quyền thêm câu hỏi cho khảo sát này!')
        return redirect('surveys:survey_detail', pk=survey.pk)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.survey = survey
            question.save()

            if question.question_type in ['single', 'multiple']:
                return redirect('surveys:choice_add', question_pk=question.pk)
            else:
                messages.success(request, 'Đã thêm câu hỏi thành công!')
                return redirect('surveys:survey_detail_token', token=make_survey_token(survey.pk))
    else:
        form = QuestionForm()

    return render(request, 'surveys/question/question_form.html', {
        'form': form,
        'survey': survey,
        'title': 'Thêm câu hỏi'
    })


@login_required
def question_edit(request, pk):
    """Chỉnh sửa câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    survey = question.survey

    access = get_survey_access(request.user, survey)
    if not access.can_edit:
        messages.error(request, 'Bạn không có quyền chỉnh sửa câu hỏi này!')
        return redirect('surveys:survey_detail_token', token=make_survey_token(survey.pk))

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật câu hỏi thành công!')
            return redirect('surveys:survey_detail_token', token=make_survey_token(survey.pk))
    else:
        form = QuestionForm(instance=question)

    return render(request, 'surveys/question/question_form.html', {
        'form': form,
        'survey': survey,
        'question': question,
        'title': 'Chỉnh sửa câu hỏi'
    })


@login_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    survey = question.survey

    access = get_survey_access(request.user, survey)
    if not access.can_edit:
        messages.error(request, 'Bạn không có quyền xóa câu hỏi này!')
        return redirect('surveys:survey_detail_token', token=make_survey_token(survey.pk))

    if request.method == 'POST':
        survey_pk = survey.pk
        question.delete()
        messages.success(request, 'Đã xóa câu hỏi thành công!')
        return redirect('surveys:survey_detail_token', token=make_survey_token(survey_pk))

    return render(request, 'surveys/question/question_confirm_delete.html', {
        'question': question,
        'survey': survey
    })


@login_required
def choice_add(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    survey = question.survey

    access = get_survey_access(request.user, survey)
    if not access.can_edit:
        messages.error(request, 'Bạn không có quyền thêm lựa chọn!')
        return redirect('surveys:survey_detail_token', token=make_survey_token(survey.pk))

    if request.method == 'POST':
        option_text = request.POST.get('text', '').strip()
        if option_text:
            if question.options is None:
                question.options = []
            question.options.append(option_text)
            question.save()

            if 'add_another' in request.POST:
                messages.success(request, 'Đã thêm lựa chọn! Tiếp tục thêm...')
                return redirect('surveys:choice_add', question_pk=question.pk)
            else:
                messages.success(request, 'Đã thêm lựa chọn thành công!')
                return redirect('surveys:survey_detail_token', token=make_survey_token(survey.pk))
        else:
            messages.error(request, 'Vui lòng nhập nội dung lựa chọn!')

    options = question.options or []

    return render(request, 'surveys/choice/choice_form.html', {
        'question': question,
        'survey': survey,
        'options': options,
        'title': 'Thêm lựa chọn'
    })


