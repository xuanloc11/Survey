"""
Public views API.

This package re-exports all view callables used by `surveys/urls.py` and the
project-level error handlers (e.g. `surveys.views.custom_404`).
"""

# Auth & account
from .auth import (  # noqa: F401
    register_view,
    activate_account,
    login_view,
    logout_view,
    password_reset_request,
    password_reset_confirm,
    profile_view,
)

# Public pages
from .pages import (  # noqa: F401
    home,
    dashboard,
)

# Survey management (creator)
from .survey import (  # noqa: F401
    survey_list,
    survey_create,
    survey_edit,
    survey_detail,
    survey_detail_token,
    survey_delete,
)

# Collaborators / roles (owner only)
from .collaborators import (  # noqa: F401
    survey_collaborators,
)

# Question & choice management (creator)
from .questions import (  # noqa: F401
    question_add,
    question_edit,
    question_delete,
    choice_add,
)

# Taking survey (public)
from .take import (  # noqa: F401
    survey_take,
    survey_take_token,
    survey_edit_token,
    survey_review_response,
    survey_thankyou,
)

# Results & export (creator)
from .results import (  # noqa: F401
    survey_results,
    survey_export_csv,
    survey_export_excel,
)

# AJAX endpoints (creator)
from .api import (  # noqa: F401
    question_add_ajax,
    question_update_ajax,
    question_delete_ajax,
    question_reorder_ajax,
    survey_publish_toggle_ajax,
    question_image_upload_ajax,
    choice_add_ajax,
    choice_delete_ajax,
)

# Error handlers
from .errors import (  # noqa: F401
    custom_404,
    custom_500,
    custom_502,
    custom_404_preview,
)


