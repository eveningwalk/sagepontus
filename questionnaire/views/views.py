import json
import logging

from django.conf import settings
from django.contrib import messages
import json as _json
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from questionnaire.models.models import Question,Category, Answer
from django.contrib.auth.decorators import login_required

from questionnaire.models.models_braintree import BrainTree, BrainBlockNode, BrainNode
from questionnaire.demo_config import get_demo_default_answer, pick_demo_domain_category_name
from questionnaire.prompts import run_prompt_generation_pair
from questionnaire.prompts.service import generate_ai_followup_questions, _chat_generate_with_usage, autofill_answers_from_brain_dump
from questionnaire.device import landing_template_name

logger = logging.getLogger(__name__)


def _is_demo_session(request) -> bool:
    return bool(
        request.session.get("demo_mode")
        and request.user.is_authenticated
        and request.user.get_username()
        == getattr(settings, "DEMO_USER_USERNAME", "")
    )


def _demo_flow_template(request, base_name: str) -> str:
    """데모 세션: 카톡·인앱 브라우저용 모바일 레이아웃(*_mobile.html)."""
    if _is_demo_session(request):
        return f"questionnaire/test/{base_name}_mobile.html"
    return f"questionnaire/test/{base_name}.html"


def root(request):
    if request.user.is_authenticated:
        demo_username = getattr(settings, "DEMO_USER_USERNAME", "")
        if getattr(settings, "DEMO_ENABLED", False) and demo_username and request.user.get_username() == demo_username:
            response = redirect("demo")
            response["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response["Pragma"] = "no-cache"
            return response
        return home(request)
    response = render(request, landing_template_name(request), {})
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


@login_required
def home(request):
    braintrees = BrainTree.objects.filter(user=request.user)
    count = braintrees.count()

    if count == 1:
        braintree = braintrees.first()
        return redirect("questionnaire:resume_tree", tree_id=braintree.id)

    return redirect("questionnaire:my_trees")

@login_required
def show_question_step(request, category, order, block_id):
    block_node = (
        BrainBlockNode.objects.select_related("braintree")
        .filter(id=block_id, braintree__user=request.user)
        .first()
    )
    if not block_node:
        messages.warning(
            request,
            "질문 링크가 없거나 만료되었습니다. 처음부터 다시 시작해 주세요.",
        )
        if getattr(settings, "DEMO_ENABLED", False):
            return redirect("demo")
        return redirect("questionnaire:home")

    braintree = block_node.braintree

    cat = get_object_or_404(Category, name=category)
    question = get_object_or_404(Question, category=cat, order=order)
    
    if request.method == 'POST':
        # 「앞으로 가기」: 이전에 답했던 질문 화면으로 이동 (저장·제출 없음)
        if request.POST.get('forward') == '1':
            if order > 1:
                return redirect(
                    'questionnaire:show_question_step',
                    category=category,
                    order=order - 1,
                    block_id=block_id,
                )
            if category != 'common':
                parent_block = block_node.parent
                if parent_block:
                    common_cat = Category.objects.filter(name='common').first()
                    if common_cat:
                        last_common = (
                            Question.objects.filter(category=common_cat)
                            .order_by('-order')
                            .first()
                        )
                        if last_common:
                            return redirect(
                                'questionnaire:show_question_step',
                                category='common',
                                order=last_common.order,
                                block_id=parent_block.id,
                            )
            return redirect('home')

        answer_text = request.POST.get('answer', '').strip()
        if _is_demo_session(request) and not answer_text:
            answer_text = get_demo_default_answer(cat.name, order).strip()
        if answer_text:
            # 이전 질문 노드 찾기
            '''
            previous_node = BrainNode.objects.filter(
                block=block_node,
                order=order - 1
            ).first()
            '''
            # 현재 질문 노드 생성
            brain_node = BrainNode.objects.create(
                block=block_node,
                #parent=previous_node,
                question_text=question.question_text.strip(),
                order=question.order
            )

            # 답변 저장 또는 업데이트
            answer_obj, created = Answer.objects.get_or_create(
                user=request.user,
                question=question,
                brainnode=brain_node,
                defaults={'answer_text': answer_text}
            )
            if not created:
                answer_obj.answer_text = answer_text
                answer_obj.save()

            # 다음 질문 존재 여부 확인
            has_next = Question.objects.filter(category=cat, order=order + 1).exists()

            if has_next:
                return redirect(
                    'questionnaire:show_question_step',
                    category=category,
                    order=order + 1,
                    block_id=block_id
                )
            else:
                if category == 'common':
                    # brain dump 경로에서 도메인이 미리 선택된 경우 domain selection 건너뜀
                    preselected = request.session.pop(
                        f'preselected_domain_{block_node.id}', None
                    )
                    if preselected:
                        return redirect(
                            'questionnaire:show_question_step',
                            category=preselected['domain'],
                            order=1,
                            block_id=preselected['domain_block_id'],
                        )
                    return redirect('questionnaire:select_domain', parent_block_id=block_node.id)
                else:
                    return redirect('questionnaire:ai_question_start', block_id=block_node.id)

    
    demo_default_answer = ""
    if _is_demo_session(request):
        demo_default_answer = get_demo_default_answer(cat.name, order)

    # 공통 vs 도메인 특화 (템플릿·앱 연동용)
    if cat.name == "common":
        question_scope = "common"
        scope_label = "공통 질문"
    else:
        question_scope = "domain"
        scope_label = f"도메인 특화 · {cat.name}"

    has_next_q = Question.objects.filter(category=cat, order=order + 1).exists()
    is_last_domain_question = (not has_next_q) and (cat.name != "common")

    return render(request, _demo_flow_template(request, "show_question_step"), {
        'question': question,
        'block': block_node,
        'tree': braintree,
        'demo_default_answer': demo_default_answer,
        'demo_session': _is_demo_session(request),
        'question_scope': question_scope,
        'scope_label': scope_label,
        'is_last_domain_question': is_last_domain_question,
        'brain_dump_text': _get_brain_dump_text(braintree),
    })

def select_domain(request, parent_block_id):
    parent_node = get_object_or_404(BrainBlockNode, id=parent_block_id)
    tree = parent_node.braintree  # ← 이렇게 바로 접근 가능!
    categories = Category.objects.exclude(name='common')  # 'common' 제외
    allowed_domain = getattr(settings, "DEMO_DOMAIN_CATEGORY", "startup")

    if request.method == "POST":
        selected_domain = request.POST.get("domain")
        if selected_domain != allowed_domain:
            demo_mode = bool(request.session.get("demo_mode"))
            demo_default_domain = None
            if _is_demo_session(request):
                demo_default_domain = pick_demo_domain_category_name()
            return render(
                request,
                _demo_flow_template(request, "select_domain"),
                {
                    "tree": tree,
                    "parent_node": parent_node,
                    "categories": categories,
                    "demo_mode": demo_mode,
                    "demo_default_domain": demo_default_domain,
                    "allowed_domain": allowed_domain,
                },
            )

        # 1. 도메인 카테고리 가져오기 (없으면 생성)
        category, _ = Category.objects.get_or_create(name=selected_domain)

        # 2. 도메인 노드 생성
        domain_node = BrainBlockNode.objects.create(
            parent=parent_node,
            braintree=tree,
            title=f"{selected_domain} 시작",
            type="domain",
            description=f"{selected_domain} 관련 질문 흐름",
            order=1
        )

        # 3. 해당 도메인의 첫 질문 가져오기
        first_question = Question.objects.filter(category=category, order=1).first()
        if not first_question:
            # 질문이 없으면 에러 페이지나 안내로
            return render(request, "questionnaire/test/no_questions.html", {"category": category})

        # 4. 질문 단계로 이동
        return redirect(
            "questionnaire:show_question_step",
            category=category.name,
            order=1,
            block_id=domain_node.id
        )

    demo_mode = bool(request.session.get("demo_mode"))
    demo_default_domain = None
    if _is_demo_session(request):
        demo_default_domain = pick_demo_domain_category_name()

    return render(request, _demo_flow_template(request, "select_domain"), {
        "tree": tree,
        "parent_node": parent_node,
        "categories": categories,
        "demo_mode": demo_mode,
        "demo_default_domain": demo_default_domain,
        "allowed_domain": allowed_domain,
    })

def _get_prompt_flow_answers(user, block_id):
    """block_id 기준 트리 전체 답변 (공통+도메인)."""
    current_block = get_object_or_404(BrainBlockNode, id=block_id, braintree__user=user)
    root_block = current_block.get_ancestors(include_self=True).first()
    all_blocks = root_block.get_descendants(include_self=True)
    nodes = BrainNode.objects.filter(block__in=all_blocks)
    answers = (
        Answer.objects.filter(user=user, brainnode__in=nodes)
        .select_related('question', 'question__category')
        .order_by('created_at')
    )
    return current_block, answers


def _session_key(block_id: int) -> str:
    return f"pf_results_{block_id}"


def _get_ai_block(domain_block):
    return BrainBlockNode.objects.filter(parent=domain_block, type='ai_followup').first()

def _get_user_block(domain_block):
    return BrainBlockNode.objects.filter(parent=domain_block, type='user_custom').first()

def _get_or_create_user_block(domain_block):
    block, _ = BrainBlockNode.objects.get_or_create(
        braintree=domain_block.braintree,
        parent=domain_block,
        type='user_custom',
        defaults={'title': '직접 추가', 'order': 20},
    )
    return block


@never_cache
@login_required
def answers_review(request, block_id):
    """
    도메인 마지막 질문 이후 1단계: 답변만 검토·수정 (AI 미생성).
    POST 시 저장 후 AI 결과 페이지로 이동.
    """
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)

    ai_block = _get_ai_block(current_block)
    ai_brainnodes = list(ai_block.brainnodes.order_by('order')) if ai_block else []

    user_block = _get_user_block(current_block)
    user_brainnodes = list(user_block.brainnodes.order_by('order')) if user_block else []

    if request.method == 'POST':
        # ── 기존 답변 수정 ──
        for a in answers:
            key = f'answer_{a.id}'
            if key in request.POST:
                a.answer_text = request.POST.get(key, '').strip()
                a.save()

        # ── AI 보완 답변 수정 (DB) ──
        for bn in ai_brainnodes:
            field_key = f'ai_answer_{bn.order}'
            if field_key in request.POST:
                bn.answer_text = request.POST.get(field_key, '').strip()
                bn.save()

        # ── 사용자 추가 항목: 기존 항목 수정/삭제 ──
        for bn in user_brainnodes:
            if request.POST.get(f'delete_custom_{bn.id}') == '1':
                bn.delete()
            else:
                q = request.POST.get(f'custom_question_{bn.id}', '').strip()
                a_text = request.POST.get(f'custom_answer_{bn.id}', '').strip()
                if q:
                    bn.question_text = q
                    bn.answer_text = a_text
                    bn.save()

        # ── 사용자 추가 항목: 새 항목 생성 ──
        new_count = int(request.POST.get('new_custom_count', '0') or '0')
        if new_count > 0:
            ub = _get_or_create_user_block(current_block)
            max_order = ub.brainnodes.count()
            for i in range(1, new_count + 1):
                q = request.POST.get(f'new_custom_question_{i}', '').strip()
                a_text = request.POST.get(f'new_custom_answer_{i}', '').strip()
                if q:
                    max_order += 1
                    BrainNode.objects.create(
                        block=ub,
                        question_text=q,
                        answer_text=a_text,
                        order=max_order,
                    )

        # ── 세션 + DB 캐시 초기화 ──
        request.session.pop(_session_key(block_id), None)
        current_block.cached_result_1 = ""
        current_block.cached_result_2 = ""
        current_block.cached_cra = None
        current_block.save(update_fields=["cached_result_1", "cached_result_2", "cached_cra"])
        return redirect('questionnaire:prompt_flow_results', block_id=block_id)

    return render(request, _demo_flow_template(request, "answers_review"), {
        'answers': answers,
        'ai_brainnodes': ai_brainnodes,
        'user_brainnodes': user_brainnodes,
        'block_id': block_id,
        'tree': current_block.braintree,
    })


@never_cache
@login_required
def prompt_flow_results(request, block_id):
    """결과 페이지: 세션에 데이터 있으면 즉시 렌더, 없으면 로딩 화면."""
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)
    user_block = _get_user_block(current_block)
    user_brainnodes = list(user_block.brainnodes.order_by('order')) if user_block else []
    base_ctx = {
        'answers': answers,
        'user_brainnodes': user_brainnodes,
        'tree': current_block.braintree,
        'block_id': block_id,
    }
    session_data = request.session.get(_session_key(block_id))

    # 세션 없으면 DB 캐시 확인
    if not session_data:
        cached = current_block.cached_cra or {}
        if current_block.cached_result_1 and current_block.cached_result_2:
            session_data = {
                "result_1": current_block.cached_result_1,
                "result_2": current_block.cached_result_2,
                "cra_tokens": (cached.get("call1") or {}).get("domain_hits", []),
                "cra_call3": cached.get("call3") or {},
                "continuity_hint": cached.get("continuity_hint"),
                "real_generic_result": cached.get("real_generic_result", ""),
                "real_sp_result": cached.get("real_sp_result", ""),
                "token_before": cached.get("token_before") or {},
                "token_after": cached.get("token_after") or {},
            }
            # 세션에도 복원
            request.session[_session_key(block_id)] = session_data
            request.session.save()

    if not session_data:
        return render(request, _demo_flow_template(request, "prompt_results"), {
            **base_ctx, 'loading': True,
        })
    return render(request, _demo_flow_template(request, "prompt_results"), {
        **base_ctx,
        'loading': False,
        'result_1': session_data.get('result_1', ''),
        'result_2': session_data.get('result_2', ''),
        'cra_tokens': session_data.get('cra_tokens', []),
        'cra_call3': session_data.get('cra_call3', {}),
        'continuity_hint': session_data.get('continuity_hint'),
        'real_generic_result': session_data.get('real_generic_result', ''),
        'real_sp_result': session_data.get('real_sp_result', ''),
        'token_before': session_data.get('token_before', {}),
        'token_after': session_data.get('token_after', {}),
    })


@never_cache
@login_required
def prompt_flow_stream(request, block_id):
    """SSE 스트림: 단계별 AI 생성 진행 상황을 실시간으로 전송."""
    from questionnaire.prompts.service import run_single_task

    def send(data):
        return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def event_stream():
        try:
            current_block, answers = _get_prompt_flow_answers(request.user, block_id)
            extra_qa = []
            ai_block = _get_ai_block(current_block)
            if ai_block:
                for bn in ai_block.brainnodes.order_by('order'):
                    if bn.question_text and bn.answer_text:
                        extra_qa.append({"q": bn.question_text, "a": bn.answer_text})
            user_block = _get_user_block(current_block)
            for bn in (user_block.brainnodes.order_by('order') if user_block else []):
                if bn.question_text and bn.answer_text:
                    extra_qa.append({"q": bn.question_text, "a": bn.answer_text})

            yield send({"step": 1, "total": 6, "label": "답변 분석 준비 중...", "progress": 5})

            yield send({"step": 2, "total": 6, "label": "전략 방향 도출 중...", "progress": 18})
            result_1 = run_single_task("strategy", answers, extra_qa=extra_qa)

            yield send({"step": 3, "total": 6, "label": "맞춤 프롬프트 생성 중...", "progress": 35})
            result_2 = run_single_task("prompt_builder", answers, extra_qa=extra_qa)

            yield send({"step": 4, "total": 6, "label": "핵심 개념 추출 중 (CRA 분석)...", "progress": 55})
            from questionnaire.prompts.cra_engine import run_cra_pipeline
            from pathlib import Path as _Path
            combined_text = " ".join(
                a.answer_text for a in answers if a.answer_text and a.answer_text.strip()
            )
            for item in extra_qa:
                combined_text += f" [추가정보] {item['q']}: {item['a']}"
            kb_names = [p.stem for p in (_Path(__file__).resolve().parent.parent / "prompts" / "kb").glob("*.json")]
            block_title = (current_block.title or "").lower().replace(" ", "_")
            domain = next((k for k in kb_names if k in block_title), None)
            if not domain:
                for a in answers:
                    cat_name = getattr(getattr(a, 'question', None), 'category', None)
                    cat_name = getattr(cat_name, 'name', '') or ''
                    if cat_name in kb_names and cat_name != 'common':
                        domain = cat_name
                        break
            pipeline_result = run_cra_pipeline(
                combined_text, domain=domain, use_ai=True,
                user=request.user, braintree=current_block.braintree,
            )
            cra_tokens, cra_call3, continuity_hint = [], {}, None
            if pipeline_result.get("status") == "OK":
                cra_tokens = (pipeline_result.get("call1") or {}).get("domain_hits", [])
                cra_call3 = pipeline_result.get("call3") or {}
                continuity_hint = pipeline_result.get("continuity_hint")
            logger.info("SSE CRA 결과: status=%s cra_call3_keys=%s expert_len=%d",
                        pipeline_result.get("status"),
                        list(cra_call3.keys()) if cra_call3 else "empty",
                        len((cra_call3.get("expert_output") or "")))

            yield send({"step": 5, "total": 6, "label": "일반 AI 프롬프트 생성 중...", "progress": 73})
            call = _chat_generate_with_usage()
            raw_prompt = (
                "아래는 사용자가 입력한 답변입니다.\n"
                "이 내용을 바탕으로 다른 AI에게 전달할 수 있는 프롬프트를 작성해주세요.\n"
                "프롬프트는 명확한 지시와 필요한 맥락을 포함한 2~4 문단의 산문 형태로 작성하세요.\n\n"
                + combined_text
            )
            try:
                real_generic_result, token_before = call(
                    "gemini-2.5-flash-lite", raw_prompt, {"max_tokens": 600, "temperature": 0.5}
                )
            except Exception as e:
                logger.warning("Before AI 호출 실패 (무시): %s", e)
                real_generic_result, token_before = "", {}

            yield send({"step": 6, "total": 6, "label": "결과 정리 중...", "progress": 90})
            real_sp_result = result_2 if result_2 else ""
            token_after = {}

            session_payload = {
                "result_1": result_1, "result_2": result_2,
                "cra_tokens": cra_tokens, "cra_call3": cra_call3,
                "continuity_hint": continuity_hint,
                "real_generic_result": real_generic_result,
                "real_sp_result": real_sp_result,
                "token_before": token_before, "token_after": token_after,
            }
            request.session[_session_key(block_id)] = session_payload
            request.session.save()

            # DB에도 저장 (세션 만료 후 재방문 시 재호출 방지)
            current_block.cached_result_1 = result_1
            current_block.cached_result_2 = result_2
            current_block.cached_cra = {
                "call3": cra_call3,
                "continuity_hint": continuity_hint,
                "real_generic_result": real_generic_result,
                "real_sp_result": real_sp_result,
                "token_before": token_before,
                "token_after": token_after,
                "call1": {"domain_hits": cra_tokens},
            }
            current_block.save(update_fields=["cached_result_1", "cached_result_2", "cached_cra"])

            yield send({"step": 6, "total": 6, "label": "분석 완료! 결과를 불러오는 중...", "progress": 100})
            yield send({"done": True})

        except Exception as e:
            logger.exception("SSE 스트림 오류 (block_id=%s)", block_id)
            yield send({"error": str(e)})

    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


# 기존 URL 이름 `summary` 호환 (동일 뷰)
summary = answers_review


@login_required
def edit_answer(request, answer_id):
    answer = get_object_or_404(
        Answer.objects.select_related('brainnode'),
        id=answer_id,
        user=request.user,
    )

    if request.method == 'POST':
        new_text = request.POST.get('answer_text')
        if new_text is not None:
            answer.answer_text = new_text.strip()
            answer.save()
        bid = answer.brainnode.block_id
        if bid:
            # 개별 답변 수정 시 세션 + DB 캐시 무효화
            request.session.pop(_session_key(bid), None)
            try:
                block = BrainBlockNode.objects.get(id=bid)
                block.cached_result_1 = ""
                block.cached_result_2 = ""
                block.cached_cra = None
                block.save(update_fields=["cached_result_1", "cached_result_2", "cached_cra"])
            except BrainBlockNode.DoesNotExist:
                pass
            return redirect('questionnaire:summary', block_id=bid)
        return redirect('home')

    return render(request, _demo_flow_template(request, "edit_answer"), {'answer': answer})


@login_required
def regenerate_prompt(request, block_id):
    """캐시 초기화 후 결과 페이지로 리다이렉트 → SSE 재실행."""
    block = get_object_or_404(BrainBlockNode, id=block_id, braintree__user=request.user)
    request.session.pop(_session_key(block_id), None)
    block.cached_result_1 = ""
    block.cached_result_2 = ""
    block.cached_cra = None
    block.save(update_fields=["cached_result_1", "cached_result_2", "cached_cra"])
    return redirect('questionnaire:prompt_flow_results', block_id=block_id)


def can_create_tree(user):
    plan = user.policy.plan
    count = user.brain_trees.filter(status="active").count()
    return count < plan.max_brain_trees

def can_add_child(node):
    plan = node.tree.owner.policy.plan
    return node.depth + 1 <= plan.max_depth

def can_branch_more(parent):
    plan = parent.tree.owner.policy.plan
    return parent.children.count() < plan.max_width

def next_version(node):
    last = node.artifacts.first()
    return (last.version + 1) if last else 1

def dashboard(request):
    braintrees = BrainTree.objects.filter(user=request.user).prefetch_related('nodes')
    return render(request, 'questionnaire/dashboard.html', {
        'braintrees': braintrees
    })

# ─── 데모 세션 목록 ──────────────────────────────────────────────

@login_required
def demo_session_list(request):
    """
    데모 사용자의 전체 세션(BrainTree) 목록.
    도메인 블록이 있으면 결과 페이지 링크를 제공한다.
    """
    if not _is_demo_session(request):
        return redirect('questionnaire:my_trees')

    trees = BrainTree.objects.filter(user=request.user).order_by('-created_at')

    sessions = []
    for tree in trees:
        domain_block = (
            BrainBlockNode.objects.filter(braintree=tree, type='domain')
            .order_by('id')
            .last()
        )
        sessions.append({
            'tree': tree,
            'domain_block': domain_block,
        })

    return render(request, _demo_flow_template(request, 'demo_session_list'), {
        'sessions': sessions,
    })


# ─── AI 보완 질문 플로우 ───────────────────────────────────────────

_AI_Q_SESSION_KEY = "ai_questions_{block_id}"
_AI_A_SESSION_KEY = "ai_answers_{block_id}"
AI_FOLLOWUP_COUNT = 3


_DEMO_FALLBACK_QUESTIONS = [
    {
        "order": 1,
        "text": "목표 고객이 현재 이 문제를 어떻게 해결하고 있나요? 기존 대안의 가장 큰 불편함은 무엇인가요?",
        "hint": "현재 시장의 대안(경쟁사, 수동 방법 등)과 그 한계를 구체적으로 적어주세요.",
    },
    {
        "order": 2,
        "text": "6개월 후 핵심 성과 지표(KPI) 목표치는 어떻게 설정하셨나요?",
        "hint": "MAU, 매출, 고객 수 등 측정 가능한 수치로 적어주세요.",
    },
    {
        "order": 3,
        "text": "팀이 이 문제를 해결하기에 가장 적합한 이유는 무엇인가요?",
        "hint": "창업팀의 도메인 경험, 기술력, 네트워크 등 강점을 적어주세요.",
    },
]


@never_cache
@login_required
def ai_question_start(request, block_id):
    """
    공통+도메인 답변 → AI 보완 질문 생성 → BrainBlockNode(ai_followup) + 세션에 질문 목록 저장.
    """
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)

    questions = generate_ai_followup_questions(list(answers), count=AI_FOLLOWUP_COUNT)
    if not questions:
        logger.warning("AI 보완 질문 생성 실패 (block_id=%s) — fallback 질문 사용", block_id)
        questions = _DEMO_FALLBACK_QUESTIONS

    # AI 보완 블록 생성 (재시작 시 기존 BrainNode 초기화)
    ai_block, created = BrainBlockNode.objects.get_or_create(
        braintree=current_block.braintree,
        parent=current_block,
        type='ai_followup',
        defaults={'title': 'AI 보완 질문', 'order': 10},
    )
    if not created:
        ai_block.brainnodes.all().delete()

    # 세션에 질문 목록만 저장 (step 화면 표시용)
    q_key = _AI_Q_SESSION_KEY.format(block_id=block_id)
    request.session[q_key] = questions
    request.session.modified = True

    return redirect('questionnaire:ai_question_step', block_id=block_id, order=1)


@never_cache
@login_required
def ai_question_step(request, block_id, order):
    """
    AI 보완 질문을 순서대로 보여주고 답변을 BrainNode(DB)에 저장한다.
    """
    q_key = _AI_Q_SESSION_KEY.format(block_id=block_id)
    questions = request.session.get(q_key)
    if not questions:
        return redirect('questionnaire:summary', block_id=block_id)

    total = len(questions)
    if order < 1 or order > total:
        return redirect('questionnaire:summary', block_id=block_id)

    current_q = questions[order - 1]

    if request.method == 'POST':
        answer_text = request.POST.get('answer', '').strip()
        if not answer_text and _is_demo_session(request):
            answer_text = f"(데모 답변 {order})"

        if answer_text:
            ai_block = BrainBlockNode.objects.filter(
                parent_id=block_id, type='ai_followup'
            ).first()
            if ai_block:
                BrainNode.objects.update_or_create(
                    block=ai_block,
                    order=order,
                    defaults={
                        'question_text': current_q["text"],
                        'answer_text': answer_text,
                    },
                )

        if order < total:
            return redirect('questionnaire:ai_question_step', block_id=block_id, order=order + 1)
        return redirect('questionnaire:summary', block_id=block_id)

    current_block = get_object_or_404(BrainBlockNode, id=block_id, braintree__user=request.user)
    return render(request, _demo_flow_template(request, "ai_question_step"), {
        'question': current_q,
        'order': order,
        'total': total,
        'block_id': block_id,
        'tree': current_block.braintree,
        'is_last': order == total,
    })


# ---------------------------------------------------------------------------
# CRA API endpoint
# POST /api/cra/process/   { "text": "..." }
# GET  /api/cra/process/?text=...
# ---------------------------------------------------------------------------
@csrf_exempt
def cra_process(request):
    """
    CRA 엔진 테스트용 API 엔드포인트.

    파라미터:
      text    (필수) 처리할 원문 텍스트
      domain  (선택) startup | marketing | content_creation | efficiency |
                     business_growth | self_development | relationship
      pipeline (선택) true면 Call1+Call2 전체 파이프라인 실행 (기본: false)
      use_ai  (선택) true면 AI 호출 (기본: false, 규칙 기반)
    """
    from questionnaire.prompts.cra_engine import process_cra, run_cra_pipeline

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            text    = body.get("text", "").strip()
            domain  = body.get("domain", "").strip() or None
            pipeline = str(body.get("pipeline", "false")).lower() == "true"
            use_ai  = str(body.get("use_ai", "false")).lower() == "true"
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"error": "JSON body with 'text' field required."}, status=400)
    elif request.method == "GET":
        text    = request.GET.get("text", "").strip()
        domain  = request.GET.get("domain", "").strip() or None
        pipeline = request.GET.get("pipeline", "false").lower() == "true"
        use_ai  = request.GET.get("use_ai", "false").lower() == "true"
    else:
        return JsonResponse({"error": "GET or POST only."}, status=405)

    if not text:
        return JsonResponse({"error": "'text' must not be empty."}, status=400)

    if pipeline:
        result = run_cra_pipeline(text, domain=domain, use_ai=use_ai)
    else:
        result = process_cra(text, domain=domain, use_ai=use_ai)

    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})


# ─── Brain Dump 플로우 ────────────────────────────────────────────────────────

def _get_brain_dump_text(braintree) -> str:
    block = BrainBlockNode.objects.filter(braintree=braintree, type='brain_dump').first()
    return (block.description or "") if block else ""


@never_cache
@login_required
def brain_dump(request, block_id):
    """Brain Dump 입력 페이지 — root block 생성 직후 호출."""
    root_block = get_object_or_404(BrainBlockNode, id=block_id, braintree__user=request.user)

    if request.method == 'POST':
        dump_text = request.POST.get('dump_text', '').strip()

        # 기존 brain_dump 블록이 있으면 갱신, 없으면 생성
        bd_block, _ = BrainBlockNode.objects.update_or_create(
            braintree=root_block.braintree,
            parent=root_block,
            type='brain_dump',
            defaults={'title': 'Brain Dump', 'description': dump_text, 'order': 0},
        )

        if _is_demo_session(request) and not dump_text:
            # 데모: 빈 dump 허용 → 도메인 선택으로 바로 이동
            pass

        return redirect('questionnaire:brain_dump_setup', block_id=root_block.id)

    return render(request, _demo_flow_template(request, 'brain_dump'), {
        'root_block': root_block,
        'tree': root_block.braintree,
    })


@never_cache
@login_required
def brain_dump_setup(request, block_id):
    """도메인 + 진행 방식 선택 페이지."""
    root_block = get_object_or_404(BrainBlockNode, id=block_id, braintree__user=request.user)
    categories = Category.objects.exclude(name='common')
    allowed_domain = getattr(settings, 'DEMO_DOMAIN_CATEGORY', 'physical_therapist')
    brain_dump_text = _get_brain_dump_text(root_block.braintree)

    if request.method == 'POST':
        selected_domain = request.POST.get('domain', '').strip()
        track = request.POST.get('track', 'question_flow')  # 'question_flow' | 'autofill'

        if not selected_domain or selected_domain not in [c.name for c in categories]:
            return render(request, _demo_flow_template(request, 'brain_dump_setup'), {
                'root_block': root_block,
                'tree': root_block.braintree,
                'categories': categories,
                'allowed_domain': allowed_domain,
                'brain_dump_text': brain_dump_text,
                'error': '도메인을 선택해 주세요.',
            })

        category, _ = Category.objects.get_or_create(name=selected_domain)
        domain_block, _ = BrainBlockNode.objects.get_or_create(
            braintree=root_block.braintree,
            parent=root_block,
            type='domain',
            defaults={
                'title': f'{selected_domain} 시작',
                'description': f'{selected_domain} 관련 질문 흐름',
                'order': 1,
            },
        )

        if track == 'autofill':
            return redirect('questionnaire:brain_dump_autofill', domain_block_id=domain_block.id)

        # 질문 flow: 도메인 블록 ID를 세션에 저장 → 공통 질문 완료 후 자동 분기
        request.session[f'preselected_domain_{root_block.id}'] = {
            'domain': selected_domain,
            'domain_block_id': domain_block.id,
        }
        first_common = Question.objects.filter(category__name='common', order=1).first()
        if not first_common:
            return redirect('questionnaire:select_domain', parent_block_id=root_block.id)
        return redirect(
            'questionnaire:show_question_step',
            category='common',
            order=1,
            block_id=root_block.id,
        )

    return render(request, _demo_flow_template(request, 'brain_dump_setup'), {
        'root_block': root_block,
        'tree': root_block.braintree,
        'categories': categories,
        'allowed_domain': allowed_domain,
        'brain_dump_text': brain_dump_text,
    })


@never_cache
@login_required
def brain_dump_autofill(request, domain_block_id):
    """AI가 brain dump → 공통+도메인 답변 자동 생성 후 answers_review로 이동."""
    domain_block = get_object_or_404(
        BrainBlockNode, id=domain_block_id, braintree__user=request.user
    )
    root_block = domain_block.get_ancestors(include_self=True).first()
    brain_dump_text = _get_brain_dump_text(root_block.braintree)

    if request.method == 'POST':
        domain_name = domain_block.title.replace(' 시작', '').strip()
        common_cat = Category.objects.filter(name='common').first()
        domain_cat = Category.objects.filter(name=domain_name).first()

        all_questions = []
        if common_cat:
            all_questions += list(
                Question.objects.filter(category=common_cat).order_by('order')
            )
        if domain_cat:
            all_questions += list(
                Question.objects.filter(category=domain_cat).order_by('order')
            )

        # AI 자동 매핑
        q_dicts = [
            {'id': q.id, 'text': q.question_text, 'category': q.category.name}
            for q in all_questions
        ]
        ai_answers = autofill_answers_from_brain_dump(brain_dump_text, q_dicts)

        # BrainNode + Answer 생성 (질문 flow와 동일한 구조)
        for q in all_questions:
            block = root_block if q.category.name == 'common' else domain_block
            answer_text = ai_answers.get(q.id, '').strip()
            brain_node = BrainNode.objects.create(
                block=block,
                question_text=q.question_text.strip(),
                order=q.order,
            )
            Answer.objects.get_or_create(
                user=request.user,
                question=q,
                brainnode=brain_node,
                defaults={'answer_text': answer_text},
            )

        # 세션 캐시 초기화 (이전 결과 있을 경우 대비)
        request.session.pop(_session_key(domain_block.id), None)
        domain_block.cached_result_1 = ''
        domain_block.cached_result_2 = ''
        domain_block.cached_cra = None
        domain_block.save(update_fields=['cached_result_1', 'cached_result_2', 'cached_cra'])

        return redirect('questionnaire:summary', block_id=domain_block.id)

    return render(request, _demo_flow_template(request, 'brain_dump_autofill'), {
        'domain_block': domain_block,
        'tree': domain_block.braintree,
        'brain_dump_text': brain_dump_text,
    })
