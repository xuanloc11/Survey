from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json
from .models import Survey, Question, Response
from .forms import SurveyForm, QuestionForm, ResponseForm, UserRegisterForm


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
    questions = survey.questions.all().order_by('order')
    
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
        option_text = request.POST.get('text', '').strip()
        if option_text:
            # Thêm vào options (JSONField)
            if question.options is None:
                question.options = []
            question.options.append(option_text)
            question.save()
            
            # Kiểm tra xem có muốn thêm tiếp không
            if 'add_another' in request.POST:
                messages.success(request, 'Đã thêm lựa chọn! Tiếp tục thêm...')
                return redirect('surveys:choice_add', question_pk=question.pk)
            else:
                messages.success(request, 'Đã thêm lựa chọn thành công!')
                return redirect('surveys:survey_detail', pk=survey.pk)
        else:
            messages.error(request, 'Vui lòng nhập nội dung lựa chọn!')
    
    # Lấy options từ JSONField
    options = question.options or []
    
    return render(request, 'surveys/choice/choice_form.html', {
        'question': question,
        'survey': survey,
        'options': options,
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
            # Lưu tất cả câu trả lời vào response_data (JSONField)
            response_data = {}
            for question in survey.questions.all():
                field_name = f'question_{question.id}'
                
                if question.question_type == 'text':
                    text_answer = request.POST.get(field_name, '').strip()
                    if text_answer:
                        response_data[str(question.id)] = text_answer
                elif question.question_type == 'single':
                    # Lấy index của option được chọn
                    selected_index = request.POST.get(field_name)
                    if selected_index and question.options:
                        try:
                            index = int(selected_index)
                            if 0 <= index < len(question.options):
                                response_data[str(question.id)] = question.options[index]
                        except (ValueError, IndexError):
                            pass
                elif question.question_type == 'multiple':
                    # Lấy danh sách các index được chọn
                    selected_indices = request.POST.getlist(field_name)
                    if selected_indices and question.options:
                        selected_options = []
                        for idx_str in selected_indices:
                            try:
                                index = int(idx_str)
                                if 0 <= index < len(question.options):
                                    selected_options.append(question.options[index])
                            except (ValueError, IndexError):
                                pass
                        if selected_options:
                            response_data[str(question.id)] = selected_options
            
            # Create response với response_data
            response = Response.objects.create(
                survey=survey,
                respondent=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                response_data=response_data
            )
            
            messages.success(request, 'Cảm ơn bạn đã tham gia khảo sát!')
            if request.user == survey.creator:
                return redirect('surveys:survey_results', pk=pk)
            else:
                return redirect('surveys:survey_detail', pk=pk)
    
    questions = survey.questions.all()
    
    return render(request, 'surveys/survey/survey_take.html', {
        'survey': survey,
        'questions': questions
    })


@login_required
def survey_results(request, pk):
    """Kết quả khảo sát"""
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    
    responses = survey.responses.all()
    questions = survey.questions.all().order_by('order')
    
    # Thống kê
    stats = []
    total_responses_count = responses.count()
    
    for question in questions:
        question_id_str = str(question.id)
        
        if question.question_type == 'text':
            # Thu thập tất cả câu trả lời text
            text_answers = []
            for response in responses:
                if response.response_data and question_id_str in response.response_data:
                    answer_value = response.response_data[question_id_str]
                    if isinstance(answer_value, str) and answer_value.strip():
                        text_answers.append(answer_value)
            
            stats.append({
                'question': question,
                'type': 'text',
                'answers': text_answers[:10],  # Hiển thị 10 câu trả lời đầu
                'total': len(text_answers)
            })
        else:
            # Thống kê lựa chọn từ options (JSONField)
            choice_stats = []
            if question.options:
                for idx, option_text in enumerate(question.options):
                    count = 0
                    for response in responses:
                        if response.response_data and question_id_str in response.response_data:
                            answer_value = response.response_data[question_id_str]
                            if question.question_type == 'single':
                                # So sánh với option text
                                if answer_value == option_text:
                                    count += 1
                            elif question.question_type == 'multiple':
                                # Kiểm tra nếu option có trong danh sách
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
        
        # Lưu options vào JSONField
        options_data = data.get('choices', []) or data.get('options', [])
        question.options = [opt.strip() for opt in options_data if opt and opt.strip()]
        question.save()
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'options': question.options or []
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
        
        # Cập nhật options nếu có
        if 'choices' in data or 'options' in data:
            options_data = data.get('choices', []) or data.get('options', [])
            question.options = [opt.strip() for opt in options_data if opt and opt.strip()]
        
        question.save()
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'options': question.options or []
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
        
        # Lưu options vào JSONField
        options_data = data.get('choices', []) or data.get('options', [])
        question.options = [opt.strip() for opt in options_data if opt and opt.strip()]
        question.save()
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'options': question.options or []
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
        
        # Cập nhật options nếu có
        if 'choices' in data or 'options' in data:
            options_data = data.get('choices', []) or data.get('options', [])
            question.options = [opt.strip() for opt in options_data if opt and opt.strip()]
        
        question.save()
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
                'question_type': question.question_type,
                'is_required': question.is_required,
                'order': question.order,
                'options': question.options or []
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


