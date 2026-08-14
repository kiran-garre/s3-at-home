import os
from collections import deque, defaultdict
from typing import Self
from dataclasses import dataclass
from blob import Blob
from storage_error import *

"""
A block-based approach, where a single blob maps to one or more blocks. There
are a fixed number of blocks, and each block is one of many fixed sizes.

Operations:
- Insert
- Fetch
- Delete
"""

@dataclass
class Chunk:
	size: int
	offset: int

class Storage2:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "r+b")
		# key -> (size, list of chunks)
		self.blob_map: dict[any: tuple[int, list[Chunk]]] = defaultdict(tuple)
		# chunk size -> list of free chunks of that size
		self.free_map: dict[int: list[Chunk]] = defaultdict(list)

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
		if key in self.blob_map:
			return
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

		if remaining > 0:
			for size in self.CHUNK_SIZES:
				if size > remaining and self.free_map[size]:
					chunks.append(self.free_map[size].pop())
					remaining -= size
					break

		# If there's still stuff remaining, that means we couldn't find a block
		if remaining > 0:
			return StorageError(OUT_OF_SPACE, "out of space")
		
		self.write_chunks(blob, chunks)
		self.blob_map[key] = (blob.size, chunks)
		return 
				
	
	def write_chunks(self, blob: Blob, allocated_chunks: list[Chunk]):
		for chunk in allocated_chunks:
			data_chunk = blob.get_chunk(chunk.size)
			self.handle.seek(chunk.offset)
			self.handle.write(data_chunk)
		blob.reset_chunk_generator()

	def fetch(self, key) -> Blob:
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		read_chunks = []
		size, disk_chunks = self.blob_map[key]
		for disk_chunk in disk_chunks:
			self.handle.seek(disk_chunk.offset)
			read_chunks.append(self.handle.read(disk_chunk.size))
		blob = Blob.from_data_chunks(read_chunks)
		blob.truncate(size)
		return blob
		
	def delete(self, key):
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		_, chunks = self.blob_map[key]
		for chunk in chunks:
			self.free_map[chunk.size].append(chunk)
		del self.blob_map[key]

	def close(self):
		self.handle.close()