from functools import lru_cache


class Node: #Not Bst
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
        Check if this node is a sub-concept of another node.
        Returns:
            1 if this node is a sub-concept of other_node,
            -1 if other_node is a sub-concept of this node,
            0 otherwise.
        """
        if self.data in other_node.data:
            return 1
        elif other_node.data in self.data:
            return -1
        return 0

class DataTree:
    def __init__(self):
        self.root = None
        self.nodes = []

    def add_node(self, node: Node):
        self.nodes.append(node)
        if self.root is None:
            self.root = node
        else:
            if node.is_sub_concept_of(self.root):
                self.root.add_child(node)
            else:
                self._add_node_recursive(self.root, node)

    def get_root(self) -> Node:
        return self.root

    def get_nodes(self) -> list[Node]:
        return self.nodes

    def get_node_by_data(self, data: str) -> Node:
        for node in self.nodes:
            if node.data == data:
                return node
        return None

    def _add_node_recursive(self, current_node: Node, new_node: Node):
        if len(current_node.children) == 0:
            print(f"Adding {new_node.data} as a child of {current_node.data}")
            current_node.add_child(new_node)
            return

        tmp = []
        while len(current_node.children) != 0:
            child = current_node.children.pop(0)
            relation = new_node.is_sub_concept_of(child)
            if relation == 1:
                self._add_node_recursive(child, new_node)
                current_node.children.append(child)
                current_node.children.extend(tmp)
                return

            elif relation == -1:
                print(f"Adding {new_node.data} as a child of {current_node.data}")
                current_node.add_child(new_node)
                return

            else:
                tmp.append(child)

        current_node.add_child(new_node)
        current_node.children.extend(tmp)
        return


    def __str__(self):
        return self.root.__str__()

@lru_cache(maxsize=1)
def get_data_tree() -> DataTree:
    return DataTree()

if __name__ == "__main__":
    # Example usage
    data_tree = get_data_tree()
    node = Node("h")
    node1 = Node("hhh")
    node2 = Node("hh")
    node3 = Node("xgs")

    data_tree.add_node(node1)
    data_tree.add_node(node2)
    data_tree.add_node(node3)
    data_tree.add_node(node)
    print(data_tree)
    print(len(data_tree.root.children))  # Should show the children of the root node