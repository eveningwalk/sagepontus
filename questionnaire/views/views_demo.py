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

from questionnaire.device import landing_template_name
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


def landing(request):
    """
    GET /landing/ — 데모 전용 랜딩(시작) 페이지.
    데모 유저가 이미 로그인된 경우에도 항상 /demo/로 보내 새 세션을 시작한다.
    """
    if not getattr(settings, "DEMO_ENABLED", False):
        raise Http404("Demo is disabled.")
    demo_username = getattr(settings, "DEMO_USER_USERNAME", "")
    if demo_username and request.user.is_authenticated and request.user.get_username() == demo_username:
        response = redirect("demo")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response["Pragma"] = "no-cache"
        return response
    response = render(request, landing_template_name(request), {})
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


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
