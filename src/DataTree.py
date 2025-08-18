from functools import lru_cache
import google.generativeai as genai

class Node:
    def __init__(self, data: str):
        self.data = data
        self.children = []
        self.parent = None

    def add_child(self, child_node):
        print(f"Adding child {child_node.data} to parent {self.data}")
        self.children.append(child_node)
        child_node.parent = self
        return self

    def __repr__(self):
        return f"Node({self.data})"

    def __str__(self):
        return f"Node: {self.data}, Children: {[child.__str__() for child in self.children]}"

    def is_sub_concept_of(self, other_node: 'Node') -> int:
        """
        Check if this node is a sub-concept of another node using simple string matching.
        For production, you might want to use AI-based comparison.
        Returns:
            1 if this node is a sub-concept of other_node,
            -1 if other_node is a sub-concept of this node,
            0 otherwise.
        """
        # 단순 문자열 포함 관계로 판단
        if self.data.lower() in other_node.data.lower() and self.data != other_node.data:
            return 1
        elif other_node.data.lower() in self.data.lower() and self.data != other_node.data:
            return -1
        return 0


class DataTree:
    def __init__(self):
        self.root = None
        self.nodes = []

    def add_node(self, node: Node):
        """노드를 트리에 추가"""
        # 중복 체크
        for existing_node in self.nodes:
            if existing_node.data.lower() == node.data.lower():
                print(f"Node {node.data} already exists, skipping...")
                return existing_node

        self.nodes.append(node)

        if self.root is None:
            self.root = node
            print(f"Setting {node.data} as root")
        else:
            relation = node.is_sub_concept_of(self.root)
            if relation == 1:
                self.root.add_child(node)
            else:
                self._add_node_recursive(self.root, node)

        return node

    def get_root(self) -> Node:
        return self.root

    def get_nodes(self) -> list[Node]:
        return self.nodes

    def get_node_by_data(self, data: str) -> Node:
        """데이터로 노드 검색 (대소문자 무시)"""
        for node in self.nodes:
            if node.data.lower() == data.lower():
                return node
        return None

    def find_related_nodes(self, query: str) -> list[Node]:
        """쿼리와 관련된 노드들을 찾음"""
        related = []
        query_words = query.lower().split()

        for node in self.nodes:
            node_words = node.data.lower().split()
            # 단어 일치도 확인
            if any(word in node.data.lower() for word in query_words):
                related.append(node)

        return related

    def _add_node_recursive(self, current_node: Node, new_node: Node):
        """재귀적으로 적절한 위치에 노드 추가"""
        if len(current_node.children) == 0:
            print(f"Adding {new_node.data} as a child of {current_node.data}")
            current_node.add_child(new_node)
            return

        tmp = []
        children_copy = current_node.children.copy()
        current_node.children = []

        for child in children_copy:
            relation = new_node.is_sub_concept_of(child)
            if relation == 1:
                current_node.children.extend(tmp)
                current_node.children.append(child)
                self._add_node_recursive(child, new_node)
                return
            elif relation == -1:
                print(f"Adding {new_node.data} as a child of {current_node.data}")
                current_node.add_child(new_node)
                new_node.add_child(child)
                current_node.children.extend(tmp)
                return
            else:
                tmp.append(child)

        current_node.add_child(new_node)
        current_node.children.extend(tmp)

    def print_tree(self, node=None, level=0):
        """트리 구조를 보기 좋게 출력"""
        if node is None:
            node = self.root

        if node is None:
            print("Empty tree")
            return

        indent = "  " * level
        print(f"{indent}{node.data}")

        for child in node.children:
            self.print_tree(child, level + 1)

    def get_tree_info(self):
        """트리 정보 반환"""
        return {
            "total_nodes": len(self.nodes),
            "root": self.root.data if self.root else None,
            "tree_depth": self._calculate_depth(self.root) if self.root else 0
        }

    def _calculate_depth(self, node):
        """트리의 깊이 계산"""
        if not node or not node.children:
            return 1

        max_child_depth = max(self._calculate_depth(child) for child in node.children)
        return max_child_depth + 1

    def __str__(self):
        return self.root.__str__() if self.root else "Empty tree"


@lru_cache(maxsize=1)
def get_data_tree() -> DataTree:
    return DataTree()


if __name__ == "__main__":
    # 테스트 코드
    print("=== DataTree 테스트 ===")
    data_tree = get_data_tree()

    # 테스트 노드들
    concepts = ["동물", "포유류", "강아지", "골든리트리버", "식물", "나무", "소나무"]

    for concept in concepts:
        node = Node(concept)
        data_tree.add_node(node)

    print("\n=== 트리 구조 ===")
    data_tree.print_tree()

    print(f"\n=== 트리 정보 ===")
    info = data_tree.get_tree_info()
    for key, value in info.items():
        print(f"{key}: {value}")

    print(f"\n=== 관련 노드 검색 테스트 ===")
    query = "강아지"
    related = data_tree.find_related_nodes(query)
    print(f"'{query}'와 관련된 노드들: {[node.data for node in related]}")