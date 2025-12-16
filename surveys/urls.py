from django.urls import path
from . import views

app_name = 'surveys'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('profile/', views.profile_view, name='profile'),
    path('my-surveys/', views.survey_list, name='survey_list'),
    path('survey/create/', views.survey_create, name='survey_create'),
    path('survey/<int:pk>/', views.survey_detail, name='survey_detail'),
    path('survey/<int:pk>/edit/', views.survey_edit, name='survey_edit'),
    path('survey/<int:pk>/delete/', views.survey_delete, name='survey_delete'),
    path('survey/<int:pk>/take/', views.survey_take, name='survey_take'),
    path('survey/<int:pk>/results/', views.survey_results, name='survey_results'),
    path('survey/<int:pk>/export/csv/', views.survey_export_csv, name='survey_export_csv'),
    path('survey/<int:survey_pk>/question/add/', views.question_add, name='question_add'),
    path('question/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('question/<int:question_pk>/choice/add/', views.choice_add, name='choice_add'),
    # AJAX API endpoints
    path('api/survey/<int:survey_pk>/question/add/', views.question_add_ajax, name='question_add_ajax'),
    path('api/question/<int:pk>/update/', views.question_update_ajax, name='question_update_ajax'),
    path('api/question/<int:pk>/delete/', views.question_delete_ajax, name='question_delete_ajax'),
    path('api/survey/<int:survey_pk>/question/reorder/', views.question_reorder_ajax, name='question_reorder_ajax'),
    path('api/survey/<int:pk>/publish/', views.survey_publish_toggle_ajax, name='survey_publish_toggle_ajax'),
    path('api/question/<int:pk>/upload-image/', views.question_image_upload_ajax, name='question_image_upload_ajax'),
    path('api/question/<int:question_pk>/choice/add/', views.choice_add_ajax, name='choice_add_ajax'),
    path('api/choice/<int:pk>/delete/', views.choice_delete_ajax, name='choice_delete_ajax'),
]

