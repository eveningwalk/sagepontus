import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib import rc
import os, django

# 🔹 Django 환경
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "animamus_project.settings")
django.setup()
from questionnaire.models import BrainTree, BrainNode
from django.contrib.auth import get_user_model
User = get_user_model()

# 🔹 폰트 설정
font_path = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
fontprop = fm.FontProperties(fname=font_path)
rc('font', family=fontprop.get_name())
plt.rcParams['axes.unicode_minus'] = False

def visualize_brain_tree(user_id, tree_title="animamus_1", save_path="tree.png"):
    user = User.objects.get(id=user_id)
    tree = BrainTree.objects.get(user=user, title=tree_title)
    nodes = BrainNode.objects.filter(block__braintree=tree).select_related('block', 'parent')

    G = nx.DiGraph()
    labels = {}
    for node in nodes:
        node_label = f"Q: {node.question_text[:30]}\nA: {node.answer_text[:30]}"
        G.add_node(node.id)
        labels[node.id] = node_label
        if node.parent:
            G.add_edge(node.parent.id, node.id)

    # graphviz 'dot' layout 사용 → depth 기반 트리
    pos = graphviz_layout(G, prog='dot')

    plt.figure(figsize=(12, 8))
    nx.draw(
        G,
        pos,
        with_labels=True,
        labels=labels,
        node_size=3000,
        node_color='skyblue',
        font_size=10,
        arrows=True,
        arrowsize=20,
        font_family=fontprop.get_name()
    )

    plt.title(f"{user.username}의 {tree_title} 트리", fontproperties=fontprop)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ 트리 시각화 완료: {save_path}")


if __name__ == "__main__":
    # 테스트용 user_id=1
    visualize_brain_tree(user_id=1)
