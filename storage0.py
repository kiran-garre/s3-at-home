from blob import Blob
from storage_error import *
import os

"""
If I had to implmenet a key-value blob store:
We need to:
1. Write the blobs to disk
2. Remember where the blobs are

Operations:
- Insert
- Fetch
- Delete

Simplest case:
Insert: Keep an index in the file. For a new blob, write the blob at that index and
store the index+size in a map. This is append only

Fetch: Given a key, get the index/size, read from disk starting at that index

Delete: Given a key to delete, remove it from the map.

pspoodo code:
-----------------------------
given key, blob
let blob_map = {}

write(blob, @index)
blob_map[key] = (index, blob.size)
-----------------------------

Pros:
- Simple
- Fast if the disk writes are optimized (e.g. buffered)

Cons:
- Append-only (no modifications)
- Deleted entries still take up disk space
- Single-threaded only
"""

class Storage0:
	def __init__(self, disk_filename):
		self.blob_map: dict[any, (int, int)] = {}
		self.handle = open(disk_filename, "r+b")
		self.file_size = os.path.getsize(disk_filename)
		self.write_offset = 0
	
	def insert(self, key, blob):
		if key in self.blob_map:
			return
		if blob.size + self.write_offset > self.file_size:
			return StorageError(OUT_OF_SPACE, "out of space")
		
		self.handle.seek(self.write_offset)
		self.handle.write(blob.data)
		self.blob_map[key] = (self.write_offset, blob.size)
		self.write_offset += blob.size
		
	def fetch(self, key) -> Blob:
		if key not in self.blob_map:
			return StorageError(KEY_NOT_FOUND, f"key: \"{key}\" not found")
		
		offset, size = self.blob_map[key]
		self.handle.seek(offset)
		data = self.handle.read(size)
		return Blob(len(data), data)

		
	def delete(self, key):
		if key in self.blob_map:
			del self.blob_map[key]

	def close(self):
		self.handle.close()