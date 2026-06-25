from django.contrib import admin
from .models import InterviewResponse, UserEvent, WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ["email", "source", "created_at"]
    list_filter = ["source"]
    search_fields = ["email"]
    readonly_fields = ["created_at"]


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ["user", "event", "meta", "created_at"]
    list_filter = ["event"]
    search_fields = ["user__email", "user__username", "event"]
    readonly_fields = ["user", "event", "meta", "created_at"]


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    list_display = ["user", "trigger", "response", "created_at"]
    list_filter = ["trigger"]
    search_fields = ["user__email", "response"]
    readonly_fields = ["user", "trigger", "prompt", "response", "meta", "created_at"]
