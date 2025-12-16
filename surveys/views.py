from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.urls import reverse
import json
import csv
from .models import Survey, Question, Response
from .forms import (
    SurveyForm,
    QuestionForm,
    ResponseForm,
    UserRegisterForm,
    UserProfileForm,
)

User = get_user_model()


def register_view(request):
    """Trang đăng ký với xác nhận email"""
    if request.user.is_authenticated:
        return redirect('surveys:home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user: User = form.save(commit=False)
            # Tài khoản cần xác nhận email trước khi có thể đăng nhập
            user.is_active = False
            user.save()

            # Gửi email xác nhận
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse('surveys:activate', kwargs={'uidb64': uidb64, 'token': token})
            )

            subject = 'Xác nhận tài khoản HCMUTE Survey'
            message = (
                f'Xin chào {user.username},\n\n'
                'Cảm ơn bạn đã đăng ký tài khoản trên HCMUTE Survey.\n'
                'Vui lòng nhấp vào liên kết dưới đây để kích hoạt tài khoản của bạn:\n\n'
                f'{activation_link}\n\n'
                'Nếu bạn không thực hiện đăng ký này, hãy bỏ qua email.\n\n'
                'Trân trọng,\n'
                'HCMUTE Survey'
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    'Đăng ký thành công! Vui lòng kiểm tra email để xác nhận tài khoản trước khi đăng nhập.'
                )
            except Exception:
                # Nếu gửi mail lỗi, vẫn tạo tài khoản nhưng thông báo cho admin qua log/message
                messages.warning(
                    request,
                    'Đăng ký thành công nhưng hiện không gửi được email xác nhận. '
                    'Hãy liên hệ quản trị viên để kích hoạt tài khoản.'
                )

            return redirect('surveys:login')
    else:
        form = UserRegisterForm()

    return render(request, 'auth/register.html', {'form': form})


def activate_account(request, uidb64, token):
    """Kích hoạt tài khoản từ link trong email"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
        messages.success(request, 'Tài khoản của bạn đã được kích hoạt. Bây giờ bạn có thể đăng nhập.')
        return redirect('surveys:login')

    messages.error(request, 'Link kích hoạt không hợp lệ hoặc đã hết hạn.')
    return redirect('surveys:login')


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


@login_required
def profile_view(request):
    """Trang thông tin cá nhân"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật thông tin cá nhân!')
            return redirect('surveys:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'auth/profile.html', {'form': form})


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
        # Khi đang ở chế độ builder (người tạo đang chỉnh sửa),
        # ẩn các nút điều hướng chính trên navbar để giống Google Forms
        'builder_mode': can_edit,
        # Link chia sẻ công khai
        'share_link': request.build_absolute_uri(
            reverse('surveys:survey_take', args=[survey.pk])
        ),
    }
    
    # Thêm dữ liệu cho tab "Kết quả" nếu là creator
    if can_edit:
        responses = survey.responses.all()
        total_responses_count = responses.count()
        
        # Thống kê
        stats = []
        for question in questions:
            question_id_str = str(question.id)
            
            if question.question_type not in ['text', 'single', 'multiple']:
                continue
            
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
        
        context['stats'] = stats
        context['total_responses'] = total_responses_count
        context['responses'] = responses
    
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
    
    # Kiểm tra xem đã trả lời chưa
    if request.user.is_authenticated:
        has_responded = Response.objects.filter(survey=survey, respondent=request.user).exists()
        if has_responded:
            messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
            if survey.creator == request.user:
                return redirect('surveys:survey_results', pk=pk)
            else:
                return redirect('surveys:survey_detail', pk=pk)
    else:
        # Người dùng không đăng nhập: giới hạn theo IP (1 lần / khảo sát)
        client_ip = get_client_ip(request)
        has_responded_ip = Response.objects.filter(
            survey=survey,
            respondent__isnull=True,
            ip_address=client_ip
        ).exists()
        if has_responded_ip:
            messages.info(request, 'Bạn đã tham gia khảo sát này rồi từ thiết bị này!')
            return redirect('surveys:survey_detail', pk=pk)
    
    if request.method == 'POST':
        # Validate required questions
        errors = []
        for question in survey.questions.all():
            field_name = f'question_{question.id}'
            if question.question_type not in ['text', 'single', 'multiple']:
                continue
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
        
        if question.question_type not in ['text', 'single', 'multiple']:
            continue
        
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


@login_required
def survey_export_csv(request, pk):
    """Xuất kết quả khảo sát ra file CSV"""
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)

    responses = survey.responses.all().order_by('submitted_at')
    questions = survey.questions.all().order_by('order')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="survey_{survey.pk}_responses.csv"'
    response.write("\ufeff")  # BOM
    writer = csv.writer(response, delimiter=';')
    header = ['Thời gian']
    for question in questions:
        header.append(question.text)
    writer.writerow(header)

    # Ghi từng dòng dữ liệu
    for resp in responses:
        # Thời gian theo định dạng dễ đọc (giống Google Form)
        submitted_local = timezone.localtime(resp.submitted_at)
        time_display = submitted_local.strftime("%d/%m/%Y %H:%M:%S")
        row = [time_display]

        for question in questions:
            qid = str(question.id)
            answer = ''
            if resp.response_data and qid in resp.response_data:
                value = resp.response_data[qid]
                if isinstance(value, list):
                    answer = ' | '.join(str(v) for v in value)
                else:
                    answer = str(value)
            row.append(answer)

        writer.writerow(row)

    return response


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
            is_required=data.get('is_required', True),
            subtitle=data.get('subtitle', ''),
            media_url=data.get('media_url', '')
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
            'options': question.options or [],
            'subtitle': question.subtitle,
            'media_url': question.media_url
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
        question.subtitle = data.get('subtitle', question.subtitle)
        question.media_url = data.get('media_url', question.media_url)
        
        # Cập nhật options nếu có
        if 'choices' in data or 'options' in data:
            options_data = data.get('choices', []) or data.get('options', [])
            question.options = [opt.strip() for opt in options_data if opt and opt.strip()]

        # Cập nhật đáp án đúng cho chế độ Quiz nếu có
        if 'correct_answers' in data:
            raw_correct = data.get('correct_answers') or []
            cleaned = []
            for idx in raw_correct:
                try:
                    i = int(idx)
                    cleaned.append(i)
                except (TypeError, ValueError):
                    continue
            question.correct_answers = cleaned

        question.save()
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'text': question.text,
            'question_type': question.question_type,
            'is_required': question.is_required,
            'order': question.order,
            'options': question.options or [],
            'correct_answers': question.correct_answers or [],
            'subtitle': question.subtitle,
            'media_url': question.media_url
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
def survey_publish_toggle_ajax(request, pk):
    """Bật/tắt xuất bản khảo sát"""
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    try:
        data = json.loads(request.body or "{}")
        is_active = bool(data.get('is_active', True))
        survey.is_active = is_active
        survey.save(update_fields=['is_active'])
        return JsonResponse({'success': True, 'is_active': survey.is_active})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_image_upload_ajax(request, pk):
    """Upload ảnh cho câu hỏi và lưu đường dẫn vào media_url"""
    question = get_object_or_404(Question, pk=pk)

    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)

    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({'success': False, 'error': 'Không có file ảnh'}, status=400)

    try:
        fs = FileSystemStorage(
            location=settings.MEDIA_ROOT / 'question_images',
            base_url=settings.MEDIA_URL + 'question_images/'
        )
        filename = fs.save(image_file.name, image_file)
        file_url = fs.url(filename)

        question.media_url = file_url
        question.save(update_fields=['media_url'])

        return JsonResponse({'success': True, 'url': file_url})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def choice_add_ajax(request, question_pk):
    """API AJAX để thêm lựa chọn cho câu hỏi"""
    question = get_object_or_404(Question, pk=question_pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        data = json.loads(request.body)
        option_text = data.get('text', '').strip()
        
        if not option_text:
            return JsonResponse({'success': False, 'error': 'Vui lòng nhập nội dung lựa chọn!'}, status=400)
        
        # Thêm vào options (JSONField)
        if question.options is None:
            question.options = []
        question.options.append(option_text)
        question.save()
        
        return JsonResponse({
            'success': True,
            'choice': {
                'text': option_text,
                'index': len(question.options) - 1
            },
            'options': question.options
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def choice_delete_ajax(request, pk):
    """API AJAX để xóa lựa chọn khỏi câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    
    if question.survey.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
    
    try:
        data = json.loads(request.body)
        choice_index = data.get('index')
        
        if choice_index is None:
            return JsonResponse({'success': False, 'error': 'Thiếu thông tin index'}, status=400)
        
        if question.options is None or not isinstance(question.options, list):
            return JsonResponse({'success': False, 'error': 'Không có lựa chọn nào'}, status=400)
        
        try:
            index = int(choice_index)
            if 0 <= index < len(question.options):
                removed_option = question.options.pop(index)
                question.save()
                return JsonResponse({
                    'success': True,
                    'removed_option': removed_option,
                    'options': question.options
                })
            else:
                return JsonResponse({'success': False, 'error': 'Index không hợp lệ'}, status=400)
        except (ValueError, IndexError):
            return JsonResponse({'success': False, 'error': 'Index không hợp lệ'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


