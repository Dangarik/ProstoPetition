from django.urls import path
from .views import VoteView

urlpatterns = [path("petitions/<int:pk>/vote/", VoteView.as_view())]

