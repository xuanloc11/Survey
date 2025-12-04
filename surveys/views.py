from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json
from .models import Survey, Question, Choice, Response, Answer
from .forms import SurveyForm, QuestionForm, ChoiceForm, ResponseForm, UserRegisterForm


def register_view(request):
    """Trang đăng ký"""
    if request.user.is_authenticated:
        return redirect('surveys:home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Tài khoản {username} đã được tạo thành công! Vui lòng đăng nhập.')
            return redirect('surveys:login')
    else:
        form = UserRegisterForm()
    
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    """Trang đăng nhập"""
    if request.user.is_authenticated:
        return redirect('surveys:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('surveys:home')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """Trang đăng xuất"""
    logout(request)
    messages.success(request, 'Bạn đã đăng xuất thành công!')
    return redirect('surveys:home')


def home(request):
    """Trang chủ - hiển thị danh sách khảo sát công khai"""
    surveys = Survey.objects.filter(is_active=True).annotate(
        response_count=Count('responses')
    ).order_by('-created_at')

    # Lọc theo từ khóa
    search_query = request.GET.get('search', '')
    if search_query:
        surveys = surveys.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    context = {
        'surveys': surveys,
        'search_query': search_query,
    }
    return render(request, 'surveys/survey/home.html', context)


@login_required
def dashboard(request):
    """Trang dashboard cho người dùng đã đăng nhập"""
    # Thống kê chung
    total_surveys = Survey.objects.count()
    total_responses = Response.objects.count()

    # Thống kê riêng cho người dùng
    user_surveys = Survey.objects.filter(creator=request.user).annotate(
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


@login_required
def survey_list(request):
    """Danh sách khảo sát của người dùng"""
    surveys = Survey.objects.filter(creator=request.user).annotate(
        response_count=Count('responses')
    ).order_by('-created_at')
    
    context = {
        'surveys': surveys,
    }
    return render(request, 'surveys/survey/survey_list.html', context)


@login_required
def survey_create(request):
    """Tạo khảo sát mới"""
    if request.method == 'POST':
        form = SurveyForm(request.POST, request.FILES)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.creator = request.user
            survey.save()
            messages.success(request, 'Đã tạo khảo sát thành công!')
            return redirect('surveys:survey_detail', pk=survey.pk)
    else:
        form = SurveyForm()
    
    return render(request, 'surveys/survey/survey_form.html', {
        'form': form,
        'title': 'Tạo khảo sát mới'
    })


@login_required
def survey_edit(request, pk):
    """Chỉnh sửa khảo sát"""
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    
    if request.method == 'POST':
        form = SurveyForm(request.POST, request.FILES, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật khảo sát thành công!')
            return redirect('surveys:survey_detail', pk=survey.pk)
    else:
        form = SurveyForm(instance=survey)
    
    return render(request, 'surveys/survey/survey_form.html', {
        'form': form,
        'survey': survey,
        'title': 'Chỉnh sửa khảo sát'
    })


def survey_detail(request, pk):
    """Chi tiết khảo sát"""
    survey = get_object_or_404(Survey, pk=pk)
    questions = survey.questions.all().prefetch_related('choices').order_by('order')
    
    # Kiểm tra xem khảo sát có hết hạn không
    is_expired = survey.expires_at and survey.expires_at < timezone.now()
    
    can_edit = request.user.is_authenticated and request.user == survey.creator
    
    # Sử dụng trang builder nếu là creator, còn lại dùng trang xem chi tiết thường
    template_name = 'surveys/survey/survey_builder.html' if can_edit else 'surveys/survey/survey_detail.html'
    
    context = {
        'survey': survey,
        'questions': questions,
        'is_expired': is_expired,
        'can_edit': can_edit,
    }
    return render(request, template_name, context)


@login_required
def survey_delete(request, pk):
    """Xóa khảo sát"""
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    
    if request.method == 'POST':
        survey.delete()
        messages.success(request, 'Đã xóa khảo sát thành công!')
        return redirect('surveys:survey_list')
    
    return render(request, 'surveys/survey/survey_confirm_delete.html', {
        'survey': survey
    })


@login_required
def question_add(request, survey_pk):
    """Thêm câu hỏi vào khảo sát"""
    survey = get_object_or_404(Survey, pk=survey_pk, creator=request.user)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.survey = survey
            question.save()
            
            # Nếu là câu hỏi có lựa chọn, chuyển đến trang thêm lựa chọn
            if question.question_type in ['single', 'multiple']:
                return redirect('surveys:choice_add', question_pk=question.pk)
            else:
                messages.success(request, 'Đã thêm câu hỏi thành công!')
                return redirect('surveys:survey_detail', pk=survey.pk)
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
    
    if survey.creator != request.user:
        messages.error(request, 'Bạn không có quyền chỉnh sửa câu hỏi này!')
        return redirect('surveys:survey_detail', pk=survey.pk)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật câu hỏi thành công!')
            return redirect('surveys:survey_detail', pk=survey.pk)
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
    """Xóa câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    survey = question.survey
    
    if survey.creator != request.user:
        messages.error(request, 'Bạn không có quyền xóa câu hỏi này!')
        return redirect('surveys:survey_detail', pk=survey.pk)
    
    if request.method == 'POST':
        survey_pk = survey.pk
        question.delete()
        messages.success(request, 'Đã xóa câu hỏi thành công!')
        return redirect('surveys:survey_detail', pk=survey_pk)
    
    return render(request, 'surveys/question/question_confirm_delete.html', {
        'question': question,
        'survey': survey
    })


@login_required
def choice_add(request, question_pk):
    """Thêm lựa chọn cho câu hỏi"""
    question = get_object_or_404(Question, pk=question_pk)
    survey = question.survey
    
    if survey.creator != request.user:
        messages.error(request, 'Bạn không có quyền thêm lựa chọn!')
        return redirect('surveys:survey_detail', pk=survey.pk)
    
    if request.method == 'POST':
        form = ChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save(commit=False)
            choice.question = question
            choice.save()
            
            # Kiểm tra xem có muốn thêm tiếp không
            if 'add_another' in request.POST:
                messages.success(request, 'Đã thêm lựa chọn! Tiếp tục thêm...')
                return redirect('surveys:choice_add', question_pk=question.pk)
            else:
                messages.success(request, 'Đã thêm lựa chọn thành công!')
                return redirect('surveys:survey_detail', pk=survey.pk)
    else:
        form = ChoiceForm()
    
    choices = question.choices.all()
    
    return render(request, 'surveys/choice/choice_form.html', {
        'form': form,
        'question': question,
        'survey': survey,
        'choices': choices,
        'title': 'Thêm lựa chọn'
    })


def survey_take(request, pk):
    """Trang làm khảo sát"""
    survey = get_object_or_404(Survey, pk=pk, is_active=True)
    
    # Kiểm tra hết hạn
    if survey.expires_at and survey.expires_at < timezone.now():
        messages.error(request, 'Khảo sát này đã hết hạn!')
        return redirect('surveys:survey_detail', pk=pk)
    
    # Kiểm tra xem đã trả lời chưa (nếu đã đăng nhập)
    if request.user.is_authenticated:
        has_responded = Response.objects.filter(survey=survey, respondent=request.user).exists()
        if has_responded:
            messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
            if survey.creator == request.user:
                return redirect('surveys:survey_results', pk=pk)
            else:
                return redirect('surveys:survey_detail', pk=pk)
    
    if request.method == 'POST':
        # Validate required questions
        errors = []
        for question in survey.questions.all():
            field_name = f'question_{question.id}'
            if question.is_required:
                if question.question_type == 'multiple':
                    if field_name not in request.POST or not request.POST.getlist(field_name):
                        errors.append(f'Vui lòng trả lời câu hỏi: {question.text}')
                else:
                    if field_name not in request.POST or not request.POST.get(field_name):
                        errors.append(f'Vui lòng trả lời câu hỏi: {question.text}')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create response
            response = Response.objects.create(
                survey=survey,
                respondent=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request)
            )
            
            # Save answers
            for question in survey.questions.all():
                field_name = f'question_{question.id}'
                
                if question.question_type == 'text':
                    text_answer = request.POST.get(field_name, '').strip()
                    if text_answer:
                        Answer.objects.create(
                            response=response,
                            question=question,
                            text_answer=text_answer
                        )
                elif question.question_type == 'single':
                    choice_id = request.POST.get(field_name)
                    if choice_id:
                        try:
                            choice = Choice.objects.get(pk=choice_id, question=question)
                            Answer.objects.create(
                                response=response,
                                question=question,
                                choice=choice
                            )
                        except Choice.DoesNotExist:
                            pass
                elif question.question_type == 'multiple':
                    choice_ids = request.POST.getlist(field_name)
                    for choice_id in choice_ids:
                        try:
                            choice = Choice.objects.get(pk=choice_id, question=question)
                            Answer.objects.create(
                                response=response,
                                question=question,
                                choice=choice
                            )
                        except Choice.DoesNotExist:
                            pass
            
            messages.success(request, 'Cảm ơn bạn đã tham gia khảo sát!')
            if request.user == survey.creator:
                return redirect('surveys:survey_results', pk=pk)
            else:
                return redirect('surveys:survey_detail', pk=pk)
    
    questions = survey.questions.all().prefetch_related('choices')
    
    return render(request, 'surveys/survey/survey_take.html', {
        'survey': survey,
        'questions': questions
    })


@login_required
def survey_results(request, pk):
    """Kết quả khảo sát"""
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    
    responses = survey.responses.all()
    questions = survey.questions.all().prefetch_related('choices').order_by('order')
    
    # Prefetch answers để tối ưu query
    question_ids = [q.id for q in questions]
    answers = Answer.objects.filter(question_id__in=question_ids).select_related('choice')
    
    # Thống kê
    stats = []
    total_responses_count = responses.count()
    
    for question in questions:
        if question.question_type == 'text':
            # Đếm số câu trả lời text
            text_answers = [a for a in answers if a.question_id == question.id and a.text_answer]
            stats.append({
                'question': question,
                'type': 'text',
                'answers': text_answers[:10],  # Hiển thị 10 câu trả lời đầu
                'total': len(text_answers)
            })
        else:
            # Thống kê lựa chọn
            choice_stats = []
            for choice in question.choices.all():
                count = sum(1 for a in answers if a.question_id == question.id and a.choice_id == choice.id)
                percentage = (count / total_responses_count * 100) if total_responses_count > 0 else 0
                choice_stats.append({
                    'choice': choice,
                    'count': count,
                    'percentage': round(percentage, 1)
                })
            stats.append({
                'question': question,
                'type': question.question_type,
                'choices': choice_stats,
                'total': total_responses_count
            })
    
    context = {
        'survey': survey,
        'responses': responses,
        'stats': stats,
        'total_responses': total_responses_count
    }
    return render(request, 'surveys/survey/survey_results.html', context)


def get_client_ip(request):
    """Lấy IP address của client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ========== AJAX API Endpoints ==========

@login_required
@require_http_methods(["POST"])
def question_add_ajax(request, survey_pk):
    """API AJAX để thêm câu hỏi"""
    survey = get_object_or_404(Survey, pk=survey_pk, creator=request.user)
    
    try:
        data = json.loads(request.body)
        question = Question.objects.create(
            survey=survey,
            text=data.get('text', ''),
            question_type=data.get('question_type', 'single'),
            order=data.get('order', survey.questions.count() + 1),
            is_required=data.get('is_required', True)
        )
        
        choices_data = data.get('choices', [])
        for idx, choice_text in enumerate(choices_data):
            if choice_text.strip():
                Choice.objects.create(
                    question=question,
                    text=choice_text.strip(),
                    order=idx + 1
                )
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'choices': [{'id': c.id, 'text': c.text} for c in question.choices.all()]
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_update_ajax(request, pk):
    """API AJAX để cập nhật câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        data = json.loads(request.body)
        question.text = data.get('text', question.text)
        question.question_type = data.get('question_type', question.question_type)
        question.order = data.get('order', question.order)
        question.is_required = data.get('is_required', question.is_required)
        question.save()
        
        # Cập nhật lựa chọn nếu có
        if 'choices' in data:
            # Xóa lựa chọn cũ
            question.choices.all().delete()
            # Thêm lựa chọn mới
            for idx, choice_text in enumerate(data['choices']):
                if choice_text.strip():
                    Choice.objects.create(
                        question=question,
                        text=choice_text.strip(),
                        order=idx + 1
                    )
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'choices': [{'id': c.id, 'text': c.text} for c in question.choices.all()]
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_delete_ajax(request, pk):
    """API AJAX để xóa câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        question.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_reorder_ajax(request, survey_pk):
    """API AJAX để sắp xếp lại thứ tự câu hỏi"""
    survey = get_object_or_404(Survey, pk=survey_pk, creator=request.user)
    
    try:
        data = json.loads(request.body)
        question_orders = data.get('orders', [])  # [{id: 1, order: 1}, {id: 2, order: 2}]
        
        for item in question_orders:
            Question.objects.filter(pk=item['id'], survey=survey).update(order=item['order'])
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def choice_add_ajax(request, question_pk):
    """API AJAX để thêm lựa chọn"""
    question = get_object_or_404(Question, pk=question_pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        data = json.loads(request.body)
        choice = Choice.objects.create(
            question=question,
            text=data.get('text', ''),
            order=data.get('order', question.choices.count() + 1)
        )
        
        return JsonResponse({
            'success': True,
            'choice': {
                'id': choice.id,
                'text': choice.text,
                'order': choice.order
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def choice_delete_ajax(request, pk):
    """API AJAX để xóa lựa chọn"""
    choice = get_object_or_404(Choice, pk=pk)
    
    if choice.question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        choice.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ========== AJAX API Endpoints ==========

@login_required
@require_http_methods(["POST"])
def question_add_ajax(request, survey_pk):
    """API AJAX để thêm câu hỏi"""
    survey = get_object_or_404(Survey, pk=survey_pk, creator=request.user)
    
    try:
        data = json.loads(request.body)
        question = Question.objects.create(
            survey=survey,
            text=data.get('text', ''),
            question_type=data.get('question_type', 'single'),
            order=data.get('order', survey.questions.count() + 1),
            is_required=data.get('is_required', True)
        )
        
        choices_data = data.get('choices', [])
        for idx, choice_text in enumerate(choices_data):
            if choice_text.strip():
                Choice.objects.create(
                    question=question,
                    text=choice_text.strip(),
                    order=idx + 1
                )
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'choices': [{'id': c.id, 'text': c.text} for c in question.choices.all()]
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_update_ajax(request, pk):
    """API AJAX để cập nhật câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        data = json.loads(request.body)
        question.text = data.get('text', question.text)
        question.question_type = data.get('question_type', question.question_type)
        question.order = data.get('order', question.order)
        question.is_required = data.get('is_required', question.is_required)
        question.save()
        
        # Cập nhật lựa chọn nếu có
        if 'choices' in data:
            # Xóa lựa chọn cũ
            question.choices.all().delete()
            # Thêm lựa chọn mới
            for idx, choice_text in enumerate(data['choices']):
                if choice_text.strip():
                    Choice.objects.create(
                        question=question,
                        text=choice_text.strip(),
                        order=idx + 1
                    )
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'choices': [{'id': c.id, 'text': c.text} for c in question.choices.all()]
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_delete_ajax(request, pk):
    """API AJAX để xóa câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        question.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_reorder_ajax(request, survey_pk):
    """API AJAX để sắp xếp lại thứ tự câu hỏi"""
    survey = get_object_or_404(Survey, pk=survey_pk, creator=request.user)
    
    try:
        data = json.loads(request.body)
        question_orders = data.get('orders', [])  # [{id: 1, order: 1}, {id: 2, order: 2}]
        
        for item in question_orders:
            Question.objects.filter(pk=item['id'], survey=survey).update(order=item['order'])
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def choice_add_ajax(request, question_pk):
    """API AJAX để thêm lựa chọn"""
    question = get_object_or_404(Question, pk=question_pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        data = json.loads(request.body)
        choice = Choice.objects.create(
            question=question,
            text=data.get('text', ''),
            order=data.get('order', question.choices.count() + 1)
        )
        
        return JsonResponse({
            'success': True,
            'choice': {
                'id': choice.id,
                'text': choice.text,
                'order': choice.order
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def choice_delete_ajax(request, pk):
    """API AJAX để xóa lựa chọn"""
    choice = get_object_or_404(Choice, pk=pk)
    
    if choice.question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        choice.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
