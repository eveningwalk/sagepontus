from django.contrib import admin
from .models import EarlyAccessSignup, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "supervisor_email")
    search_fields = ("user__username", "supervisor_email")


@admin.register(EarlyAccessSignup)
class EarlyAccessSignupAdmin(admin.ModelAdmin):
    list_display = ('email', 'industry', 'created_at', 'is_approved')
    list_filter = ('industry', 'is_approved')
    search_fields = ('email',)
    list_editable = ('is_approved',)
