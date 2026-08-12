class Node:
	def __init__(self, key=0, value=0, left=None, right=None, parent=None):
		self.key = key
		self.value = value
		self.left = left
		self.right = right
		self.parent = parent

	def assign_left(self, node): 
		self.left = node
		node.parent = self
	
	def assign_right(self, node): 
		self.right = node
		node.parent = self

class KeyedBST:
	def __init__(self, root=None):
		self.root = root
		self.node_map: dict[any, Node] = {}
	
	def increment(self, key):
		if key in self.node_map:
			self.node_map[key].value += 1
			return
		self._insert(key, 1)
		
	def _insert(self, key, value) -> Node:
		# Assumes that "key" is not already present in tree
		new_node = Node(key, value)
		self.node_map[key] = new_node

		if not self.root:
			self.root = new_node
			return
			
		# you know this shit was not written by ai
		curr = self.root
		while curr:
			go_right = value > curr.value
			curr = (
				[curr.left, curr.right][go_right]
				or (lambda x: x.assign_left(new_node), lambda x: x.assign_right(new_node))[go_right](curr)
			)
	
	def get_next_greater(self, key):
		if key not in self.node_map:
			return None
		
		node = self.node_map[key]
		child = node.right
		if child:
			while child.left:
				child = child.left
			return child.key
		
		parent = node.parent
		while parent:
			if parent.key > key:
				return parent.key
			parent = parent.parent
		return None
	
	def get_next_lesser(self, key):
		if key not in self.node_map:
			return None
		
		node = self.node_map[key]
		child = node.left
		if child:
			while child.right:
				child = child.right
			return child.key
		
		parent = node.parent
		while parent:
			if parent.key < key:
				return parent.key
			parent = parent.parent
		return None

	def decrement(self, key):
		if key not in self.node_map:
			return
		self.node_map[key].value -= 1
		if not self.node_map[key].value:
			self._delete(key)

		
	def _delete(self, key):
		# Assumes that key exists in the tree
		node = self.node_map[key]
		
		# case: leaf
		if not node.left and not node.right:
			if node.parent.left == node:
				node.parent.left = None
			else:
				node.parent.right = None

		# case: one child
		elif not node.left and node.right:
			if node.parent.left == node:
				node.parent.left = node.right
			else:
				node.parent.right = node.right
		elif node.left and not node.right:
			if node.parent.left == node:
				node.parent.left = node.left
			else:
				node.parent.right = node.left

		# case: two children
		else:
			successor_key = self.get_next_greater(key)

		# incomplete, because I realized I don't need a BST
		# since we're iterating through powers of two (not the values themselves),
		# N will be small, and linear is probably faster

		# i'll leave it here just in case
			
				
		


	

	

		


	
	
