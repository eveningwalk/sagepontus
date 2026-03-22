# utils.py
def build_mptt_tree(node):
    return {
        "id": node.id,
        "title": node.title if hasattr(node, "title") else node.question_text[:30],
        "children": [build_mptt_tree(child) for child in node.get_children()]
    }
