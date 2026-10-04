from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("petitions.urls")),
    path("api/", include("voting.urls")),
    path("", lambda request: JsonResponse({"name": "ProstoPetition API", "version": 1})),
]

