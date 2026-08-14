from dataclasses import dataclass
import os
from collections import deque, defaultdict
from typing import Self
from blob import Blob
from storage_error import *


"""
A block-based approach. This is sort of the inverse of storage3, and an 
extension of storage1. Rather than starting with large blocks that we break down 
into the sizes that we need, we start with several minimum sized blocks and 
coalesce to larger blocks as needed.
"""

@dataclass
class AbstractChunk:
	size: int
	offset: int

def break_down_chunk(chunk: AbstractChunk, size: int):
	# print(f"breaking down {chunk} -> {list(range(chunk.offset, chunk.offset + chunk.size, size))}")
	return list(range(chunk.offset, chunk.offset + chunk.size, size))

def coalesce():
	pass

class Storage4:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "r+b")

		self.CHUNK_SIZE = 512
		self.blob_map: dict[any, (int, list[AbstractChunk])] = defaultdict(lambda: (0, []))
		disk_size = os.path.getsize(disk_filename)

		# Fixed size list, where each element is (disk offset, is chunk free)
		# Every AbstractChunk is always CHUNK_SIZE when it's in this list
		self.chunk_list = [
			[offset, True]
			for offset in range(0, disk_size, self.CHUNK_SIZE)
		]
		self.num_free = len(self.chunk_list)
	
	def insert(self, key, blob):
		if key in self.blob_map:
			return None
		
		num_chunks = (blob.size + self.CHUNK_SIZE - 1) / self.CHUNK_SIZE
		if num_chunks > self.num_free:
			return StorageError(OUT_OF_SPACE, "out of space")
		
		chunks: list[AbstractChunk] = []
		remaining = blob.size
		for i, (offset, is_free) in enumerate(self.chunk_list):
			if remaining <= 0:
				break
			if not is_free:
				continue
			if chunks and offset == chunks[-1].offset + chunks[-1].size:
				# CHUNK_SIZE is (only) enforced in self.chunk_list
				chunks[-1].size += self.CHUNK_SIZE
			else:
				chunks.append(AbstractChunk(self.CHUNK_SIZE, offset))
			self.chunk_list[i][1] = False
			self.num_free -= 1
			remaining -= self.CHUNK_SIZE

		# print(f"inserting into abstract chunks: {chunks}")
		self.write_chunks(blob, chunks)
		self.blob_map[key] = (blob.size, chunks)

	def write_chunks(self, blob: Blob, allocated_chunks: list[AbstractChunk]):
		offset = 0
		view = memoryview(blob.data)
		for chunk in allocated_chunks:
			data_chunk = view[offset : offset + chunk.size]
			self.handle.seek(chunk.offset)
			self.handle.write(data_chunk)
			offset += chunk.size
		blob.reset_chunk_generator()
		
	def fetch(self, key) -> Blob:
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		data_chunks = []
		size, abstract_chunks = self.blob_map[key]
		for abstract_chunk in abstract_chunks:
			self.handle.seek(abstract_chunk.offset)
			data_chunks.append(self.handle.read(abstract_chunk.size))
		blob = Blob.from_data_chunks(data_chunks)
		blob.truncate(size)
		return blob
		
	def delete(self, key):
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		for chunk in self.blob_map[key][1]:
			for offset in break_down_chunk(chunk, self.CHUNK_SIZE):
				self.chunk_list[offset // self.CHUNK_SIZE][1] = True
				self.num_free += 1
		del self.blob_map[key]

	def close(self):
		self.handle.close()



"""
[0, 1, 2, 3, 4]
[1, 1, 1, 1, 1]
[1, 2, 3, 4]
   [0, 1, 2, 3]

remove 2
[1, 1, 0, 1, 1]
[1, 3, 3, 4]
   [0, 1, 1, 3]

remove 3
[1, 1, 0, 0, 1]
[1, 4, 4, 4]
   [0, 1, 1, 1]

insert 2
[1, 1, 1, 0, 1]
[]

"""