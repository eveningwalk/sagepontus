from django.shortcuts import render, redirect, get_object_or_404
from questionnaire.models.models import Question, Category, Answer
from django.contrib.auth.decorators import login_required

from questionnaire.models.models_braintree import BrainTree, BrainNode
from .forms import NodeForm

@login_required
def home(request):
    # 로그인한 유저의 BrainTree 불러오기
    braintrees = BrainTree.objects.filter(user=request.user).order_by("created_at")

    if request.method == "POST":
        # 새 BrainTree 생성 요청
        new_name = request.POST.get("name", "Untitled BrainTree")
        BrainTree.objects.create(user=request.user, title=new_name)
        return redirect("home")

    return render(request, "questionnaire/test/home.html", {"braintrees": braintrees})
    

@login_required
def show_question_step(request, category, order, tree_id,node_id = 0):
    braintree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    node = get_object_or_404(BrainNode, id=node_id, tree=braintree)
    # 카테고리와 질문 객체 가져오기
    cat = get_object_or_404(Category, name=category)
    question = get_object_or_404(Question, category=cat, order=order)
    
    if request.method == 'POST':
        answer_text = request.POST.get('answer', '').strip()
        if answer_text:
            # 기존 답변이 있는지 확인 (user + question 기준)
            answer_obj, created = Answer.objects.get_or_create(
                user=request.user,
                question=question,
                node = node,   # ✅ BrainTree와 연결
                defaults={'answer_text': answer_text}
            )
            if not created:  # 이미 있으면 업데이트
                answer_obj.answer_text = answer_text
                answer_obj.save()

        # 공통 질문이 끝났는지 확인
        has_next = Question.objects.filter(category=cat, order=order + 1).exists()

        if not has_next:
            if category == 'common':
                return redirect('questionnaire:select_domain', tree_id=tree_id, parent_node_id= node_id)
            else:
                return redirect('questionnaire:summary')

        return redirect('questionnaire:show_question_step', category=category, order=order + 1, tree_id=tree_id, node_id= node_id)

    return render(request, 'questionnaire/test/show_question_step.html', {
        'question': question
    })

def edit_answer(request, answer_id):
    answer = get_object_or_404(Answer, id=answer_id)

    if request.method == 'POST':
        new_text = request.POST.get('answer_text')
        if new_text:
            answer.answer_text = new_text
            answer.save()
            return redirect('questionnaire:complete')

    return render(request, 'questionnaire/test/edit_answer.html', {'answer': answer})

def select_domain(request):
    return render(request, 'questionnaire/test/select_domain.html')

def select_domain(request, tree_id, parent_node_id):

    braintree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    parent_node = get_object_or_404(BrainNode, id=parent_node_id, tree=braintree)
    
    if request.method == 'POST':
        domain = request.POST.get('domain')
        if domain:
            # 새로운 하위 노드 생성 (도메인 분기용)
            new_node = BrainNode.objects.create(
                tree=braintree,
                parent=parent_node,
                depth=parent_node.depth + 1,
                order=parent_node.order + 1,
                title=f"{domain} 분기 노드"
            )
            return redirect('questionnaire:show_question_step',
                            category=domain,
                            order=1,
                            tree_id=braintree.id,
                            node_id=new_node.id)

    return render(request, 'questionnaire/test/select_domain.html', {'tree': braintree, 'parent_node': parent_node})
      


from transformers import pipeline
def prompt_generater(prompt):
    generator = pipeline("text-generation", model="EleutherAI/gpt-neo-125M")
    response = generator(prompt, max_length=300, do_sample=True, temperature=0.7)
    print(response[0]["generated_text"])

def summary(request):
    answers = Answer.objects.all().order_by('created_at')

    formatted_text = ""
    for idx, answer in enumerate(answers, start=1):
        question_text = answer.question.question_text.strip()
        answer_text = answer.answer_text.strip()
        formatted_text += f"Q{idx}. {question_text}\nA{idx}. {answer_text}\n\n"
        
    prompt_1 = f"{formatted_text} → 위 응답을 기반으로, 실행 중심 성향을 가진 사용자에게 적합한 실행 전략을 제안해주세요."
    prompt_2 = f"{formatted_text} → 위 응답을 기반으로, 실행 중심 성향을 가진 사용자에게 적합한 실행 전략을 생성할 수 있는 Prompt를 만들어주세요."
    prompt_generater(prompt_1)
    prompt_generater(prompt_2)

    return render(request, 'questionnaire/test/complete.html', {'answers': answers})

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

from django.http import JsonResponse

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


@login_required

def tree_detail(request, tree_id):
    tree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    nodes = tree.nodes.all().order_by("order")
    return render(request, "questionnaire/test/tree_detail.html", {"tree": tree, "nodes": nodes})

from .forms import BrainTreeForm
@login_required
#def create_tree_and_start(request, order, tree_id, node_id):
def create_tree_and_start(request):
    """
    새 BrainTree를 만들고, 공통 질문 step 1로 바로 이동
    """
    if request.method == "POST":
        name = request.POST.get("name", "새 BrainTree")  # 입력 없으면 기본값
        new_tree = BrainTree.objects.create(
            user=request.user,
            title=name
        )
        #first_node = BrainNode.objects.filter(tree=new_tree).order_by('order').first()
        depth = 1  # The depth of the tree
        order = 1  # The branch order of the same level
        root_node = BrainNode.objects.create(
                tree = new_tree,
                parent = None,
                depth= depth,
                order= order,
                title= f" Root 노드"
            )
        #return redirect("questionnaire:show_question_step", category="common", order=1)
        #return redirect("questionnaire:show_question_step", category="common", order=1, tree_id=new_tree.id)
        return redirect('questionnaire:show_question_step', category='common', order=root_node.order, tree_id=new_tree.id, node_id= root_node.id)

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


@login_required
def add_node(request, tree_id, node_id):
    tree = get_object_or_404(BrainTree, id=tree_id, user=request.user)
    if request.method == "POST":
        form = NodeForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.tree = tree
            step.save()
            return redirect("questionnaire:tree_detail", tree_id=tree.id)
    else:
        form = NodeForm()
    return render(request, "questionnaire/test/add_node.html", {"form": form, "tree": tree})

@login_required
def edit_node(request, step_id):
    step = get_object_or_404(Step, id=step_id, tree__user=request.user)
    if request.method == "POST":
        form = NodeForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            return redirect("tree_detail", tree_id=step.tree.id)
    else:
        form = NodeForm(instance=step)
    return render(request, "questionnaire/test/edit_step.html", {"form": form, "tree": step.tree})

@login_required
def delete_node(request, step_id):
    step = get_object_or_404(Step, id=step_id, tree__user=request.user)
    tree_id = step.tree.id
    step.delete()
    return redirect("questionnaire:tree_detail", tree_id=tree_id)



def dashboard(request):
    braintrees = BrainTree.objects.filter(user=request.user).prefetch_related('nodes')
    return render(request, 'questionnaire/dashboard.html', {
        'braintrees': braintrees
    })