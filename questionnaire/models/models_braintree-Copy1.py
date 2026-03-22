# questionnaire/models_braintree.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from treebeard.mp_tree import MP_Node


class BrainTree(models.Model):
    """
    한 사용자가 생성하는 '생각 트리' 단위.
    - 첫 BrainNode(루트)로부터 하위 노드들이 상속/분기되며 누적 컨텍스트를 형성
    """
    STATUS_CHOICES = [
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brain_trees")
    title = models.CharField(max_length=120, default="Untitled BrainTree")
    
    domain = models.CharField(
        max_length=40,
        choices=[
            ("marketing", "Marketing"),
            ("content_creation", "Content Creation"),
            ("efficiency", "Efficiency"),
            ("business_growth", "Business Growth"),
            ("common", "Common"),
        ],
    )
    persona = models.CharField(max_length=80, blank=True, default="")  # 선택: 'solo_founder', 'pm' 등
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="active")

    # 진행도/메타
    current_depth = models.PositiveIntegerField(default=1)
    node_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["domain"]),
        ]

    def __str__(self):
        return f"[{self.user}] {self.title} ({self.domain})"

#class BrainBlockNode(models.Model):
class BrainBlockNode(MP_Node):
    tree = models.ForeignKey(BrainTree, on_delete=models.CASCADE, related_name="blocks")
    title = models.CharField(max_length=200)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    depth = models.PositiveIntegerField(default=0)

    
    description = models.TextField(blank=True, null=True)
    type = models.CharField(
        max_length=20,
        choices=(("common", "공통"), ("domain", "도메인"), ("ai", "AI 생성형"))
    )
    order = models.IntegerField(default=0)
    class MPTTMeta:
        order_insertion_by = ['title']


    def __str__(self):
        return f"{self.title} ({self.tree.title})"
    
from mptt.models import MPTTModel, TreeForeignKey
from mptt.models import MPTTModel, TreeForeignKey

class BrainNode(MPTTModel):
    """
    BrainTree 내 질문/답변 단위 노드
    - MPTT를 통해 트리 구조 형성
    - block은 도메인 블록에 속함
    """

    block = models.ForeignKey(
        BrainBlockNode,
        on_delete=models.CASCADE,
        related_name="brainnodes",
        null=True,
        blank=True
    )

    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    question_text = models.TextField(blank=True, default="")
    answer_text = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class MPTTMeta:
        order_insertion_by = ['order']

    def __str__(self):
        return f"BrainNode#{self.id} [{self.order}] {self.question_text[:30]}..."

'''

class BrainNode(models.Model): #Question level
    """
    BrainTree 내 개별 노드 (질문/답변/프롬프트 스냅샷을 담는 핵심 단위)
    - parent를 통해 트리 구조 형성
    - depth는 가드레일(정책) 체크용
    """
    #tree = models.ForeignKey(BrainTree, on_delete=models.CASCADE, related_name="nodes") # 이 노드가 속한 BrainTree
    #parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children") #상위 노드. 없으면 루트 노드
    block = models.ForeignKey(BrainBlockNode, on_delete=models.CASCADE, related_name="brainnodes", null=True, blank=True)
    question_text = models.TextField(blank=True, default = "")
    answer = models.TextField(blank=True, default = "") #사용자가 기록한 응답
    order = models.PositiveIntegerField(default=0) # 같은 depth 내에서의 순서 지정
    
    #step = models.ForeignKey("Step", on_delete=models.CASCADE, null=True, blank=True) #질문이 무엇이었는지
    #depth = models.PositiveIntegerField(default=1)     # 루트=1 트리 내 깊이. 
    
    #title = models.CharField(max_length=150, blank=True, default="")  # 선택: 노드 주제(예: 'SNS 자동화'), 노드의 주제 또는 제목
    
    inherited_context = models.TextField(blank=True, default="") # 상속된 컨텍스트 요약본(짧게 압축 저장해서 LLM prompt에 주입)

    # 스냅샷: 이 노드가 생성될 당시의 공통+도메인 질문 리스트(프롬프트 재현성을 위해)
    questions_snapshot = models.JSONField(default=list)  # [{"id":..,"question_text":..}, ...]

    # 사용자가 입력한 답변(한 노드에 Q 여러개 → 답변도 여러개)
    # → 별도의 Answer 모델로 분리 (아래)
    # 프롬프트 산출물도 별도 모델(아래 PromptArtifact)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BrainNode#{self.id} [{self.order}] {self.question_text[:30]}..."

'''


class PolicyPlan(models.Model):
    """
    요금제/정책 정의 (예: Basic, Pro, Premium)
    - BrainTree 최대 생성 수 등 제한을 정의
    """
    code = models.SlugField(unique=True)  # 'basic', 'pro', 'premium'
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    max_brain_trees = models.PositiveIntegerField(default=1)
    max_depth = models.PositiveIntegerField(default=4)     # BrainTree 최대 깊이 (가드레일)
    max_width = models.PositiveIntegerField(default=8)     # 동일 depth에서의 최대 분기 수(선택)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (max_trees={self.max_brain_trees})"


class UserPolicy(models.Model):
    """
    유저별 적용되는 정책(요금제).
    - 단순화를 위해 현재 적용 중인 단일 정책만 관리 (구독 이력은 추후 확장)
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="policy")
    plan = models.ForeignKey(PolicyPlan, on_delete=models.PROTECT, related_name="users")
    started_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} → {self.plan}"


class PromptArtifact(models.Model):
    """
    각 노드에서 생성된 프롬프트/결과물 스냅샷(버전 가능)
    - prompt_input: LLM에 넣은 실제 프롬프트(컨텍스트+지시문 포함)
    - output_summary: 모델 응답 요약(전체 응답은 별도 저장하거나 파일/장문은 스토리지로)
    - version: 동일 노드에서 프롬프트를 재생성할 때 버전 증가
    """
    node = models.ForeignKey(BrainNode, on_delete=models.CASCADE, related_name="artifacts")
    version = models.PositiveIntegerField(default=1)

    prompt_input = models.TextField()        # LLM에 전달된 최종 프롬프트
    output_summary = models.TextField(blank=True, default="")  # 응답 요약
    output_raw = models.TextField(blank=True, default="")      # 전체 응답(선택)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("node", "version")]
        ordering = ["-version"]

    def __str__(self):
        return f"Artifact node={self.node_id} v={self.version}"
