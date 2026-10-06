from django.urls import path
from . import views

urlpatterns = [
    path("categories/", views.CategoryListCreate.as_view()),
    path("categories/<int:pk>/", views.CategoryDetail.as_view()),
    path("petitions/", views.PetitionListCreate.as_view()),
    path("petitions/<int:pk>/", views.PetitionDetail.as_view()),
    path("petitions/<int:pk>/status/", views.StatusView.as_view()),
    path("petitions/<int:pk>/visibility/", views.VisibilityView.as_view()),
    path("petitions/<int:pk>/response/", views.OfficialResponseView.as_view()),
    path("admin/petitions/", views.ModerationList.as_view()),
    path("admin/statistics/", views.StatisticsView.as_view()),
]

