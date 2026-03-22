
from django.contrib import admin
#from .models import Question, Category, Answer
from questionnaire.models.models import Question, Category, Answer



@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'question_text', 
        'order',
        'short_description',
        'question_hint',
        'category',
        'level',
        'created_at'
    )
    search_fields = ('question_text', 'category__name')
    list_filter = ('category', 'level')

    def short_description(self, obj):
        return (obj.question_description[:30] + '...') if len(obj.question_description) > 30 else obj.question_description
    short_description.short_description = "Description"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "brainnode_order", "brainnode_question", "answer_text", "created_at")

    def brainnode_order(self, obj):
        return obj.brainnode.order if obj.brainnode else "-"
    brainnode_order.short_description = "Order"

    def brainnode_question(self, obj):
        return obj.brainnode.question_text if obj.brainnode else "(No question)"
    brainnode_question.short_description = "Question"

