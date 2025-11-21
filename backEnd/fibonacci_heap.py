import math
from typing import Any, Optional, List


class FibonacciHeapNode:
    
    def __init__(self, key: float, data: Any):
        self.key = key
        self.data = data
        self.degree = 0
        self.mark = False
        self.parent: Optional['FibonacciHeapNode'] = None
        self.child: Optional['FibonacciHeapNode'] = None
        self.left: 'FibonacciHeapNode' = self
        self.right: 'FibonacciHeapNode' = self


class FibonacciHeap:
    
    def __init__(self):
        self.max_node: Optional[FibonacciHeapNode] = None
        self.num_nodes = 0
        self.num_marks = 0
    
    def is_empty(self) -> bool:
        return self.max_node is None
    
    def insert(self, key: float, data: Any) -> FibonacciHeapNode:
        node = FibonacciHeapNode(key, data)
        
        if self.max_node is None:
            self.max_node = node
        else:
            self._add_to_root_list(node)
            if node.key > self.max_node.key:
                self.max_node = node
        
        self.num_nodes += 1
        return node
    
    def find_max(self) -> Optional[Any]:
        return self.max_node.data if self.max_node else None
    
    def extract_max(self) -> Optional[Any]:
        max_node = self.max_node
        if max_node is None:
            return None
        
        if max_node.child is not None:
            child = max_node.child
            while True:
                next_child = child.right
                child.parent = None
                child.mark = False
                self._add_to_root_list(child)
                
                if next_child == max_node.child:
                    break
                child = next_child
        
        self._remove_from_root_list(max_node)
        
        if max_node == max_node.right:
            self.max_node = None
        else:
            self.max_node = max_node.right
            self._consolidate()
        
        self.num_nodes -= 1
        return max_node.data
    
    def extract_top_k(self, k: int) -> List[Any]:
        results = []
        for _ in range(min(k, self.num_nodes)):
            course = self.extract_max()
            if course is None:
                break
            results.append(course)
        return results
    
    def _add_to_root_list(self, node: FibonacciHeapNode):
        if self.max_node is None:
            self.max_node = node
            node.left = node
            node.right = node
        else:
            node.left = self.max_node
            node.right = self.max_node.right
            self.max_node.right.left = node
            self.max_node.right = node
    
    def _remove_from_root_list(self, node: FibonacciHeapNode):
        if node.right == node:
            return
        
        node.left.right = node.right
        node.right.left = node.left
    
    def _consolidate(self):
        max_degree = int(math.log(self.num_nodes) * 2) + 1
        degree_table = [None] * max_degree
        
        nodes = []
        if self.max_node is not None:
            node = self.max_node
            while True:
                nodes.append(node)
                node = node.right
                if node == self.max_node:
                    break
        
        for node in nodes:
            degree = node.degree
            while degree_table[degree] is not None:
                other = degree_table[degree]
                if node.key < other.key:
                    node, other = other, node
                
                self._link(other, node)
                degree_table[degree] = None
                degree += 1
            
            degree_table[degree] = node
        
        self.max_node = None
        for node in degree_table:
            if node is not None:
                if self.max_node is None:
                    self.max_node = node
                    node.left = node
                    node.right = node
                else:
                    self._add_to_root_list(node)
                    if node.key > self.max_node.key:
                        self.max_node = node
    
    def _link(self, child: FibonacciHeapNode, parent: FibonacciHeapNode):
        self._remove_from_root_list(child)
        
        if parent.child is None:
            parent.child = child
            child.left = child
            child.right = child
        else:
            child.left = parent.child
            child.right = parent.child.right
            parent.child.right.left = child
            parent.child.right = child
        
        child.parent = parent
        parent.degree += 1
        child.mark = False
    
    def union(self, other: 'FibonacciHeap') -> 'FibonacciHeap':
        new_heap = FibonacciHeap()
        
        if self.max_node is None:
            new_heap.max_node = other.max_node
        elif other.max_node is None:
            new_heap.max_node = self.max_node
        else:
            self_last = self.max_node.left
            other_last = other.max_node.left
            
            self_last.right = other.max_node
            other.max_node.left = self_last
            
            other_last.right = self.max_node
            self.max_node.left = other_last
            
            new_heap.max_node = self.max_node if self.max_node.key > other.max_node.key else other.max_node
        
        new_heap.num_nodes = self.num_nodes + other.num_nodes
        return new_heap