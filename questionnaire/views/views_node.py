from django.shortcuts import render, redirect, get_object_or_404
#from questionnaire.models.models import Question, Category
#from questionnaire.models.models_braintree import Answer
from django.contrib.auth.decorators import login_required

#from questionnaire.models.models_braintree import BrainTree, BrainNode
from questionnaire.models.models_braintree import BrainTree
#from .forms import NodeForm
from questionnaire.forms import NodeForm


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
    