from django import forms
from django.contrib import admin
from django.utils import timezone
from .models import Category, Petition, Response
from .services import TRANSITIONS, change_status, publish_response

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)

class PetitionAdminForm(forms.ModelForm):
    class Meta:
        model = Petition
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if self.instance.pk and "status" in self.changed_data:
            current = Petition.objects.get(pk=self.instance.pk)
            target = data.get("status")
            if target not in TRANSITIONS.get(current.status, set()):
                self.add_error("status", "Недозволений перехід стану.")
            if target in (Petition.Status.REJECTED, Petition.Status.HIDDEN) and not (data.get("moderation_reason") or "").strip():
                self.add_error("moderation_reason", "Причина є обов’язковою.")
            if target == Petition.Status.ACTIVE and current.deadline <= timezone.now():
                self.add_error("status", "Термін петиції вже завершився.")
        return data

@admin.register(Petition)
class PetitionAdmin(admin.ModelAdmin):
    form = PetitionAdminForm
    list_display = ("title", "author", "category", "status", "deadline", "created_at", "vote_count")
    list_filter = ("status", "category")
    search_fields = ("title", "text", "author__username")
    readonly_fields = ("author", "category", "title", "text", "deadline", "created_at", "status_changed_at")

    def get_fields(self, request, obj=None):
        if obj:
            return ("title", "text", "author", "category", "deadline", "created_at",
                    "status", "moderation_reason", "status_changed_at")
        return ("title", "text", "author", "category", "deadline")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else ("created_at", "status_changed_at")

    def vote_count(self, obj):
        return obj.votes.count()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.status = Petition.Status.MODERATION
            obj.save()
        elif "status" in form.changed_data:
            change_status(obj.pk, obj.status, obj.moderation_reason)

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("petition", "author", "published_at")
    readonly_fields = ("author", "published_at")
    fields = ("petition", "text", "author", "published_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        saved = publish_response(obj.petition_id, request.user, obj.text)
        obj.pk = saved.pk
        obj.author = saved.author
        obj.published_at = saved.published_at

