import os
from collections import deque, defaultdict
from typing import Self
from threading import Condition, Lock

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
A block-based approach supporting multiple readers and a single writer.

Operations:
- Insert
- Fetch
- Delete

To support threads, we need a 

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

class AtomicVar:
	def __init__(self, lock: Lock):
		self.val = None
		self.lock = lock

	def set(self, value):
		self.lock.acquire()
		try:
			self.val = value
		finally:
			self.lock.release()

	def get(self):
		self.lock.acquire()
		try:
			return self.val
		finally:
			self.lock.release()

	def modify(self, f):
		self.lock.acquire()
		try:
			self.val = f(self.val)
		finally:
			self.lock.release()

SIZE = 0
CHUNKS = 1

inc = lambda x: x + 1
dec = lambda x: x - 1

class Storage2:
	def __init__(self, disk_filename):
		self.handle = open(disk_filename, "a+b")

		self.CHUNK_SIZE = 512
		self.chunk_map: dict[any: (int, list[int])] = defaultdict(list)
		self.free_list = deque(range(0, os.path.getsize(disk_filename), self.CHUNK_SIZE))

		self.readers = AtomicVar(Lock())
		self.condition = Condition()

	def insert(self, key, blob):
		with self.condition:
			while self.readers.get():
				self.condition.wait()
			try:
				self._insert(key, blob)
			finally:
				self.condition.notify_all()
	
	def fetch(self, key):
		with self.condition:
			self.readers.modify(inc)
		try:
			return self._fetch(key)
		finally:
			self.readers.modify(dec)
			self.condition.notify_all()

	def delete(self, key):
		with self.condition:
			while self.readers.get():
				self.condition.wait()
			try:
				self._delete(key)
			finally:
				self.condition.notify_all()
	
	def _insert(self, key, blob):
		chunks = blob.chunkify()
		if len(chunks) > len(self.free_list):
			return
		for i in range(len(chunks)):
			offset = self.free_list.popleft()
			self.handle.seek(offset)
			self.handle.write(chunks[i])
			self.chunk_map[key][CHUNKS].append(offset)
		self.chunk_map[key][SIZE] = blob.size
		
	def _fetch(self, key):
		chunks = []
		size, offsets = self.chunk_map[key]
		for offset in offsets:
			self.handle.seek(offset)
			chunks.append(self.handle.read(self.CHUNK_SIZE))
		blob = Blob.from_chunks(chunks)
		blob.truncate(size)
		return blob
		
	def _delete(self, key):
		for offset in self.chunk_map[key][CHUNKS]:
			self.free_list.append(offset)
		del self.chunk_map[key]

	def close(self):
		self.handle.close()