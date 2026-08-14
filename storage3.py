import os
from collections import deque, defaultdict
from typing import Any
from dataclasses import dataclass
from blob import Blob
from storage_error import *

"""
A block-based approach, where a single blob maps to one or more blocks. Blocks 
are split through partitioning, and contiguous blocks are combined into
bigger blocks through coalescing. Allocated blocks are always as large as 
possible under the blob size (or remaining size) until the minimum block size
is reached.

Operations:
- Insert
- Fetch
- Delete
"""

def ceil_log(n: int):
	if n == 1:
		return 0
	return (n - 1).bit_length()

def floor_log(n: int):
	return n.bit_length() - 1

@dataclass(frozen=True)
class Chunk:
	size: int
	offset: int

ZERO_CHUNK = Chunk(0, 0)

def partition(chunk: Chunk, min_size: int) -> tuple[Chunk, Chunk]:
	size, offset = chunk.size, chunk.offset
	new_size = size // 2
	if new_size < min_size:
		return chunk, ZERO_CHUNK
	return Chunk(new_size, offset), Chunk(new_size, offset + new_size)
	
def coalesce(chunks: list[Chunk], min_size, max_size) -> list[Chunk]:
	if not chunks:
		return []
	
	# Assumes the chunks are ordered and contiguous
	offset = chunks[0].offset
	new_chunks = []
	remaining_size = sum([chunk.size for chunk in chunks])
	
	while remaining_size > 0:
		if remaining_size < min_size:
			print(f"warning: unexpected fragmentation of {remaining_size} bytes")
			break
		new_chunk_size = min(2**floor_log(remaining_size), max_size)
		new_chunks.append(Chunk(new_chunk_size, offset))
		offset += new_chunk_size
		remaining_size -= new_chunk_size

	if remaining_size < 0:
		raise RuntimeError(f"overallocation of {remaining_size} bytes")
	
	# print(f"Coalesced: {list(map(lambda x: x.size, chunks))} -> {list(map(lambda x: x.size, new_chunks))}")

	return new_chunks


def fit_big_chunk(size, big_chunk: Chunk, min_chunk_size: int) -> tuple[list[Chunk], list[Chunk]]:
	if size > big_chunk.size:
		return
		
	# print(f"Partitioning: blob of size {size} -> big chunk of size: {big_chunk.size}")
	allocated_chunks = []
	free_chunks = []
	
	def recurse(size, chunk):
		nonlocal allocated_chunks, free_chunks, min_chunk_size
		if chunk.size <= 0:
			return size
		if size <= 0:
			free_chunks.append(chunk)
			return -1
		if chunk.size == min_chunk_size or chunk.size <= size:
			allocated_chunks.append(chunk)
			return size - chunk.size
		
		# Keep partitioning if our blocks are too big (and if we can)
		chunk1, chunk2 = partition(chunk, min_chunk_size)
		remaining = recurse(size, chunk1)
		remaining = recurse(remaining, chunk2)
		return remaining
		
	recurse(size, big_chunk)
	# print(f"Allocated chunk sizes: {list(map(lambda x: x.size, allocated_chunks))}")
	# print(f"Free chunk sizes: {list(map(lambda x: x.size, free_chunks))}")
	
	return allocated_chunks, free_chunks


class Storage3:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "r+b")
		# key -> (size, list of chunks)
		self.blob_map: dict[Any, tuple[int, list[Chunk]]] = defaultdict(tuple)
		# log2(chunk size) -> list of free chunks of that size
		self.free_map: dict[int: list[Chunk]] = defaultdict(set)

		MIN_CHUNK_POWER = 9 # 512B
		max_chunk_power = os.path.getsize(disk_filename).bit_length() - 1
		if max_chunk_power < MIN_CHUNK_POWER:
			raise ValueError("how you gonna store blobs in such a tiny file")

		self.MIN_CHUNK_POWER = MIN_CHUNK_POWER
		self.max_chunk_power = max_chunk_power

		max_size = 2**max_chunk_power
		self.free_map[max_chunk_power].add(Chunk(max_size, 0))

	def coalesce(self, chunks: list[Chunk]) -> list[Chunk]:
		return coalesce(chunks, 2**self.MIN_CHUNK_POWER, 2**self.max_chunk_power)

	def insert(self, key, blob):
		if key in self.blob_map:
			return
		allocated_chunks = self.get_chunks(blob.size)
		if not allocated_chunks:
			return StorageError(OUT_OF_SPACE, "out of space")
		self.write_chunks(blob, allocated_chunks)
		self.blob_map[key] = (blob.size, allocated_chunks)
		
				
	def get_chunks(self, size) -> list[Chunk]:
		# Consider the case where we have a 6KB blob, and we have a single free 8KB and six free 1KB blocks. 
		# Then, the largest blocks that are smaller than the blob are the 1KB blocks, but the better solution
		# would be to partition the 8KB block into an allocated 6KB (4KB + 2KB) and a leftover 2KB block.
		# 
		# Therefore, the cleanest solution is actually to prioritize looking for the smallest block that
		# is larger than the blob (or whatever's left), partitioning it, coalescing the leftovers,
		# and recursing.
		#
		# Then, only once this fails (meaning there are no larger blocks) do we look for smaller blocks.
		# There's no reason to partition in this case, so we try to find the largest block that is smaller 
		# than the remaining blob size (recursively if needed).

		allocated_chunks = []
		free_chunks = []

		def look_for_and_fit_big_chunk(size):
			for power in range(ceil_log(size), self.max_chunk_power + 1):
				if self.free_map[power]:
					big_chunk = self.free_map[power].pop()
					return fit_big_chunk(size, big_chunk, 2**self.MIN_CHUNK_POWER)
			return [], []

		allocated_chunks, free_chunks = look_for_and_fit_big_chunk(size)
			
		if allocated_chunks:
			allocated_chunks = self.coalesce(allocated_chunks)
			free_chunks = self.coalesce(free_chunks)
		else:
			remaining = size
			for power in range(floor_log(size), self.MIN_CHUNK_POWER - 1, -1):
				chunk_size = 2**power
				while remaining >= chunk_size and self.free_map[power]:
					allocated_chunks.append(self.free_map[power].pop())
					remaining -= chunk_size
					if remaining < chunk_size:
						a, f = look_for_and_fit_big_chunk(remaining)
						if a:
							a = self.coalesce(a)
							f = self.coalesce(f)
							allocated_chunks.extend(a)
							free_chunks.extend(f)
							remaining = 0
							break
			if remaining > 0:
				return []
		
		
		for chunk in free_chunks:
			self.free_map[floor_log(chunk.size)].add(chunk)

		return allocated_chunks
	

	def write_chunks(self, blob: Blob, allocated_chunks: list[Chunk]):
		# print(f"writing blob of size {blob.size}")
		for chunk in allocated_chunks:
			# print(chunk)
			temp = blob.offset
			data_chunk = blob.get_chunk(chunk.size)
			# print(f"{temp} -> {blob.offset}")
			self.handle.seek(chunk.offset)
			self.handle.write(data_chunk)
		# print()
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
			s = self.free_map[floor_log(chunk.size)]
			before = Chunk(chunk.size, chunk.offset - chunk.size)
			after = Chunk(chunk.size, chunk.offset + chunk.size)
			if before in s:
				for coalesced_chunk in self.coalesce([before, chunk]):
					s.add(coalesced_chunk)
			elif after in s:
				for coalesced_chunk in self.coalesce([chunk, after]):
					s.add(coalesced_chunk)
			else:
				s.add(chunk)
				
		del self.blob_map[key]


	def close(self):
		self.handle.close()