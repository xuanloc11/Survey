from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Survey, Question, Choice, Response, Answer


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'header_image', 'is_active', 'expires_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tiêu đề khảo sát'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Nhập mô tả khảo sát'}),
            'header_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'title': 'Tiêu đề',
            'description': 'Mô tả',
            'header_image': 'Ảnh tiêu đề (tùy chọn)',
            'is_active': 'Đang hoạt động',
            'expires_at': 'Hết hạn vào',
        }


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


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lựa chọn'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'text': 'Nội dung lựa chọn',
            'order': 'Thứ tự',
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
                choices = [(choice.id, choice.text) for choice in question.choices.all()]
                self.fields[f'question_{question.id}'] = forms.ChoiceField(
                    label=question.text,
                    required=question.is_required,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )
            elif question.question_type == 'multiple':
                choices = [(choice.id, choice.text) for choice in question.choices.all()]
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

