# questionnaire/admin_braintree.py
from django.contrib import admin
from questionnaire.models.models_braintree import PolicyPlan, UserPolicy, BrainTree, BrainBlockNode, BrainNode, PromptArtifact
from treebeard.admin import TreeAdmin
from treebeard.forms import MoveNodeForm
from questionnaire.models.models import Question,Category, Answer


from mptt.admin import DraggableMPTTAdmin

@admin.register(PolicyPlan)
class PolicyPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "max_brain_trees", "max_depth", "max_width", "created_at")
    search_fields = ("name", "code")

@admin.register(UserPolicy)
class UserPolicyAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "started_at")
    search_fields = ("user__username", "plan__name")




@admin.register(BrainTree)
class BrainTreeAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at")
    search_fields = ("title", "user__username")

class BrainNodeInline(admin.TabularInline):
    """
    BrainBlockNode 상세 화면에서 BrainNode들을 같이 관리
    """
    model = BrainNode
    extra = 1   # 기본으로 보여줄 빈 폼 개수
    fields = ("question_text", "answer_text", "order", "parent")
    readonly_fields = ("order",)  # 순서 자동화 시 수정 방지

    show_change_link = True

@admin.register(BrainBlockNode)
class BrainBlockNodeAdmin(DraggableMPTTAdmin):
    """
    Block 트리 구조 관리 + Block 안의 BrainNode들 Inline 관리
    """
    mptt_indent_field = "title"
    list_display = ("indented_title", "braintree", "title", "type", "order", "level")
    #list_display = ("indented_title", "name", "type", "order")
    list_filter = ("braintree", "type")
    #list_filter = ("type")
    search_fields = ("title", "description")

    inlines = [BrainNodeInline]  # ✅ Block 화면에서 Node 같이 관리

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ("question", "answer_text", "created_at")
    readonly_fields = ("created_at",)
    
@admin.register(BrainNode)
class BrainNodeAdmin(DraggableMPTTAdmin):
    """
    질문/답변 단위도 독립적으로 트리 관리 가능
    """
    #mptt_level_indent = 0  # 들여쓰기 없애기
    mptt_indent_field = "question_text"
    #list_display = ("indented_title", "block", "question_text", "answer_text", "order", 'level')
    list_display = ("indented_title", "block", "order", 'level')
    list_filter = ("block__braintree",)
    search_fields = ("question_text", "answer_text")

    inlines = [AnswerInline]


@admin.register(PromptArtifact)
class PromptArtifactAdmin(admin.ModelAdmin):
    list_display = ("id", "node", "version", "created_at")
    search_fields = ("prompt_input", "output_summary")
