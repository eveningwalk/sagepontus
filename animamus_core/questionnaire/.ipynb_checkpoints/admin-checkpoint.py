from django.contrib import admin
from .models import (
    ResponseSet, Response,
    Category, Question
)

'''
from .models import (
    Topic, Prompt, PromptFlow,
    AnswerSet, Answer,
    ResponseSet, Response,
    Category, Question
)
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('prompt_id', 'topic', 'step')
    list_filter = ('topic',)
    search_fields = ('prompt_id', 'text')

@admin.register(PromptFlow)
class PromptFlowAdmin(admin.ModelAdmin):
    list_display = ('topic', 'current_prompt', 'next_prompt', 'condition')
    list_filter = ('topic',)

@admin.register(AnswerSet)
class AnswerSetAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'topic', 'created_at')
    list_filter = ('topic', 'created_at')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('prompt', 'answer_set', 'created_at')
    search_fields = ('answer_text',)
'''
@admin.register(ResponseSet)
class ResponseSetAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'created_at')

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('question_id', 'response_set', 'created_at')
    search_fields = ('answer', 'question_id')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('category', 'order', 'text')
    search_fields = ('text', 'guidance')
