from django.utils import timezone
from rest_framework import serializers
from .models import Category, Petition, Response

class CategorySerializer(serializers.ModelSerializer):
    vote_threshold = serializers.IntegerField(min_value=1)

    class Meta:
        model = Category
        fields = ["id", "name", "max_years", "max_months", "max_days", "vote_threshold"]
        extra_kwargs = {
            "max_years": {"min_value": 0, "max_value": 100},
            "max_months": {"min_value": 0, "max_value": 11},
            "max_days": {"min_value": 0, "max_value": 366},
        }

    def validate(self, attrs):
        if self.instance is None and not all(key in attrs for key in ("max_years", "max_months", "max_days", "vote_threshold")):
            raise serializers.ValidationError("Вкажіть ліміт часу й поріг голосів категорії.")
        values = [attrs.get(key, getattr(self.instance, key, 0)) for key in ("max_years", "max_months", "max_days")]
        if not any(values):
            raise serializers.ValidationError("Ліміт категорії має бути більшим за нуль.")
        if attrs.get("vote_threshold", getattr(self.instance, "vote_threshold", None)) is None:
            raise serializers.ValidationError({"vote_threshold": "Вкажіть поріг голосів категорії."})
        return attrs

class ResponseSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True, allow_null=True)
    class Meta:
        model = Response
        fields = ["id", "text", "author", "published_at"]

class PetitionSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    vote_count = serializers.SerializerMethodField()
    vote_threshold = serializers.IntegerField(source="category.vote_threshold", read_only=True)
    official_response = ResponseSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Petition
        fields = ["id", "title", "text", "author", "category", "category_name", "status",
                  "deadline", "created_at", "status_changed_at", "moderation_reason",
                  "vote_count", "vote_threshold", "is_active", "official_response", "is_hidden"]
        read_only_fields = ["id", "author", "status", "deadline", "created_at", "status_changed_at",
                            "moderation_reason", "vote_count", "vote_threshold", "is_active", "official_response", "is_hidden"]

    def validate(self, attrs):
        if "vote_threshold" in self.initial_data:
            raise serializers.ValidationError({"vote_threshold": "Поріг голосів задається для категорії."})
        if "deadline" in self.initial_data:
            raise serializers.ValidationError({"deadline": "Термін автоматично визначається категорією."})
        if self.instance is None and attrs.get("category"):
            if attrs["category"].vote_threshold is None:
                raise serializers.ValidationError({"category": "Адміністратор ще не задав поріг голосів категорії."})
        return attrs

    def create(self, validated_data):
        validated_data["deadline"] = validated_data["category"].maximum_deadline(timezone.now())
        return super().create(validated_data)

    def get_vote_count(self, obj):
        count = getattr(obj, "vote_count", None)
        return count if count is not None else obj.votes.count()

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Заголовок не може бути порожнім.")
        return value.strip()

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Текст не може бути порожнім.")
        return value.strip()

