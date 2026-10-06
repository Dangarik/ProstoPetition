from django import forms
from django.contrib import admin
from django.utils import timezone
from .models import Category, Petition, Response
from .services import TRANSITIONS, PetitionConflict, change_status, publish_response, reconcile_category_threshold, expire_petitions, set_petition_visibility

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "vote_threshold", "max_years", "max_months", "max_days")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and "vote_threshold" in form.changed_data:
            reconcile_category_threshold(obj.pk)

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
            if target == Petition.Status.REJECTED and not (data.get("moderation_reason") or "").strip():
                self.add_error("moderation_reason", "Причина є обов’язковою.")
            if target == Petition.Status.ACTIVE and current.deadline <= timezone.now():
                self.add_error("status", "Термін петиції вже завершився.")
            if target == Petition.Status.ACTIVE and current.category.vote_threshold is None:
                self.add_error("status", "Спочатку вкажіть поріг голосів для категорії.")
        return data

@admin.register(Petition)
class PetitionAdmin(admin.ModelAdmin):
    form = PetitionAdminForm

    def get_queryset(self, request):
        expire_petitions()
        return super().get_queryset(request)
    list_display = ("title", "author", "category", "status", "is_hidden", "deadline", "created_at", "vote_count")
    list_filter = ("status", "is_hidden", "category")
    actions = ("hide_petitions", "restore_petitions")
    search_fields = ("title", "text", "author__username")
    readonly_fields = ("author", "category", "title", "text", "deadline", "created_at", "status_changed_at", "is_hidden")

    def get_fields(self, request, obj=None):
        if obj:
            return ("title", "text", "author", "category", "deadline", "created_at",
                    "status", "moderation_reason", "status_changed_at", "is_hidden")
        return ("title", "text", "author", "category", "deadline")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else ("deadline", "created_at", "status_changed_at")

    def vote_count(self, obj):
        return obj.votes.count()

    def update_visibility(self, request, queryset, is_hidden):
        for petition_id in queryset.values_list("pk", flat=True):
            try:
                set_petition_visibility(petition_id, is_hidden)
            except PetitionConflict as error:
                self.message_user(request, str(error.detail), level="error")

    @admin.action(description="Приховати прострочені та відхилені петиції", permissions=["change"])
    def hide_petitions(self, request, queryset):
        self.update_visibility(request, queryset, True)

    @admin.action(description="Повернути зі схованих", permissions=["change"])
    def restore_petitions(self, request, queryset):
        self.update_visibility(request, queryset, False)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.status = Petition.Status.MODERATION
            obj.deadline = obj.category.maximum_deadline(timezone.now())
            obj.save()
        elif "status" in form.changed_data:
            saved = change_status(obj.pk, obj.status, obj.moderation_reason)
            obj.status = saved.status
            obj.status_changed_at = saved.status_changed_at

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

