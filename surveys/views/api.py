import json

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from ..models import Survey, Question
from ..permissions import get_survey_access


@login_required
@require_http_methods(["POST"])
def question_add_ajax(request, survey_pk):
    survey = get_object_or_404(Survey, pk=survey_pk, is_deleted=False)
    access = get_survey_access(request.user, survey)
    if not access.can_edit:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)

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
    question = get_object_or_404(Question, pk=pk)

    access = get_survey_access(request.user, question.survey)
    if not access.can_edit:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)

    try:
        data = json.loads(request.body)
        question.text = data.get('text', question.text)
        question.question_type = data.get('question_type', question.question_type)
        question.order = data.get('order', question.order)
        question.is_required = data.get('is_required', question.is_required)
        question.subtitle = data.get('subtitle', question.subtitle)
        question.media_url = data.get('media_url', question.media_url)

        if 'choices' in data or 'options' in data:
            options_data = data.get('choices', []) or data.get('options', [])
            question.options = [opt.strip() for opt in options_data if opt and opt.strip()]
        if getattr(question, 'correct_answers', None):
            question.correct_answers = []

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
                'correct_answers': [],  # quiz disabled
                'subtitle': question.subtitle,
                'media_url': question.media_url
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_delete_ajax(request, pk):
    question = get_object_or_404(Question, pk=pk)

    access = get_survey_access(request.user, question.survey)
    if not access.can_edit:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)

    try:
        question.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def question_reorder_ajax(request, survey_pk):
    survey = get_object_or_404(Survey, pk=survey_pk, is_deleted=False)
    access = get_survey_access(request.user, survey)
    if not access.can_edit:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)

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
    survey = get_object_or_404(Survey, pk=pk, is_deleted=False)
    access = get_survey_access(request.user, survey)
    if not access.can_publish:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)
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
    question = get_object_or_404(Question, pk=pk)

    access = get_survey_access(request.user, question.survey)
    if not access.can_edit:
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
    question = get_object_or_404(Question, pk=question_pk)

    access = get_survey_access(request.user, question.survey)
    if not access.can_edit:
        return JsonResponse({'success': False, 'error': 'Không có quyền'}, status=403)

    try:
        data = json.loads(request.body)
        option_text = data.get('text', '').strip()

        if not option_text:
            return JsonResponse({'success': False, 'error': 'Vui lòng nhập nội dung lựa chọn!'}, status=400)

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
    question = get_object_or_404(Question, pk=pk)

    access = get_survey_access(request.user, question.survey)
    if not access.can_edit:
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


