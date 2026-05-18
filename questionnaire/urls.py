from django.urls import path
#from . import views
from questionnaire import views



app_name = "questionnaire"

from django.urls import path

urlpatterns = [
    path("", views.home, name="home"),
    path('question/<str:category>/<int:order>/<int:block_id>', views.show_question_step, name='show_question_step'),
    path('edit-answer/<int:answer_id>/', views.edit_answer, name='edit_answer'),
    path('select-domain/<int:parent_block_id>/', views.select_domain, name='select_domain'),
    path('summary/<int:block_id>', views.summary, name='summary'),
    path('ai-questions/<int:block_id>/start/', views.ai_question_start, name='ai_question_start'),
    path('ai-questions/<int:block_id>/step/<int:order>/', views.ai_question_step, name='ai_question_step'),
    path('brain-dump/<int:block_id>/', views.brain_dump, name='brain_dump'),
    path('brain-dump/<int:block_id>/setup/', views.brain_dump_setup, name='brain_dump_setup'),
    path('brain-dump/autofill/<int:domain_block_id>/', views.brain_dump_autofill, name='brain_dump_autofill'),
    path('demo/sessions/', views.demo_session_list, name='demo_session_list'),
    path(
        'prompt-flow/<int:block_id>/results/',
        views.prompt_flow_results,
        name='prompt_flow_results',
    ),
    path(
        'prompt-flow/<int:block_id>/stream/',
        views.prompt_flow_stream,
        name='prompt_flow_stream',
    ),
    path(
        'prompt-flow/<int:block_id>/regenerate/',
        views.regenerate_prompt,
        name='regenerate_prompt',
    ),
    
    path("check-title/", views.check_braintree_title, name="check_braintree_title"),
    path('<int:tree_id>/resume/', views.resume_tree, name='resume_tree'),
    path('<int:tree_id>/review/', views.review_tree, name='review_tree'),
    #path("tree/<int:tree_id>/", views.tree_detail, name="tree_detail"),
    path("tree/<int:tree_id>/edit/", views.edit_tree, name="edit_tree"),
    path("tree/<int:tree_id>/delete/", views.delete_tree, name="delete_tree"),
    
    path("tree/create/", views.create_tree_and_start, name="create_tree_and_start"),
    path("my-trees/", views.my_trees, name="my_trees"),
    
    path('tree/<int:braintree_id>/', views.tree_view, name='tree_view'),
    path('tree/<int:braintree_id>/edit/', views.edit_tree, name='edit_tree'),
    path('tree/<int:braintree_id>/delete/', views.delete_tree, name='delete_tree'),
    
    
    
    path('tree/<int:tree_id>/node/<int:node_id>/step/add/', views.add_node, name='add_node'),
    path('node/<int:node_id>/edit/', views.edit_node, name='edit_node'),
    path('node/<int:node_id>/delete/', views.delete_node, name='delete_node'),

    path('api/save-custom-node/', views.save_custom_node, name='save_custom_node'),
    path('api/brainblock_tree/<int:braintree_id>/', views.brainblock_tree_json, name='brainblock_tree_json'),
    path('api/brainnode_tree/<int:block_id>/', views.brainnode_tree_json, name='brainnode_tree_json'),
    path('api/braintree/<int:braintree_id>/add-block/', views.add_block_node,   name='add_block_node'),
    path('api/brainblock/<int:block_id>/add-nodes/',   views.add_brain_node,   name='add_brain_node'),
    path('api/brainblock/<int:block_id>/update/',      views.update_block_node, name='update_block_node'),
    path('api/brainblock/<int:block_id>/delete/',      views.delete_block_node, name='delete_block_node'),
    path('api/brainnode/<int:node_id>/update/',        views.update_brain_node, name='update_brain_node'),
    path('api/brainnode/<int:node_id>/delete/',        views.delete_brain_node, name='delete_brain_node'),
    path('api/cra/process/', views.cra_process, name='cra_process'),

    path('perf-test/', views.perf_test, name='perf_test'),
    path('perf-test/run/', views.perf_test_run, name='perf_test_run'),
    path('perf-test/vote/', views.perf_test_vote, name='perf_test_vote'),
    path('perf-test/<int:pk>/', views.perf_test_detail, name='perf_test_detail'),

    path('compare/<int:pk>/', views.perf_test_compare, name='perf_test_compare'),
]