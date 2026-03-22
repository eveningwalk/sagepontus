from django.urls import path
#from . import views
from questionnaire import views



app_name = "questionnaire"

from django.urls import path

urlpatterns = [
    path("", views.home, name="home"),
    path('questionnaire/question/<str:category>/<int:order>/<int:block_id>', views.show_question_step, name='show_question_step'),
    path('edit-answer/<int:answer_id>/', views.edit_answer, name='edit_answer'),
    path('questionnaire/select-domain/<int:parent_block_id>/', views.select_domain, name='select_domain' ),
    path('summary/<int:block_id>', views.summary, name='summary'),
    
    path("check-title/", views.check_braintree_title, name="check_braintree_title"),
    path('<int:tree_id>/resume/', views.resume_tree, name='resume_tree'),
    path('<int:tree_id>/review/', views.review_tree, name='review_tree'),
    #path("tree/<int:tree_id>/", views.tree_detail, name="tree_detail"),
    path("tree/<int:tree_id>/edit/", views.edit_tree, name="edit_tree"),
    path("tree/<int:tree_id>/delete/", views.delete_tree, name="delete_tree"),
    
    path("tree/create/", views.create_tree_and_start, name="create_tree_and_start"),
    
    path('tree/<int:braintree_id>/', views.tree_view, name='tree_view'),
    path('tree/<int:braintree_id>/edit/', views.edit_tree, name='edit_tree'),
    path('tree/<int:braintree_id>/delete/', views.delete_tree, name='delete_tree'),
    
    
    
    path('tree/<int:tree_id>/node/<int:node_id>/step/add/', views.add_node, name='add_node'),
    path('node/<int:node_id>/edit/', views.edit_node, name='edit_node'),
    path('node/<int:node_id>/delete/', views.delete_node, name='delete_node'),

    path('api/brainblock_tree/<int:braintree_id>/', views.brainblock_tree_json, name='brainblock_tree_json'),
    path('api/brainnode_tree/<int:block_id>/', views.brainnode_tree_json, name='brainnode_tree_json'),


]