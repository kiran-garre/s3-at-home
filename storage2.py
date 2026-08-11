import os
from collections import deque, defaultdict
from typing import Self
from dataclasses import dataclass

class Blob:
	def __init__(self, size):
		self.size = size

	def get_chunk(self, chunk_size: int) -> Self: # maybe blob, maybe bytes, doesn't matter for now
		# generator
		pass
	
	def truncate(self) -> None:
		pass

	@staticmethod
	def from_chunks(chunks: list[Self]) -> Self:
		pass

"""
A block-based approach, where a single blob maps to one or more blocks. Each 
block is one of many fixed sizes.

Operations:
- Insert
- Fetch
- Delete
- Modify (new)
"""

SIZE = 0
CHUNKS = 1

@dataclass
class Chunk:
	size: int
	offset: int

class Storage2:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "a+b")
		self.blob_map: dict[any: tuple[int, list[Chunk]]] = defaultdict(tuple)
		self.free_map = defaultdict(list)

		# ----- Build free list -----

		MIN_CHUNK_POWER = 10 # 1KiB
		MAX_CHUNK_POWER = 15 # 32KiB
		self.CHUNK_SIZES = [2**n for n in range(MIN_CHUNK_POWER, MAX_CHUNK_POWER + 1)]
		disk_size = os.path.getsize(disk_filename)
		
		# Let each block size take up at most 0.5 of the remaining available disk space
		# Fill the remaining with minimum chunk size blocks
		THRESHOLD_PCT = 0.5
		tracked_space = 0
		threshold = THRESHOLD_PCT * disk_size
		
		for size in reversed(self.CHUNK_SIZES):
			while (
				tracked_space + size < threshold
				or (size == self.CHUNK_SIZES[0] and tracked_space < disk_size) 
			):
				self.free_map[size].append(Chunk(size, tracked_space))
				tracked_space += size
			threshold = THRESHOLD_PCT * (disk_size - tracked_space)

	
	def insert(self, key, blob):
		# For any blob, we want to grab the largest chunk 
		# such that remaining blob size > size of chunk
		# If there are none, this means the remaining blob size is smaller than
		# all available chunks. Therefore, the minimum sized free chunk is the
		# closest to the remaining blob size (lowest fragmentation).

		# Separate chunk size calculation from actual writing. We don't want to
		# reach the end and then realize we don't have the right sized chunks
		chunks = []
		remaining = blob.size
		for size in reversed(self.CHUNK_SIZES):
			while remaining > size and self.free_map[size]:
				chunks.append(self.free_map[size].pop())
				remaining -= size
		if remaining:
			for size in self.CHUNK_SIZES:
				if self.free_map[size]:
					chunks.append(self.free_map[size].pop())
					self.write_chunks(blob, chunks)
					self.blob_map[key] = (size, chunks)
		
	
	def write_chunks(self, blob: Blob, allocated_chunks: list[Chunk]):
		for chunk in allocated_chunks:
			data_chunk = blob.get_chunk(chunk.size)
			self.handle.seek(chunk.offset)
			self.handle.write(data_chunk)

		
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