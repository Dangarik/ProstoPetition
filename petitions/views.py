from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Category, Petition
from .serializers import CategorySerializer, PetitionSerializer, ResponseSerializer
from .services import PetitionConflict, change_status, publish_response, reconcile_category_threshold, expire_petitions, set_petition_visibility

def petition_queryset():
    expire_petitions()
    return Petition.objects.select_related("author", "category", "official_response", "official_response__author").annotate(vote_count=Count("votes"))

class PetitionListCreate(generics.ListCreateAPIView):
    serializer_class = PetitionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = petition_queryset().filter(is_hidden=False)
        if not self.request.user.is_staff:
            qs = qs.filter(status__in=Petition.PUBLIC_STATUSES)
        status_value = self.request.query_params.get("status")
        if status_value:
            if status_value not in Petition.Status.values:
                raise ValidationError({"status": "Невідомий статус."})
            qs = qs.filter(status=status_value)
        category = self.request.query_params.get("category")
        if category:
            if not category.isdecimal():
                raise ValidationError({"category": "Очікується ідентифікатор категорії."})
            qs = qs.filter(category_id=int(category))
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(text__icontains=search))
        ordering = self.request.query_params.get("ordering", "-created_at")
        allowed = {"created_at", "-created_at", "title", "-title", "vote_count", "-vote_count"}
        if ordering not in allowed:
            raise ValidationError({"ordering": "Доступні created_at, title, vote_count із необов’язковим префіксом -."})
        return qs.order_by(ordering, "id")

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class PetitionDetail(generics.RetrieveDestroyAPIView):
    serializer_class = PetitionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = petition_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(Q(status__in=Petition.PUBLIC_STATUSES, is_hidden=False) | Q(author=user))
        return qs.filter(status__in=Petition.PUBLIC_STATUSES, is_hidden=False)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Потрібна авторизація.")
        with transaction.atomic():
            petition = get_object_or_404(Petition.objects.select_for_update(), pk=kwargs["pk"])
            if petition.author_id != request.user.id:
                raise PermissionDenied("Видаляти можна лише власну петицію.")
            if petition.status in (Petition.Status.IN_REVIEW, Petition.Status.ANSWERED, Petition.Status.CLOSED):
                raise PetitionConflict("Петицію вже передано на розгляд.")
            if petition.votes.exists():
                raise PetitionConflict("Петицію з голосами видалити неможливо.")
            petition.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CategoryListCreate(generics.ListCreateAPIView):
    queryset = Category.objects.order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_permissions(self):
        return [IsAdminUser()] if self.request.method == "POST" else [AllowAny()]

class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    http_method_names = ["get", "patch", "delete"]
    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAdminUser()]
    def perform_update(self, serializer):
        category = serializer.save()
        reconcile_category_threshold(category.pk)
    def perform_destroy(self, instance):
        if instance.petitions.exists():
            raise PetitionConflict("Категорію використовують петиції.")
        try:
            instance.delete()
        except ProtectedError:
            raise PetitionConflict("Категорію використовують петиції.")

class ModerationList(generics.ListAPIView):
    serializer_class = PetitionSerializer
    permission_classes = [IsAdminUser]
    def get_queryset(self):
        qs = petition_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            if status_value not in Petition.Status.values:
                raise ValidationError({"status": "Невідомий статус."})
            qs = qs.filter(status=status_value)
        return qs.order_by("-created_at")

class VisibilityView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        get_object_or_404(Petition, pk=pk)
        is_hidden = request.data.get("is_hidden")
        if not isinstance(is_hidden, bool):
            raise ValidationError({"is_hidden": "Очікується true або false."})
        petition = set_petition_visibility(pk, is_hidden)
        return Response(PetitionSerializer(petition_queryset().get(pk=petition.pk)).data)

class StatusView(APIView):
    permission_classes = [IsAdminUser]
    def patch(self, request, pk):
        get_object_or_404(Petition, pk=pk)
        new_status = request.data.get("status")
        reason = request.data.get("reason", "")
        if new_status not in Petition.Status.values:
            raise ValidationError({"status": "Невідомий статус."})
        if not isinstance(reason, str):
            raise ValidationError({"reason": "Причина має бути текстом."})
        if "vote_threshold" in request.data:
            raise ValidationError({"vote_threshold": "Поріг голосів змінюють у категорії."})
        petition = change_status(pk, new_status, reason)
        return Response(PetitionSerializer(petition_queryset().get(pk=petition.pk)).data)

class OfficialResponseView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk):
        get_object_or_404(Petition, pk=pk)
        text = request.data.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValidationError({"text": "Текст відповіді є обов’язковим."})
        response = publish_response(pk, request.user, text.strip())
        return Response(ResponseSerializer(response).data, status=201)

class StatisticsView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        expire_petitions()
        counts = dict(Petition.objects.values("status").annotate(count=Count("id")).values_list("status", "count"))
        from django.contrib.auth import get_user_model
        from voting.models import Vote
        return Response({
            "users": get_user_model().objects.count(),
            "petitions": Petition.objects.count(),
            "votes": Vote.objects.count(),
            "by_status": {value: counts.get(value, 0) for value in Petition.Status.values},
        })




