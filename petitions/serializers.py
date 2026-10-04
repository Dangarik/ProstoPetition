from django.utils import timezone
from rest_framework import serializers
from .models import Category, Petition, Response

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]

class ResponseSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True, allow_null=True)
    class Meta:
        model = Response
        fields = ["id", "text", "author", "published_at"]

class PetitionSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    vote_count = serializers.IntegerField(read_only=True)
    official_response = ResponseSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Petition
        fields = ["id", "title", "text", "author", "category", "category_name", "status",
                  "deadline", "created_at", "status_changed_at", "moderation_reason",
                  "vote_count", "is_active", "official_response"]
        read_only_fields = ["id", "author", "status", "created_at", "status_changed_at",
                            "moderation_reason", "vote_count", "is_active", "official_response"]

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Дата завершення має бути в майбутньому.")
        return value

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Заголовок не може бути порожнім.")
        return value.strip()

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Текст не може бути порожнім.")
        return value.strip()

