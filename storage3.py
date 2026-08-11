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
	def from_data_chunks(chunks: list[Self]) -> Self:
		pass

"""
A block-based approach, where a single blob maps to one or more blocks. Blocks 
are split through partitioning, and smaller blocks are combined into
bigger blocks through coalescing. Allocated blocks are always as large as 
possible under the blob size (or remaining size) until the minimum block size
is reached.

Operations:
- Insert
- Fetch
- Delete
"""

@dataclass
class Chunk:
	size: int
	offset: int

class Storage3:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "a+b")
		# key -> (size, list of chunks)
		self.blob_map: dict[any: tuple[int, list[Chunk]]] = defaultdict(tuple)
		# chunk size -> list of free chunks of that size
		self.free_map: dict[int: list[Chunk]] = defaultdict(list)

		MIN_CHUNK_POWER = 10 # 1KiB
		max_chunk_power = os.path.getsize(disk_filename).bit_length - 1
		if max_chunk_power < MIN_CHUNK_POWER:
			raise ValueError("how you gonna store blobs in such a tiny file")
		self.chunk_sizes = [2**n for n in range(MIN_CHUNK_POWER, max_chunk_power + 1)]

		max_size = self.chunk_sizes[-1]
		self.free_map[max_size].append(Chunk(max_size, 0))

	def partition_chunk(chunk: Chunk) -> tuple[Chunk, Chunk]:
		size, offset = chunk.size, chunk.offset
		new_size = size // 2
		return Chunk(new_size, offset), Chunk(new_size, offset + new_size)
	
	def coalesce_chunks(chunk1: Chunk, chunk2: Chunk) -> Chunk:
		# This function assumes chunk1 and chunk2 are contiguous and ordered
		if chunk1.size != chunk2.size:
			raise ValueError("Attempted to coalesce chunks of different sizes")
		return Chunk(chunk1.size + chunk2.size, chunk1.offset)

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
					return 0
				print("Failed to insert object")
				return 1
	
	def write_chunks(self, blob: Blob, allocated_chunks: list[Chunk]):
		for chunk in allocated_chunks:
			data_chunk = blob.get_chunk(chunk.size)
			self.handle.seek(chunk.offset)
			self.handle.write(data_chunk)

	def fetch(self, key) -> Blob:
		read_chunks = []
		size, disk_chunks = self.blob_map[key]
		for disk_chunk in disk_chunks:
			self.handle.seek(disk_chunk.offset)
			read_chunks.append(self.handle.read(disk_chunk.size))
		blob = Blob.from_data_chunks(read_chunks)
		blob.truncate(size)
		return blob
		
	def delete(self, key):
		_, chunks = self.blob_map[key]
		for chunk in chunks:
			self.free_map[chunk.size].append(chunk)
		del self.blob_map[key]

	def close(self):
		self.handle.close()