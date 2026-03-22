"""
공개 데모 진입: 비로그인 방문자를 데모 전용 계정으로 세션 로그인한 뒤
새 BrainTree를 만들고 질문 흐름으로 보냄.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from questionnaire.models.models_braintree import BrainTree, BrainBlockNode


def _get_or_create_demo_user() -> User:
    username = getattr(settings, "DEMO_USER_USERNAME", "demo_gov_evaluator")
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": "demo@example.invalid",
            "is_active": True,
        },
    )
    if created or not user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def demo_landing(request):
    """
    GET / — 데모가 켜져 있을 때 비로그인 방문자에게 보이는 첫 화면(로그인 없음).
    「데모 시작」으로 /demo/ 진입.
    """
    if not getattr(settings, "DEMO_ENABLED", False):
        raise Http404("Demo is disabled.")
    return render(request, "questionnaire/demo_landing.html", {})


def demo_entry(request):
    """
    GET /demo/ — 로그인 폼 없이 데모 세션 시작.
    """
    if not getattr(settings, "DEMO_ENABLED", False):
        raise Http404("Demo is disabled.")

    if request.method != "GET":
        return HttpResponseForbidden("GET only.")

    demo_user = _get_or_create_demo_user()
    login(request, demo_user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["demo_mode"] = True
    request.session.modified = True

    suffix = timezone.now().strftime("%Y%m%d-%H%M%S")
    short = str(uuid.uuid4())[:8]
    title = f"정부과제 데모 시연 ({suffix}-{short})"

    new_tree = BrainTree.objects.create(user=demo_user, title=title)

    root_node = BrainBlockNode.objects.create(
        parent=None,
        braintree=new_tree,
        title="Root 노드",
        type="common",
        description="데모 트리의 시작점입니다.",
        order=1,
    )

    return redirect(
        "questionnaire:show_question_step",
        category="common",
        order=root_node.order,
        block_id=root_node.id,
    )
