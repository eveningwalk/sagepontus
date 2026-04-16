import json
import logging

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from questionnaire.models.models import Question,Category, Answer
from django.contrib.auth.decorators import login_required

from questionnaire.models.models_braintree import BrainTree, BrainBlockNode, BrainNode
from questionnaire.demo_config import get_demo_default_answer, pick_demo_domain_category_name
from questionnaire.prompts import run_prompt_generation_pair
from questionnaire.prompts.service import generate_ai_followup_questions, _chat_generate_with_usage
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
    """
    루트 URL(/). 비로그인 + 데모 ON → 랜딩 페이지.
    데모 유저 로그인 중 → 항상 /demo/ (새 세션 시작)으로 이동.
    """
    if request.user.is_authenticated:
        demo_username = getattr(settings, "DEMO_USER_USERNAME", "")
        if getattr(settings, "DEMO_ENABLED", False) and demo_username and request.user.get_username() == demo_username:
            response = redirect("demo")
            response["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response["Pragma"] = "no-cache"
            return response
        return home(request)
    if getattr(settings, "DEMO_ENABLED", False):
        response = render(request, landing_template_name(request), {})
        response["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response["Pragma"] = "no-cache"
        return response
    return redirect("accounts:login")


@login_required
def home(request):
    # 로그인한 유저의 BrainTree 불러오기
    braintrees = BrainTree.objects.filter(user=request.user).order_by("created_at")

    if request.method == "POST":
        new_name = request.POST.get("name", "Untitled BrainTree")
        new_tree = BrainTree.objects.create(user=request.user, title=new_name)
        return redirect("questionnaire:create_tree_and_start")

    return render(request, "questionnaire/test/home.html", {"braintrees": braintrees})

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


@login_required
def answers_review(request, block_id):
    """
    도메인 마지막 질문 이후 1단계: 답변만 검토·수정 (AI 미생성).
    POST 시 저장 후 AI 결과 페이지로 이동.
    """
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)

    # 세션에서 AI 보완 질문 답변 로드
    a_key = _AI_A_SESSION_KEY.format(block_id=block_id)
    raw_ai = request.session.get(a_key, {})
    # order 순서대로 정렬된 리스트: [{"order": 1, "q": "...", "a": "..."}]
    ai_qa_list = sorted(
        [{"order": int(k), **v} for k, v in raw_ai.items()],
        key=lambda x: x["order"]
    )

    if request.method == 'POST':
        for a in answers:
            key = f'answer_{a.id}'
            if key in request.POST:
                a.answer_text = request.POST.get(key, '').strip()
                a.save()
        # AI 보완 답변 수정 반영 (세션 업데이트)
        updated_ai = dict(raw_ai)
        for item in ai_qa_list:
            field_key = f'ai_answer_{item["order"]}'
            if field_key in request.POST:
                updated_ai[str(item["order"])]["a"] = request.POST.get(field_key, '').strip()
        request.session[a_key] = updated_ai
        request.session.modified = True
        # 답변이 바뀌었으므로 캐시 전체 무효화
        current_block.cached_result_1 = ""
        current_block.cached_result_2 = ""
        current_block.cached_cra = None
        current_block.save(update_fields=["cached_result_1", "cached_result_2", "cached_cra"])
        return redirect('questionnaire:prompt_flow_results', block_id=block_id)

    return render(request, _demo_flow_template(request, "answers_review"), {
        'answers': answers,
        'ai_qa_list': ai_qa_list,
        'block_id': block_id,
        'tree': current_block.braintree,
    })


@login_required
def prompt_flow_results(request, block_id):
    """2단계: 답변을 바탕으로 맞춤 프롬프트(및 실행 요약) 생성."""
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)

    # AI 보완 질문 답변을 세션에서 가져와 함께 전달
    a_key = _AI_A_SESSION_KEY.format(block_id=block_id)
    raw_ai = request.session.get(a_key, {})
    extra_qa = list(raw_ai.values()) if raw_ai else []

    # 캐시된 결과가 있으면 AI 재호출 없이 바로 사용
    if current_block.cached_result_1 and current_block.cached_result_2:
        result_1 = current_block.cached_result_1
        result_2 = current_block.cached_result_2
    else:
        result_1, result_2 = run_prompt_generation_pair(answers, extra_qa=extra_qa)
        current_block.cached_result_1 = result_1
        current_block.cached_result_2 = result_2
        current_block.save(update_fields=["cached_result_1", "cached_result_2"])

    # CRA 파이프라인 + 실제 Before/After — 최초 1회만 AI 호출, 이후 cached_cra 재사용
    cra_tokens = []
    cra_call3 = {}
    continuity_hint = None
    real_generic_result = ""
    real_sp_result = ""
    token_before = {}
    token_after = {}
    try:
        cached = current_block.cached_cra or {}

        # ── 캐시에 실제 결과까지 있으면 바로 사용 ──
        if cached.get("status") == "OK" and cached.get("real_generic_result"):
            pipeline_result = cached
            real_generic_result = cached.get("real_generic_result", "")
            real_sp_result = cached.get("real_sp_result", "")
            token_before = cached.get("token_before") or {}
            token_after = cached.get("token_after") or {}
        else:
            # ── 최초 호출 ──
            from questionnaire.prompts.cra_engine import run_cra_pipeline
            from pathlib import Path

            combined_text = " ".join(
                a.answer_text for a in answers if a.answer_text and a.answer_text.strip()
            )
            kb_names = [p.stem for p in (Path(__file__).resolve().parent.parent / "prompts" / "kb").glob("*.json")]
            block_title = (current_block.title or "").lower().replace(" ", "_")
            domain = next((k for k in kb_names if k in block_title), None)
            if not domain:
                for a in answers:
                    cat_name = getattr(getattr(a, 'question', None), 'category', None)
                    cat_name = getattr(cat_name, 'name', '') or ''
                    if cat_name in kb_names and cat_name != 'common':
                        domain = cat_name
                        break

            # CRA 파이프라인
            pipeline_result = run_cra_pipeline(
                combined_text,
                domain=domain,
                use_ai=True,
                user=request.user,
                braintree=current_block.braintree,
            )

            gen = {"max_tokens": 800, "temperature": 0.5}
            call = _chat_generate_with_usage()

            # ① 일반 AI (Before): raw 답변 그대로 전송
            raw_prompt = (
                "아래는 사용자가 입력한 답변입니다. 이를 바탕으로 실행 가능한 조언을 해주세요.\n\n"
                + combined_text
            )
            real_generic_result, token_before = call("gemini-2.0-flash", raw_prompt, gen)

            # ② Sage Pontus (After): CRA 정제 프롬프트(result_2) 전송
            sp_prompt = result_2 if result_2 else combined_text
            real_sp_result, token_after = call("gemini-2.0-flash", sp_prompt, gen)

            # 전체 캐시 저장
            if pipeline_result.get("status") == "OK":
                pipeline_result["real_generic_result"] = real_generic_result
                pipeline_result["real_sp_result"] = real_sp_result
                pipeline_result["token_before"] = token_before
                pipeline_result["token_after"] = token_after
                current_block.cached_cra = pipeline_result
                current_block.save(update_fields=["cached_cra"])

        if pipeline_result.get("status") == "OK":
            cra_tokens = (pipeline_result.get("call1") or {}).get("domain_hits", [])
            cra_call3 = pipeline_result.get("call3") or {}
            continuity_hint = pipeline_result.get("continuity_hint")
    except Exception:
        logger.exception("CRA 파이프라인 실패 — 결과 페이지는 정상 표시")

    return render(request, _demo_flow_template(request, "prompt_results"), {
        'answers': answers,
        'result_1': result_1,
        'result_2': result_2,
        'tree': current_block.braintree,
        'block_id': block_id,
        'cra_tokens': cra_tokens,
        'cra_call3': cra_call3,
        'continuity_hint': continuity_hint,
        'real_generic_result': real_generic_result,
        'real_sp_result': real_sp_result,
        'token_before': token_before,
        'token_after': token_after,
    })


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
            # 개별 답변 수정 시 캐시 무효화
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
        return redirect('landing')

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


@login_required
def ai_question_start(request, block_id):
    """
    공통+도메인 답변을 Gemini에 보내 보완 질문 AI_FOLLOWUP_COUNT개를 생성한 후
    첫 번째 질문 화면으로 이동한다.
    생성 실패 시: 데모 세션이면 fallback 질문 사용, 일반 세션이면 answers_review로 스킵.
    """
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)

    questions = generate_ai_followup_questions(list(answers), count=AI_FOLLOWUP_COUNT)

    if not questions:
        if _is_demo_session(request):
            # 데모에서 AI 생성 실패 시 fallback 질문으로 단계를 보여줌
            questions = _DEMO_FALLBACK_QUESTIONS
        else:
            # 일반 세션은 기존대로 요약 단계로 스킵
            return redirect('questionnaire:summary', block_id=block_id)

    # 세션에 저장
    q_key = _AI_Q_SESSION_KEY.format(block_id=block_id)
    a_key = _AI_A_SESSION_KEY.format(block_id=block_id)
    request.session[q_key] = questions
    request.session[a_key] = {}
    request.session.modified = True

    return redirect('questionnaire:ai_question_step', block_id=block_id, order=1)


@login_required
def ai_question_step(request, block_id, order):
    """
    AI 생성 보완 질문을 order 순서로 보여주고 답변을 세션에 저장한다.
    마지막 질문 후 answers_review로 이동.
    """
    q_key = _AI_Q_SESSION_KEY.format(block_id=block_id)
    a_key = _AI_A_SESSION_KEY.format(block_id=block_id)

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
            ai_answers = request.session.get(a_key, {})
            ai_answers[str(order)] = {"q": current_q["text"], "a": answer_text}
            request.session[a_key] = ai_answers
            request.session.modified = True

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
