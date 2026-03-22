from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from questionnaire.models.models import Answer
from questionnaire.models.models_braintree import BrainTree, BrainBlockNode, BrainNode
#from .forms import NodeForm
from django.http import JsonResponse
from questionnaire.forms import BrainTreeForm


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

        # 3. 질문 단계로 이동
        print("\n # 3. 질문 단계로 이동")
        return redirect(
            'questionnaire:show_question_step',
            category='common',
            order=root_node.order,
            #tree_id=new_tree.id,
            block_id=root_node.id
        )
       

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
        return redirect("home")  # 홈으로 리다이렉트

    return render(request, "questionnaire/test/delete_tree.html", {"tree": tree})



def check_braintree_title(request):
    title = request.GET.get("title", "").strip()
    exists = BrainTree.objects.filter(user=request.user, title=title).exists()
    return JsonResponse({"exists": exists})


def resume_tree(request, tree_id):
    braintree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    # 해당 트리에 대한 사용자의 답변 목록
    answers = Answer.objects.filter(user=request.user, question__tree=tree).select_related("question")

    return render(request, "questionnaire/resume.html", {
        "tree": braintree,
        "answers": answers
    })

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
def tree_view(request, braintree_id):
    braintree = get_object_or_404(BrainTree, id=braintree_id)
    return render(request, "questionnaire/test/tree_view.html", {"braintree": braintree})

# JSON endpoint for BrainBlockNode tree
def brainblock_tree_json(request, braintree_id):
    braintree = get_object_or_404(BrainTree, id=braintree_id)

    def serialize_node(node):
        # Include BrainNodes (questions + answers) under this block
        brainnodes_data = []
        for bn in node.brainnodes.all():
            answers_data = [
                {"user": a.user.username, "answer": a.answer_text} 
                for a in bn.answers.all()
            ]
            brainnodes_data.append({
                "id": bn.id,
                "question": bn.question_text,
                "answers": answers_data
            })

        return {
            "id": node.id,
            "title": node.title,
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




