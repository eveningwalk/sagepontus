from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from questionnaire.models.models import Answer
from questionnaire.models.models_braintree import BrainTree, BrainBlockNode, BrainNode
from django.http import JsonResponse
from questionnaire.forms import BrainTreeForm
from questionnaire.prompts.service import _SOAP_DOMAINS


@login_required
def my_trees(request):
    trees = BrainTree.objects.filter(user=request.user).order_by("-created_at")
    tree_data = []
    for tree in trees:
        root_node = BrainBlockNode.objects.filter(braintree=tree, parent=None).first()
        tree_data.append({"tree": tree, "root_node": root_node})
    return render(request, "questionnaire/test/my_trees.html", {"tree_data": tree_data})


@login_required
def create_tree_and_start(request):
    """
    새 BrainTree를 만들고, 첫 Root BrainBlockNode를 생성한 뒤 공통 질문 step 1로 이동
    """
    print("\n 새 BrainTree를 만들고, 첫 Root BrainBlockNode를 생성한 뒤 공통 질문 step 1로 이동")
    if request.method == "POST":
        name = request.POST.get("name", "새 BrainTree")
        
        # 1. 트리 생성
        print(" \n# 1. 트리 생성")
        new_tree = BrainTree.objects.create(
            user=request.user,
            title=name
        )

        print("\n # 2. 루트 노드 생성 (Mptt 기반)")
        root_node = BrainBlockNode.objects.create(
            parent = None,
            braintree=new_tree,
            title="Root 노드",
            type="common",
            description="트리의 시작점입니다",
            order=1
        )

        # 3. Brain Dump 입력 단계로 이동
        print("\n # 3. Brain Dump 단계로 이동")
        return redirect('questionnaire:brain_dump', block_id=root_node.id)
       

    return redirect("home")

@login_required
def edit_tree(request, tree_id):
    tree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
          
    if request.method == "POST":
        form = BrainTreeForm(request.POST, instance=tree)
        if form.is_valid():
            form.save()
            return redirect("home")  # 홈으로 리다이렉트
    else:
        form = BrainTreeForm(instance=tree)

    return render(request, "questionnaire/test/edit_tree.html", {"form": form, "tree": tree})


@login_required
def delete_tree(request, tree_id):
    tree = get_object_or_404(BrainTree, id=tree_id, user=request.user)

    if request.method == "POST":
        tree.delete()
        return redirect("questionnaire:my_trees")

    return render(request, "questionnaire/test/delete_tree.html", {"tree": tree})



def check_braintree_title(request):
    title = request.GET.get("title", "").strip()
    exists = BrainTree.objects.filter(user=request.user, title=title).exists()
    return JsonResponse({"exists": exists})


@login_required
def resume_tree(request, tree_id):
    """트리 진행 상태를 감지하여 적절한 페이지로 리다이렉트."""
    braintree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    root_block = BrainBlockNode.objects.filter(braintree=braintree, parent=None).first()

    if not root_block:
        return redirect('questionnaire:my_trees')

    # 가장 최근 도메인 블록 확인
    domain_block = BrainBlockNode.objects.filter(
        braintree=braintree, type='domain'
    ).order_by('-id').first()

    if domain_block:
        # AI 결과 캐시 있으면 → 결과 페이지
        if domain_block.cached_result_1:
            return redirect('questionnaire:prompt_flow_results', block_id=domain_block.id)
        # 도메인 답변 있으면 → 답변 검토 페이지 (vertical_profile 제외)
        has_domain_answers = Answer.objects.filter(
            user=request.user,
            brainnode__block__braintree=braintree,
        ).exclude(
            brainnode__block__type='vertical_profile',
        ).exists()
        if has_domain_answers:
            return redirect('questionnaire:summary', block_id=domain_block.id)

        # SOAP 도메인 + 프로필 완성 → 바로 autofill
        domain_name = (domain_block.description or '').strip()
        if domain_name in _SOAP_DOMAINS:
            has_profile = Answer.objects.filter(
                user=request.user,
                brainnode__block__braintree=braintree,
                brainnode__block__type='vertical_profile',
            ).exists()
            if has_profile:
                return redirect('questionnaire:brain_dump_autofill', domain_block_id=domain_block.id)

    # brain_dump 블록 있으면 → brain_dump_setup
    brain_dump_exists = BrainBlockNode.objects.filter(
        braintree=braintree, type='brain_dump'
    ).exists()
    if brain_dump_exists:
        return redirect('questionnaire:brain_dump_setup', block_id=root_block.id)

    # 기본: Brain Dump 입력 페이지
    return redirect('questionnaire:brain_dump', block_id=root_block.id)

def review_tree(request, tree_id):
    braintree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    answers = Answer.objects.filter(user=request.user, question__tree=tree).select_related("question")

    return render(request, "questionnaire/review.html", {
        "tree": braintree,
        "answers": answers
    })


###################
# Recursive helper to build MPTT JSON
def build_mptt_tree(node):
    return {
        "id": node.id,
        "title": getattr(node, "title", getattr(node, "question_text", "No Title")),
        "children": [build_mptt_tree(child) for child in node.get_children()]
    }

# Page view: renders template
@login_required
def tree_view(request, braintree_id):
    braintree = get_object_or_404(BrainTree, id=braintree_id, user=request.user)
    return render(request, "questionnaire/test/tree_view.html", {"braintree": braintree})

# JSON endpoint for BrainBlockNode tree
def brainblock_tree_json(request, braintree_id):
    braintree = get_object_or_404(BrainTree, id=braintree_id)

    PURPOSE_LABELS = {
        "context":    "맥락 탐색",
        "motivation": "심리 기반 동기/목표",
        "constraint": "조건/제약",
        "other":      "기타",
    }

    def serialize_node(node):
        # Include BrainNodes (questions + answers) under this block
        brainnodes_data = []
        for bn in node.brainnodes.order_by('order').prefetch_related('answers__question'):
            answers_data = []
            purpose_label = ""
            for a in bn.answers.all():
                answers_data.append({"user": a.user.username, "answer": a.answer_text})
                if not purpose_label and a.question_id:
                    purpose_label = PURPOSE_LABELS.get(a.question.purpose, "")
                # AI 보완·직접 추가 BrainNode는 answer_text에 직접 저장
            if not answers_data and bn.answer_text:
                answers_data.append({"user": "사용자", "answer": bn.answer_text})

            brainnodes_data.append({
                "id": bn.id,
                "order": bn.order,
                "question": bn.question_text,
                "purpose_label": purpose_label,
                "answers": answers_data,
            })

        return {
            "id": node.id,
            "title": node.title,
            "type": node.type,
            "brainnodes": brainnodes_data,
            "children": [serialize_node(c) for c in node.get_children()]
        }

    roots = BrainBlockNode.objects.filter(braintree=braintree, parent=None)

    data = {
        "tree_id": braintree.id,
        "tree_title": braintree.title,
        "tree_owner": braintree.user.username,
        "nodes": [serialize_node(r) for r in roots]
    }

    return JsonResponse(data)

# JSON endpoint for BrainNode tree under a block
def brainnode_tree_json(request, block_id):
    root_nodes = BrainNode.objects.filter(block_id=block_id, parent=None)
    data = [build_mptt_tree(node) for node in root_nodes]
    return JsonResponse(data, safe=False)




