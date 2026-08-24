from django.urls import path
from . import views

urlpatterns = [
    # Endpoint chiamati da AuthPage (frontend/src/App.jsx) quando l'utente invia
    # il form: rispettivamente per registrazione e per login. Nessun middleware
    # di autenticazione blocca queste due rotte, perché servono anche a chi
    # non ha ancora un account/token (vedi permission_classes AllowAny nelle view).
    path("auth/registrati/", views.register),
    path("auth/login/", views.login),
    path("auth/password/", views.change_password),
    path("profilo/", views.profile),
    path("percorso/", views.path_lessons),
    path("lezioni/indice/", views.lesson_index),
    path("lezioni/<str:lesson_id>/", views.lesson_detail),
    path("lezioni/<str:lesson_id>/assegna/", views.lesson_assignment),
    path("lezioni/<str:lesson_id>/inizia/", views.start_lesson),
    path("lezioni/<str:lesson_id>/quiz/<str:modalita>/quesiti/<int:question_id>/verifica/", views.check_answer),
    path("lezioni/<str:lesson_id>/quiz-finale/", views.submit_final_quiz),
    path("progressi/", views.progress_list),
    path("admin/contenuti-mancanti/", views.content_gaps),
]
