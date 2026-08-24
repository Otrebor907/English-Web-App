from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Ogni URL che il frontend chiama con /api/... (vedi API_URL in
    # frontend/src/api.js) arriva qui e viene passato a learning/urls.py,
    # che definisce le rotte specifiche (es. auth/login/).
    path("api/", include("learning.urls")),
]

