from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Survey, Question, Response, UserProfile


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        # Quiz mode is disabled in this project (feature turned off)
        fields = ['title', 'description', 'header_image', 'is_active', 'expires_at', 'max_responses', 'password', 'whitelist_emails', 'allow_review_response', 'send_confirmation_email', 'one_response_only']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tiêu đề khảo sát'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Nhập mô tả khảo sát'}),
            'header_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'max_responses': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Ví dụ: 100'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu khảo sát (tùy chọn)'}, render_value=False),
            'whitelist_emails': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'vd: user1@gmail.com\\nuser2@gmail.com'}),
            'allow_review_response': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_confirmation_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'one_response_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Tiêu đề',
            'description': 'Mô tả',
            'header_image': 'Ảnh tiêu đề (tùy chọn)',
            'is_active': 'Đang hoạt động',
            'expires_at': 'Hết hạn vào',
            'max_responses': 'Giới hạn số phản hồi',
            'password': 'Mật khẩu khảo sát',
            'whitelist_emails': 'Whitelist email (mỗi dòng 1 email)',
            'allow_review_response': 'Cho phép xem lại câu trả lời',
            'send_confirmation_email': 'Gửi email xác nhận',
            'one_response_only': 'Chỉ cho phép trả lời 1 lần',
        }
        help_texts = {
            'password': 'Để trống nếu không yêu cầu mật khẩu. Khi sửa, nhập giá trị mới để thay đổi.',
            'whitelist_emails': 'Chỉ các email này mới được tham gia và xuất kết quả (để trống nếu không giới hạn).',
            'allow_review_response': 'Cho phép người trả lời xem lại câu trả lời của mình sau khi gửi.',
            'send_confirmation_email': 'Gửi email cảm ơn đến người trả lời (chỉ hoạt động khi TẮT tính năng xem lại câu trả lời).',
            'one_response_only': 'Mỗi người chỉ được trả lời 1 lần. TẮT để cho phép trả lời nhiều lần.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].initial = ''


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'order', 'is_required']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Nhập nội dung câu hỏi'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'text': 'Nội dung câu hỏi',
            'question_type': 'Loại câu hỏi',
            'order': 'Thứ tự',
            'is_required': 'Bắt buộc',
        }

class ResponseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        survey = kwargs.pop('survey')
        super().__init__(*args, **kwargs)
        
        for question in survey.questions.all():
            if question.question_type == 'text':
                self.fields[f'question_{question.id}'] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                )
            elif question.question_type == 'single':
                options = question.options or []
                choices = [(idx, opt) for idx, opt in enumerate(options)]
                self.fields[f'question_{question.id}'] = forms.ChoiceField(
                    label=question.text,
                    required=question.is_required,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )
            elif question.question_type == 'multiple':
                options = question.options or []
                choices = [(idx, opt) for idx, opt in enumerate(options)]
                self.fields[f'question_{question.id}'] = forms.MultipleChoiceField(
                    label=question.text,
                    required=question.is_required,
                    choices=choices,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                )


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email của bạn'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên đăng nhập'}),
        }
        labels = {
            'username': 'Tên đăng nhập',
            'email': 'Email',
            'first_name': 'Tên',
            'last_name': 'Họ',
            'password1': 'Mật khẩu',
            'password2': 'Xác nhận mật khẩu',
        }
        help_texts = {
            'username': '',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Mật khẩu'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Xác nhận mật khẩu'})
        self.fields['password1'].label = 'Mật khẩu'
        self.fields['password2'].label = 'Xác nhận mật khẩu'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng!")
        return email


class UserProfileForm(forms.ModelForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email của bạn'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ'})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label='Ảnh đại diện'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
        labels = {
            'username': 'Tên đăng nhập',
            'email': 'Email',
            'first_name': 'Tên',
            'last_name': 'Họ',
        }
        help_texts = {
            'username': '',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile') and self.instance.profile.avatar:
            self.fields['avatar'].initial = self.instance.profile.avatar

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Email này đã được sử dụng!")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        avatar = self.cleaned_data.get('avatar')
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if avatar:
            profile.avatar = avatar
            profile.save()
        return user
