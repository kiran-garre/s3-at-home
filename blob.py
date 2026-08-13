from typing import Self

class Blob:
	def __init__(self, size, data: bytes):
		self.size = size
		self.data = data
		self.offset = 0

	def get_chunk(self, chunk_size: int) -> memoryview: # maybe blob, maybe bytes, doesn't matter for now
		data = None
		if offset < self.size:
			data = memoryview(self.data)[offset : offset + chunk_size]
			offset += chunk_size
		return data
	
	def chunkify(self, chunk_size) -> list[bytes]:
		return [self.data[i:i + chunk_size] for i in range(0, len(self.data), chunk_size)]
		
	def truncate(self, new_size) -> None:
		self.data = self.data[:new_size]

	@staticmethod
	def from_data_chunks(chunks: list[memoryview]) -> Self:
		data = b"".join(bytes(m) for m in chunks)
		return Blob(len(data), data)