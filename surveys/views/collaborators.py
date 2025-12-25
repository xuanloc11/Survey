from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Survey, SurveyCollaborator
from ..permissions import get_survey_access

User = get_user_model()


@login_required
def survey_collaborators(request, pk):
    survey = get_object_or_404(Survey, pk=pk, is_deleted=False)
    access = get_survey_access(request.user, survey)
    if not access.can_manage_collaborators:
        messages.error(request, "Bạn không có quyền quản lý cộng tác viên của khảo sát này.")
        return redirect("surveys:survey_detail", pk=survey.pk)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "add":
            identifier = (request.POST.get("user", "") or "").strip()
            role = (request.POST.get("role", "") or "").strip() or SurveyCollaborator.ROLE_VIEWER

            if role not in {SurveyCollaborator.ROLE_OWNER, SurveyCollaborator.ROLE_EDITOR, SurveyCollaborator.ROLE_VIEWER}:
                messages.error(request, "Vai trò không hợp lệ.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            if not identifier:
                messages.error(request, "Vui lòng nhập username hoặc email.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            user = (
                User.objects.filter(username=identifier).first()
                or User.objects.filter(email__iexact=identifier).first()
            )
            if not user:
                messages.error(request, "Không tìm thấy user theo username/email đã nhập.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            if user.id == survey.creator_id:
                messages.info(request, "Người tạo khảo sát mặc định là Owner.")
                SurveyCollaborator.objects.get_or_create(
                    survey=survey, user=user, defaults={"role": SurveyCollaborator.ROLE_OWNER}
                )
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            obj, created = SurveyCollaborator.objects.get_or_create(
                survey=survey, user=user, defaults={"role": role}
            )
            if not created:
                obj.role = role
                obj.save(update_fields=["role"])
                messages.success(request, "Đã cập nhật vai trò cộng tác viên.")
            else:
                messages.success(request, "Đã thêm cộng tác viên.")

            return redirect("surveys:survey_collaborators", pk=survey.pk)

        if action == "update":
            collab_id = request.POST.get("collab_id")
            role = (request.POST.get("role", "") or "").strip()
            if role not in {SurveyCollaborator.ROLE_OWNER, SurveyCollaborator.ROLE_EDITOR, SurveyCollaborator.ROLE_VIEWER}:
                messages.error(request, "Vai trò không hợp lệ.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            collab = get_object_or_404(SurveyCollaborator, pk=collab_id, survey=survey)
            if collab.user_id == survey.creator_id:
                messages.error(request, "Không thể thay đổi vai trò của người tạo khảo sát.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            collab.role = role
            collab.save(update_fields=["role"])
            messages.success(request, "Đã cập nhật vai trò.")
            return redirect("surveys:survey_collaborators", pk=survey.pk)

        if action == "remove":
            collab_id = request.POST.get("collab_id")
            collab = get_object_or_404(SurveyCollaborator, pk=collab_id, survey=survey)
            if collab.user_id == survey.creator_id:
                messages.error(request, "Không thể xóa người tạo khảo sát khỏi danh sách Owner.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            # Prevent removing the last owner (consider creator as owner)
            owner_count = SurveyCollaborator.objects.filter(survey=survey, role=SurveyCollaborator.ROLE_OWNER).count()
            if collab.role == SurveyCollaborator.ROLE_OWNER and owner_count <= 1:
                messages.error(request, "Không thể xóa Owner cuối cùng của khảo sát.")
                return redirect("surveys:survey_collaborators", pk=survey.pk)

            collab.delete()
            messages.success(request, "Đã xóa cộng tác viên.")
            return redirect("surveys:survey_collaborators", pk=survey.pk)

        messages.error(request, "Thao tác không hợp lệ.")
        return redirect("surveys:survey_collaborators", pk=survey.pk)

    collaborators = (
        SurveyCollaborator.objects.filter(survey=survey)
        .select_related("user")
        .order_by("role", "user__username")
    )

    return render(
        request,
        "surveys/survey_management/survey_collaborators.html",
        {
            "survey": survey,
            "collaborators": collaborators,
            "ROLE_OWNER": SurveyCollaborator.ROLE_OWNER,
            "ROLE_EDITOR": SurveyCollaborator.ROLE_EDITOR,
            "ROLE_VIEWER": SurveyCollaborator.ROLE_VIEWER,
        },
    )


