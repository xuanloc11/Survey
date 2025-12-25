from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.urls import reverse

from ..forms import UserRegisterForm, UserProfileForm

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('surveys:home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user: User = form.save(commit=False)
            user.is_active = False
            user.save()

            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse('surveys:activate', kwargs={'uidb64': uidb64, 'token': token})
            )

            subject = 'Xác nhận đăng ký tài khoản HCMUTE Survey'
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
                    'Đăng ký tài khoản thành công! Vui lòng kiểm tra email để xác nhận tài khoản trước khi đăng nhập.'
                )
            except Exception:
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
        return redirect('surveys:survey_list')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('surveys:survey_list')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')

    return render(request, 'auth/login.html')


def logout_view(request):
    """Trang đăng xuất"""
    logout(request)
    messages.success(request, 'Bạn đã đăng xuất thành công!')
    return redirect('surveys:home')


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Vui lòng nhập email đã đăng ký.')
        else:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = None

            if user is None:
                messages.error(request, 'Không tìm thấy tài khoản nào với email này.')
            else:
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = request.build_absolute_uri(
                    reverse('surveys:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
                )

                subject = 'Đặt lại mật khẩu tài khoản hệ thống khảo sát HCMUTE'
                message = (
                    f'Xin chào {user.username},\n\n'
                    'Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản HCMUTE Survey.\n'
                    'Vui lòng nhấp vào liên kết dưới đây để đặt mật khẩu mới:\n\n'
                    f'{reset_link}\n\n'
                    'Nếu bạn không yêu cầu, hãy bỏ qua email này.\n\n'
                    'Trân trọng,\n'
                    'Đội ngũ HCMUTE Survey'
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
                        'Đã gửi email hướng dẫn đặt lại mật khẩu. Vui lòng kiểm tra hộp thư của bạn.'
                    )
                    return redirect('surveys:login')
                except Exception:
                    messages.error(
                        request,
                        'Hiện không gửi được email đặt lại mật khẩu. Vui lòng thử lại sau hoặc liên hệ quản trị viên.'
                    )

    return render(request, 'auth/password_reset_request.html')


def password_reset_confirm(request, uidb64, token):
    """Đặt mật khẩu mới từ link trong email"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.')
        return redirect('surveys:login')

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not password1 or not password2:
            messages.error(request, 'Vui lòng nhập đầy đủ mật khẩu mới.')
        elif password1 != password2:
            messages.error(request, 'Mật khẩu nhập lại không khớp.')
        elif len(password1) < 6:
            messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự.')
        else:
            user.set_password(password1)
            user.save()
            messages.success(request, 'Đã đặt lại mật khẩu thành công. Bây giờ bạn có thể đăng nhập.')
            return redirect('surveys:login')

    return render(request, 'auth/password_reset_confirm.html', {'uidb64': uidb64, 'token': token})


@login_required
def profile_view(request):
    """Trang thông tin cá nhân"""
    from ..models import UserProfile
    UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật thông tin cá nhân!')
            return redirect('surveys:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'auth/profile.html', {'form': form})


