# questionnaire/models_braintree.py
from django.conf import settings
from django.db import models
from django.utils import timezone
#from treebeard.mp_tree import MP_Node


from django.contrib.auth.models import User
from mptt.models import MPTTModel, TreeForeignKey

class BrainTree(models.Model):
    """
    사용자의 전체 브레인트리
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="braintrees")
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class BrainBlockNode(MPTTModel):
    """
    트리 구조의 Block 단위 (공통 → 도메인 → AI 생성형 등)
    """
    #braintree = models.ForeignKey(BrainTree, on_delete=models.CASCADE, related_name="blocks")
    braintree = models.ForeignKey(   # ← 이름 변경
        "BrainTree",
        on_delete=models.CASCADE,
        related_name="blocks"
    )
    title = models.CharField(max_length=200)

    parent = TreeForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children"
    )

    description = models.TextField(blank=True, null=True)
    type = models.CharField(
        max_length=20,
        choices=(("common", "공통"), ("domain", "도메인"), ("ai", "AI 생성형")),
        default="common"
    )
    order = models.PositiveIntegerField(default=0)

    class MPTTMeta:
        order_insertion_by = ["order"]

    def __str__(self):
        return f"{self.title} ({self.braintree.title})"


class BrainNode(MPTTModel):
    """
    질문/답변 단위 노드
    - Block 하위에서 계층형으로 구성됨
    """
    block = models.ForeignKey(
        "BrainBlockNode",
        on_delete=models.CASCADE,
        related_name="brainnodes",
        null=True,
        blank=True
    )
    
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )
    question_text = models.TextField(blank=True, default="")
    answer_text = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class MPTTMeta:
        order_insertion_by = ["order"]

    def __str__(self):
        return f"Node#{self.id} [{self.order}] {self.question_text[:30]}..."


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
