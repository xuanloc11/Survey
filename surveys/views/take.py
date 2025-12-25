from uuid import uuid4
from urllib.parse import quote

import requests

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.core import signing
from django.core.mail import send_mail

from ..models import Survey, Response
from .utils import get_client_ip


def survey_take(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    session_key = f'survey_access_{survey.id}'
    done_session_key = f'survey_done_{survey.id}'

    default_back_url = (
        reverse('surveys:survey_list')
        if request.user.is_authenticated
        else reverse('surveys:home')
    )

    back_url = request.META.get('HTTP_REFERER')
    current_url = request.build_absolute_uri(request.get_full_path())
    if back_url:
        if back_url.rstrip('/') == current_url.rstrip('/'):
            back_url = None
    if not back_url:
        back_url = reverse('surveys:survey_detail', args=[survey.pk])

    if (not survey.is_active) or getattr(survey, 'is_deleted', False):
        return render(request, 'surveys/survey_management/survey_take.html', {
            'survey': survey,
            'questions': [],
            'survey_closed': True,
            'back_url': default_back_url,
        })

    if getattr(survey, 'starts_at', None) and survey.starts_at > timezone.now():
        return render(request, 'surveys/survey_management/survey_take.html', {
            'survey': survey,
            'questions': [],
            'survey_closed': True,
            'survey_closed_title': 'Khảo sát chưa mở',
            'survey_closed_message': 'Khảo sát chưa đến thời gian bắt đầu nên hiện không nhận phản hồi.',
            'back_url': default_back_url,
        })

    if not request.session.session_key:
        request.session.create()
    if 'anon_session_id' not in request.session:
        request.session['anon_session_id'] = uuid4().hex

    whitelist_raw = survey.whitelist_emails or ""
    whitelist = {email.strip().lower() for email in whitelist_raw.splitlines() if email.strip()}

    if whitelist and not request.user.is_authenticated:
        messages.error(request, 'Khảo sát này yêu cầu đăng nhập bằng email nằm trong danh sách.')
        next_url = quote(request.get_full_path(), safe="/?=&")
        return redirect(f"{reverse('surveys:login')}?next={next_url}")

    responses_count = survey.responses.count()
    if survey.max_responses and responses_count >= survey.max_responses:
        messages.error(request, 'Khảo sát đã đạt tới giới hạn số phản hồi.')
        return redirect('surveys:survey_detail', pk=pk)
    if survey.password:
        has_access = request.session.get(session_key)
        if not has_access:
            if request.method == 'POST' and 'survey_password' in request.POST:
                entered_password = request.POST.get('survey_password', '')
                if entered_password and check_password(entered_password, survey.password):
                    request.session[session_key] = True
                    messages.success(request, 'Đã xác nhận mật khẩu khảo sát.')
                    return redirect('surveys:survey_take', pk=pk)
                else:
                    messages.error(request, 'Mật khẩu không đúng. Vui lòng thử lại.')
            return render(request, 'surveys/survey_management/survey_take.html', {
                'survey': survey,
                'questions': [],
                'need_password': True,
                'back_url': back_url,
            })

    if survey.expires_at and survey.expires_at < timezone.now():
        messages.error(request, 'Khảo sát này đã hết hạn!')
        return redirect('surveys:survey_detail', pk=pk)

    if whitelist and request.user.is_authenticated:
        user_email = (request.user.email or '').strip().lower()
        if not user_email:
            messages.error(request, 'Tài khoản của bạn chưa có email nên không thể tham gia khảo sát whitelist. Vui lòng cập nhật email trong hồ sơ.')
            return redirect('surveys:profile')
        if user_email not in whitelist and request.user != survey.creator:
            messages.error(request, 'Email của bạn không nằm trong whitelist tham gia khảo sát.')
            return redirect('surveys:survey_detail', pk=pk)

    if request.user.is_authenticated:
        existing_response = Response.objects.filter(survey=survey, respondent=request.user).first()
        if existing_response:
            if survey.creator == request.user:
                messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
                return redirect('surveys:survey_results', pk=pk)
            else:
                if not survey.one_response_only:
                    pass
                else:
                    if survey.allow_review_response:
                        messages.info(request, 'Bạn đã tham gia khảo sát này rồi! Đang chuyển đến xem lại câu trả lời của bạn.')
                        return redirect('surveys:survey_review_response', response_id=existing_response.id)
                    elif not survey.allow_review_response and survey.send_confirmation_email:
                        messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
                        return redirect('surveys:survey_thankyou', pk=pk)
                    else:
                        messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
                        return redirect('surveys:survey_detail', pk=pk)
    else:
        if request.session.get(done_session_key):
            response_id_key = f'survey_response_{survey.id}'
            response_id = request.session.get(response_id_key)

            if not survey.one_response_only:
                pass
            else:
                if response_id:
                    if survey.allow_review_response:
                        messages.info(request, 'Bạn đã tham gia khảo sát này rồi! Đang chuyển đến xem lại câu trả lời của bạn.')
                        return redirect('surveys:survey_review_response', response_id=response_id)
                    elif not survey.allow_review_response and survey.send_confirmation_email:
                        messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
                        return redirect('surveys:survey_thankyou', pk=pk)

                messages.info(request, 'Bạn đã tham gia khảo sát này rồi từ thiết bị này!')
                return redirect('surveys:survey_detail', pk=pk)

        client_ip = get_client_ip(request)
        existing_response_ip = Response.objects.filter(
            survey=survey,
            respondent__isnull=True,
            ip_address=client_ip
        ).first()
        if existing_response_ip:
            if not survey.one_response_only:
                pass
            else:
                if survey.allow_review_response:
                    messages.info(request, 'Bạn đã tham gia khảo sát này rồi! Đang chuyển đến xem lại câu trả lời của bạn.')
                    return redirect('surveys:survey_review_response', response_id=existing_response_ip.id)
                elif not survey.allow_review_response and survey.send_confirmation_email:
                    messages.info(request, 'Bạn đã tham gia khảo sát này rồi!')
                    return redirect('surveys:survey_thankyou', pk=pk)
                else:
                    messages.info(request, 'Bạn đã tham gia khảo sát này rồi từ thiết bị này!')
                    return redirect('surveys:survey_detail', pk=pk)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            cf_response = request.POST.get('cf-turnstile-response')

            if not cf_response:
                messages.error(request, 'Vui lòng hoàn thành xác minh captcha.')
                questions = survey.questions.all()
                return render(request, 'surveys/survey_management/survey_take.html', {
                    'survey': survey,
                    'questions': questions,
                    'need_password': False,
                    'back_url': back_url,
                    'TURNSTILE_SITE_KEY': settings.CLOUDFLARE_TURNSTILE_SITE_KEY,
                })

            verify_url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
            verify_data = {
                'secret': settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                'response': cf_response,
                'remoteip': get_client_ip(request)
            }

            try:
                verify_result = requests.post(verify_url, data=verify_data, timeout=10).json()

                if not verify_result.get('success'):
                    messages.error(request, 'Xác minh captcha thất bại. Vui lòng thử lại.')
                    questions = survey.questions.all()
                    return render(request, 'surveys/survey_management/survey_take.html', {
                        'survey': survey,
                        'questions': questions,
                        'need_password': False,
                        'back_url': back_url,
                        'TURNSTILE_SITE_KEY': settings.CLOUDFLARE_TURNSTILE_SITE_KEY,
                    })
            except requests.RequestException:
                messages.error(request, 'Không thể xác minh captcha. Vui lòng thử lại sau.')
                questions = survey.questions.all()
                return render(request, 'surveys/survey_management/survey_take.html', {
                    'survey': survey,
                    'questions': questions,
                    'need_password': False,
                    'back_url': back_url,
                    'TURNSTILE_SITE_KEY': settings.CLOUDFLARE_TURNSTILE_SITE_KEY,
                })

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
            response_data = {}
            for question in survey.questions.all():
                field_name = f'question_{question.id}'

                if question.question_type == 'text':
                    text_answer = request.POST.get(field_name, '').strip()
                    if text_answer:
                        response_data[str(question.id)] = text_answer
                elif question.question_type == 'single':
                    selected_index = request.POST.get(field_name)
                    if selected_index and question.options:
                        try:
                            index = int(selected_index)
                            if 0 <= index < len(question.options):
                                response_data[str(question.id)] = question.options[index]
                        except (ValueError, IndexError):
                            pass
                elif question.question_type == 'multiple':
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

            response = Response.objects.create(
                survey=survey,
                respondent=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                response_data=response_data
            )
            request.session[done_session_key] = True
            response_id_key = f'survey_response_{survey.id}'
            request.session[response_id_key] = response.id

            messages.success(request, 'Cảm ơn bạn đã tham gia khảo sát!')

            if survey.allow_review_response:
                return redirect('surveys:survey_review_response', response_id=response.id)
            else:
                if survey.send_confirmation_email and request.user.is_authenticated and request.user.email:
                    try:
                        from django.template.loader import render_to_string

                        email_context = {
                            'survey': survey,
                            'user_email': request.user.email,
                            'completion_time': timezone.now(),
                        }

                        html_message = render_to_string('surveys/email/survey_confirmation.html', email_context)

                        send_mail(
                            subject=f'Cảm ơn bạn đã tham gia: {survey.title}',
                            message=f'Cảm ơn bạn đã hoàn thành khảo sát "{survey.title}". Câu trả lời của bạn đã được ghi nhận.',
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[request.user.email],
                            html_message=html_message,
                            fail_silently=True,
                        )
                    except Exception:
                        pass

                    return redirect('surveys:survey_thankyou', pk=pk)
                else:
                    return redirect('surveys:survey_detail', pk=pk)

    questions = survey.questions.all()

    return render(request, 'surveys/survey_management/survey_take.html', {
        'survey': survey,
        'questions': questions,
        'need_password': False,
        'back_url': back_url,
        'TURNSTILE_SITE_KEY': settings.CLOUDFLARE_TURNSTILE_SITE_KEY,
    })


def survey_take_token(request, token):
    try:
        pk = signing.loads(token, salt="survey-share", max_age=None)
    except signing.BadSignature:
        messages.error(request, 'Link khảo sát không hợp lệ hoặc đã bị thay đổi.')
        return redirect('surveys:home')
    return redirect('surveys:survey_take', pk=pk)


def survey_review_response(request, response_id):
    response = get_object_or_404(Response, pk=response_id)
    survey = response.survey

    if not survey.allow_review_response:
        if request.user != survey.creator:
            messages.error(request, 'Khảo sát này không cho phép xem lại câu trả lời.')
            return redirect('surveys:survey_detail', pk=survey.pk)

    if request.user.is_authenticated:
        if response.respondent != request.user and survey.creator != request.user:
            messages.error(request, 'Bạn không có quyền xem câu trả lời này.')
            return redirect('surveys:home')
    else:
        client_ip = get_client_ip(request)
        if response.respondent is not None or response.ip_address != client_ip:
            messages.error(request, 'Bạn không có quyền xem câu trả lời này.')
            return redirect('surveys:home')

    questions = survey.questions.all()
    response_data = response.response_data or {}
    questions_with_answers = []
    for question in questions:
        if question.question_type in ['text', 'single', 'multiple']:
            answer = response_data.get(str(question.id))
            questions_with_answers.append({
                'question': question,
                'answer': answer
            })

    return render(request, 'surveys/survey_management/survey_review.html', {
        'survey': survey,
        'response': response,
        'questions_with_answers': questions_with_answers,
    })


def survey_thankyou(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    user_email = None
    if request.user.is_authenticated:
        user_email = request.user.email

    return render(request, 'surveys/survey_management/survey_thankyou.html', {
        'survey': survey,
        'user_email': user_email,
        'completion_time': timezone.now(),
    })


