import os
from collections import deque, defaultdict
from typing import Self

class Blob:
	def __init__(self, size):
		self.size = size

	def chunkify(self, chunk_size) -> list[Self]: # maybe blob, maybe bytes, doesn't matter for now
		pass
	
	def truncate(self) -> None:
		pass

	@staticmethod
	def from_chunks(chunks):
		pass

"""
A block-based approach, where a single blob maps to one or more fixed-size blocks.

Operations:
- Insert
- Fetch
- Delete

State:
- const BLOCK_SIZE
- free_list: [int], storing the offsets of free blocks
- chunk_map: [key: [int]]

Insert: Check if there are enough free blocks remaining. If there are, pop the 
offsets from the free list and write BLOCK_SIZE bytes at each offset. Also store
the offsets in the map from blob -> offsets.

Fetch: Given a key, get the list of offsets of the blob's chunks, read them,
and combine them.

Delete: Given a key to delete, add each index of the blob's chunks to the free
list

pspoodo code:
-----------------------------
given key, blob
let chunk_map = {}

num_chunks = ceil(blob.size / BLOCK_SIZE)
if len(free_list) > num_chunks:
	for i in 0..num_chunks:
		offset = free_list.pop()
		write(block, BLOCK_SIZE) @ offset
		chunk_map[key].append(offset)
-----------------------------

Pros:
- Supports re-allocation

Cons:
- Inefficent due to non-sequential disk writes
- Single-threaded
"""

SIZE = 0
CHUNKS = 1

class Storage1:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "a+b")

		self.CHUNK_SIZE = 512
		self.chunk_map: dict[any: (int, list[int])] = defaultdict(list)
		self.free_list = deque(range(0, os.path.getsize(disk_filename), self.CHUNK_SIZE))
	
	def insert(self, key, blob):
		chunks = blob.chunkify()
		if len(chunks) > len(self.free_list):
			return
		for i in range(len(chunks)):
			offset = self.free_list.popleft()
			self.handle.seek(offset)
			self.handle.write(chunks[i])
			self.chunk_map[key][CHUNKS].append(offset)
		self.chunk_map[key][SIZE] = blob.size
		
	def fetch(self, key):
		chunks = []
		size, offsets = self.chunk_map[key]
		for offset in offsets:
			self.handle.seek(offset)
			chunks.append(self.handle.read(self.CHUNK_SIZE))
		blob = Blob.from_chunks(chunks)
		blob.truncate(size)
		return blob
		
	def delete(self, key):
		for offset in self.chunk_map[key][CHUNKS]:
			self.free_list.append(offset)
		del self.chunk_map[key]

	def close(self):
		self.handle.close()