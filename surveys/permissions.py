from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth.models import AnonymousUser

from .models import Survey, SurveyCollaborator


@dataclass(frozen=True)
class SurveyAccess:
    role: Optional[str]

    @property
    def is_owner(self) -> bool:
        return self.role == SurveyCollaborator.ROLE_OWNER

    @property
    def is_editor(self) -> bool:
        return self.role == SurveyCollaborator.ROLE_EDITOR

    @property
    def is_viewer(self) -> bool:
        return self.role == SurveyCollaborator.ROLE_VIEWER

    @property
    def can_edit(self) -> bool:
        return self.is_owner or self.is_editor

    @property
    def can_view_results(self) -> bool:
        return self.is_owner or self.is_editor or self.is_viewer

    @property
    def can_publish(self) -> bool:
        return self.is_owner

    @property
    def can_delete(self) -> bool:
        return self.is_owner

    @property
    def can_manage_collaborators(self) -> bool:
        return self.is_owner


def get_survey_access(user, survey: Survey) -> SurveyAccess:

    if not user or isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return SurveyAccess(role=None)

    if survey.creator_id == user.id:
        return SurveyAccess(role=SurveyCollaborator.ROLE_OWNER)

    role = (
        SurveyCollaborator.objects.filter(survey=survey, user=user)
        .values_list("role", flat=True)
        .first()
    )
    return SurveyAccess(role=role)


