from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from questionnaire.models.models import Question,Category, Answer
from django.contrib.auth.decorators import login_required

from questionnaire.models.models_braintree import BrainTree, BrainBlockNode, BrainNode
from questionnaire.demo_config import get_demo_default_answer, pick_demo_domain_category_name
from questionnaire.prompts import run_prompt_generation_pair
from questionnaire.views.views_demo import demo_landing


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
    루트 URL(/). QR이 도메인만 넣으면 여기로 옴 — 비로그인은 데모가 켜져 있으면 /demo/ 로 보냄.
    """
    if request.user.is_authenticated:
        return home(request)
    if getattr(settings, "DEMO_ENABLED", False):
        return demo_landing(request)
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
    block_node = get_object_or_404(BrainBlockNode, id=block_id)
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
                    return redirect('questionnaire:summary', block_id=block_node.id)

    
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
        'question_scope': question_scope,
        'scope_label': scope_label,
        'is_last_domain_question': is_last_domain_question,
    })

def select_domain(request, parent_block_id):
    parent_node = get_object_or_404(BrainBlockNode, id=parent_block_id)
    tree = parent_node.braintree  # ← 이렇게 바로 접근 가능!
    categories = Category.objects.exclude(name='common')  # 'common' 제외

    if request.method == "POST":
        selected_domain = request.POST.get("domain")
        print("선택된 도메인:", selected_domain)  # ✅ 로그 확인용


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

    if request.method == 'POST':
        for a in answers:
            key = f'answer_{a.id}'
            if key in request.POST:
                text = request.POST.get(key, '').strip()
                a.answer_text = text
                a.save()
        return redirect('questionnaire:prompt_flow_results', block_id=block_id)

    return render(request, _demo_flow_template(request, "answers_review"), {
        'answers': answers,
        'block_id': block_id,
        'tree': current_block.braintree,
    })


@login_required
def prompt_flow_results(request, block_id):
    """2단계: 답변을 바탕으로 맞춤 프롬프트(및 실행 요약) 생성."""
    current_block, answers = _get_prompt_flow_answers(request.user, block_id)

    result_1, result_2 = run_prompt_generation_pair(answers)

    return render(request, _demo_flow_template(request, "prompt_results"), {
        'answers': answers,
        'result_1': result_1,
        'result_2': result_2,
        'tree': current_block.braintree,
        'block_id': block_id,
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