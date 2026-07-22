from django.urls import path
from . import views

urlpatterns = [
    path("auth/registrati/", views.register),
    path("auth/login/", views.login),
    path("profilo/", views.profile),
    path("percorso/", views.path_lessons),
    path("lezioni/<str:lesson_id>/", views.lesson_detail),
    path("lezioni/<str:lesson_id>/inizia/", views.start_lesson),
    path("lezioni/<str:lesson_id>/quesiti/<int:question_id>/verifica/", views.check_answer),
    path("lezioni/<str:lesson_id>/quiz-finale/", views.submit_final_quiz),
    path("progressi/", views.progress_list),
    path("admin/contenuti-mancanti/", views.content_gaps),
]
