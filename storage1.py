import os
from collections import deque, defaultdict
from typing import Self
from blob import Blob
from storage_error import *


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
		self.handle = open(disk_filename, "r+b")

		self.CHUNK_SIZE = 512
		self.blob_map: dict[any, (int, list[int])] = defaultdict(lambda: (0, []))
		self.free_list = deque(range(0, os.path.getsize(disk_filename), self.CHUNK_SIZE))
	
	def insert(self, key, blob):
		if key in self.blob_map:
			return None
		chunks = blob.chunkify(self.CHUNK_SIZE)
		if len(chunks) > len(self.free_list):
			return StorageError(OUT_OF_SPACE, "out of space")
		offsets = []
		for i in range(len(chunks)):
			offset = self.free_list.popleft()
			self.handle.seek(offset)
			self.handle.write(chunks[i])
			offsets.append(offset)
		self.blob_map[key] = (blob.size, offsets)
		
	def fetch(self, key) -> Blob:
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		chunks = []
		size, offsets = self.blob_map[key]
		for offset in offsets:
			self.handle.seek(offset)
			chunks.append(self.handle.read(self.CHUNK_SIZE))
		blob = Blob.from_data_chunks(chunks)
		blob.truncate(size)
		return blob
		
	def delete(self, key):
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		for offset in self.blob_map[key][CHUNKS]:
			self.free_list.append(offset)
		del self.blob_map[key]

	def close(self):
		self.handle.close()